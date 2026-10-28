"""Chuyển TXT dạng Câu N: ... thành bộ hỏi đáp có nguồn, giữ nguyên lời đáp."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "src"))

from cotu_app.features.stories.characters import CHARACTERS
from cotu_app.features.stories.questions import parse_numbered_questions, validate_questions
from cotu_app.core.files import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--character", choices=list(CHARACTERS), default="elder")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("File nguồn và file hỏi đáp phải khác nhau.")
    parsed = parse_numbered_questions(source.read_text(encoding="utf-8-sig"))
    previous = json.loads(output.read_text(encoding="utf-8")) if output.is_file() else {}
    # Chỉ giữ cách hỏi cũ khi câu gốc và người trả lời giữ nguyên.
    aliases = {(item["question"], item.get("character_id")): item.get("aliases", [])
               for item in previous.get("questions", [])}
    questions = [dict(question=question, answer=answer, character_id=args.character,
                      source_question=number, aliases=aliases.get((question, args.character), []))
                 for number, (question, answer) in parsed.items()]
    validate_questions(questions)
    data = dict(title=previous.get("title", source.stem),
                source_file=os.path.relpath(source, output.parent),
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                questions=questions)
    write_json(output, data)
    print(f"Đã nạp {len(questions)} câu, giữ nguyên lời đáp từ {source.name}.")
    print(f"Bộ hỏi đáp: {output}")


if __name__ == "__main__":
    main()
