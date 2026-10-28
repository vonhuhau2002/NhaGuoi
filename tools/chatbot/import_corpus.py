#!/usr/bin/env python3
"""Copy validated JSONL without rewriting approval flags or source metadata."""
import argparse
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from cotu_app.features.chatbot.retrieval import read_corpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path,
                        default=ROOT / "data/chatbot/clean/documents.jsonl")
    parser.add_argument("--target", type=Path, default=ROOT / "data/chatbot/corpus/documents.jsonl")
    args = parser.parse_args()
    raw = args.source.read_bytes()
    # Validate the exact bytes that will be installed, not a second read of source.
    args.target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=args.target.parent, delete=False) as temp:
        temp.write(raw)
        temp_path = Path(temp.name)
    try:
        docs = read_corpus(temp_path)
        temp_path.replace(args.target)
    finally:
        temp_path.unlink(missing_ok=True)
    print(f"Đã nhập {len(docs)} ghi chú; giữ nguyên mọi trạng thái duyệt. Dựng lại index để áp dụng.")


if __name__ == "__main__":
    main()
