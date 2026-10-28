import json
import math
from pathlib import Path
import platform
import resource
import statistics
import time


def evaluate(retriever, questions_path, rounds=100):
    questions = [json.loads(line) for line in Path(questions_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not questions or rounds < 100:
        raise ValueError("Cần bộ câu hỏi và ít nhất 100 lượt đo warm retrieval.")
    cases, hits, total, no_answer_matches = [], 0, 0, 0
    for case in questions:
        found = [d["document_id"] for d in retriever.search(case["question"], case.get("history", []))]
        relevant = case.get("relevant_document_ids", [])
        hit = bool(set(relevant) & set(found))
        if case["answerability"] == "answerable":
            total += 1
            hits += hit
        elif case["answerability"] == "insufficient_evidence" and found:
            no_answer_matches += 1
        cases.append({"id": case["id"], "expected": case["answerability"], "relevant": relevant,
                      "retrieved": found, "hit": hit})
    samples = []
    for i in range(rounds):
        case = questions[i % len(questions)]
        started = time.perf_counter()
        retriever.search(case["question"], case.get("history", []))
        samples.append((time.perf_counter() - started) * 1000)
    return {
        "kind": "offline_retrieval_only", "seed_is_human_gold": False,
        "model_api_called": False, "machine": platform.machine(), "python": platform.python_version(),
        "mode": retriever.mode, "index_version": retriever.meta["version"],
        "documents": int(retriever.meta["count"]), "questions": len(questions),
        "answerable": total, "hits_at_3": hits,
        "hit_rate_at_3": hits / total if total else None,
        "mean_recall_at_3": statistics.mean(
            len(set(c["relevant"]) & set(c["retrieved"])) / len(set(c["relevant"]))
            for c in cases if c["expected"] == "answerable" and c["relevant"]) if total else None,
        "unanswerable_with_retrieval_matches": no_answer_matches,
        "warm_requests": rounds, "retrieval_p50_ms": round(statistics.median(samples), 3),
        "retrieval_p95_ms": round(sorted(samples)[math.ceil(.95 * len(samples)) - 1], 3),
        "process_peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
        "cases": cases,
    }
