"""FTS5/BM25 sans neural models; index built explicitly, read-only per request."""

import hashlib
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import time
import unicodedata

from cotu_app.core.paths import CHATBOT_CONFIG_DIR
from .config import ROOT


SCHEMA_VERSION = 1
EXCLUDED = {"quarantine", "context_only", "corroboration_only", "research_candidate"}
STOP_WORDS = set("la gi co tu cua nguoi thi va de dung lam cho ve nhu nao vay sao nhung cac mot trong voi khong phai hay toi ban nay do y nghia biet duoc the chi con dung chung".split())


def normalize(text):
    text = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in text if unicodedata.category(c) != "Mn")))


def eligible(doc, mode):
    if mode not in {"approved", "research"}:
        raise ValueError("Mode phải là approved hoặc research.")
    if doc.get("usage") in EXCLUDED or "quarantine" in doc.get("review_status", ""):
        return False
    approved = doc.get("production_approved") is True and doc.get("review_status") == "approved"
    return approved or (mode == "research" and doc.get("usage") == "research_notes"
                        and doc.get("review_status") == "agent_reviewed")


def read_corpus(path):
    docs, ids = [], set()
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        doc = json.loads(line)
        for key in ("document_id", "source_id", "title", "text", "source_url", "raw_sha256"):
            if not isinstance(doc.get(key), str) or not doc[key].strip():
                raise ValueError(f"Corpus dòng {number}: thiếu {key}.")
        if doc["document_id"] in ids:
            raise ValueError(f"Trùng document_id dòng {number}.")
        if not re.fullmatch(r"[A-Za-z0-9:_\-.]+", doc["document_id"]):
            raise ValueError(f"document_id dòng {number} không hợp lệ.")
        if not doc["source_url"].startswith(("https://", "http://", "local:")):
            raise ValueError(f"Nguồn dòng {number} không hợp lệ.")
        if not re.fullmatch(r"[a-f0-9]{64}", doc["raw_sha256"]):
            raise ValueError(f"Hash dòng {number} không hợp lệ.")
        if not doc.get("evidence_locator"):
            raise ValueError(f"Corpus dòng {number}: thiếu evidence_locator.")
        if len(doc["text"]) > 2000:
            raise ValueError(f"Corpus dòng {number} > 2.000 ký tự: chia đoạn và giữ locator trước.")
        ids.add(doc["document_id"])
        docs.append(doc)
    return docs


def index_path(mode):
    if mode not in {"approved", "research"}:
        raise ValueError("Mode không hợp lệ.")
    return ROOT / "index" / f"{mode}.sqlite3"


def build_index(corpus, target, mode, aliases_path=CHATBOT_CONFIG_DIR / "aliases.json"):
    docs = read_corpus(corpus)
    selected = [d for d in docs if eligible(d, mode)]
    aliases = json.loads(Path(aliases_path).read_text(encoding="utf-8"))
    fingerprint = hashlib.sha256(json.dumps(
        [SCHEMA_VERSION, mode, docs, aliases], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".sqlite3", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        with closing(sqlite3.connect(temp_path)) as db, db:
            db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
            db.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, body TEXT)")
            db.execute("CREATE VIRTUAL TABLE chunks USING fts5(id UNINDEXED, title, text, terms, tokenize='unicode61 remove_diacritics 2')")
            for doc in selected:
                terms = [a for topic in doc.get("topics", []) for a in aliases.get(topic, [])]
                db.execute("INSERT INTO documents VALUES (?, ?)",
                           (doc["document_id"], json.dumps(doc, ensure_ascii=False)))
                db.execute("INSERT INTO chunks VALUES (?, ?, ?, ?)", (
                    doc["document_id"], normalize(doc["title"] + " " + doc.get("heading", "")),
                    normalize(doc["text"]), normalize(" ".join(terms))))
            meta = {"version": fingerprint, "mode": mode, "count": str(len(selected)),
                    "schema": str(SCHEMA_VERSION), "built_at": str(time.time())}
            db.executemany("INSERT INTO meta VALUES (?, ?)", meta.items())
        temp_path.replace(target)
    finally:
        temp_path.unlink(missing_ok=True)
    return meta


class Retriever:
    def __init__(self, path, mode):
        self.path, self.mode = Path(path).resolve(), mode
        if not self.path.is_file():
            raise ValueError(f"Chưa có index {mode}; chạy build-index --mode {mode} trước.")
        with closing(self.connect()) as db:
            self.meta = dict(db.execute("SELECT key, value FROM meta"))
        if self.meta.get("mode") != mode or self.meta.get("schema") != str(SCHEMA_VERSION):
            raise ValueError("Index sai mode/phiên bản; dựng lại index.")

    def connect(self):
        # Connections are request-local; safe across UI worker threads.
        return sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)

    def search(self, question, history=(), limit=3):
        query = normalize(question)
        words = [w for w in query.split() if w not in STOP_WORDS and len(w) > 1]
        # Only anaphoric follow-ups inherit prior USER topic; never assistant claims.
        followup = query.startswith(("con ", "the ", "vay ", "do ")) or len(words) < 2
        if followup and history:
            prior = next((h["content"] for h in reversed(history) if h.get("role") == "user"), "")
            words += [w for w in normalize(prior).split() if w not in STOP_WORDS and len(w) > 1]
        words = list(dict.fromkeys(words))[:32]
        if not words:
            return []
        expression = " OR ".join('"' + w + '"' for w in words)
        with closing(self.connect()) as db:
            current = dict(db.execute("SELECT key,value FROM meta"))
            if current.get("version") != self.meta["version"]:
                raise ValueError("Index đã đổi; khởi động lại chatbot để đồng bộ cache.")
            rows = db.execute(
                "SELECT d.body, chunks.title, chunks.text, chunks.terms FROM chunks JOIN documents d ON d.id=chunks.id "
                "WHERE chunks MATCH ? ORDER BY bm25(chunks, 0, 3, 1, 2), chunks.id LIMIT ?",
                (expression, max(limit * 4, 12))).fetchall()
        # One accidental syllable (giá/giả, tỷ/ty) is too weak for longer queries.
        # This is a retrieval heuristic, never a proof that evidence answers a question.
        minimum = 2 if len(words) >= 3 else 1
        return [json.loads(row[0]) for row in rows
                if len(set(words) & set(" ".join(row[1:]).split())) >= minimum][:limit]
