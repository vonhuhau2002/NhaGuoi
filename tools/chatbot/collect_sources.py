"""Tải bản raw của các nguồn đã chọn; ghi hash, URL cuối và lỗi để đối chiếu."""

from concurrent.futures import ThreadPoolExecutor
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parents[2]
ROOT = BASE / "data/chatbot"
MANIFEST = ROOT / "manifests/sources.json"


def collect(source):
    row = dict(source)
    row["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    try:
        url = row["url"]
        if url.startswith("local:"):
            content = (BASE / url.removeprefix("local:")).read_bytes()
            suffix, content_type = ".txt", "text/plain; charset=utf-8"
            row["http_status"], row["final_url"] = None, url
        else:
            response = requests.get(url, timeout=(12, 45), headers={
                "User-Agent": "NhaRongCoTuResearch/0.1 (source verification)"})
            row["http_status"], row["final_url"] = response.status_code, response.url
            response.raise_for_status()
            content = response.content
            content_type = response.headers.get("Content-Type", "")
            suffix = ".pdf" if content.startswith(b"%PDF-") else ".html"
            if row["kind"].endswith("_pdf") and suffix != ".pdf":
                raise ValueError("Nguồn PDF trả về HTML/chặn truy cập; không coi là PDF đã tải.")
            if len(content) > 25 * 1024 * 1024:
                raise ValueError("Nguồn vượt giới hạn 25 MiB của đợt thu thập này.")
        digest = hashlib.sha256(content).hexdigest()
        path = ROOT / "raw" / f"{row['source_id']}_{digest[:12]}{suffix}"
        if not path.exists():
            path.write_bytes(content)
        row.update(status="downloaded", raw_path=str(path.relative_to(BASE)),
                   sha256=digest, bytes=len(content), content_type=content_type)
    except Exception as error:
        row.update(status="failed", error=f"{type(error).__name__}: {error}")
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", help="Chỉ tải các source_id được chọn")
    args = parser.parse_args()
    sources = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if args.only:
        unknown = set(args.only) - {row["source_id"] for row in sources}
        if unknown:
            parser.error(f"source_id không tồn tại: {sorted(unknown)}")
        sources = [row for row in sources if row["source_id"] in args.only]
    ROOT.joinpath("raw").mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(collect, sources))
    target = ROOT / "manifests/downloads.jsonl"
    # Giữ lịch sử lỗi và các phiên bản tải; raw được đặt tên theo hash.
    with target.open("a", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    for row in rows:
        print(row["source_id"], row["status"], row.get("bytes", 0),
              urlparse(row["url"]).netloc or "local", row.get("error", ""), flush=True)
    return 0 if all(row["status"] == "downloaded" for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
