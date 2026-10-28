"""Curated video/document question banks and provenance checks."""
import hashlib
import re
from cotu_app.core.files import read_json, resolve_path
from cotu_app.core.text import normalize
from .characters import CHARACTERS


def question_title(item):
    """Use an existing approved wording for short touchscreen rows."""
    return min([item["question"], *item.get("aliases", [])], key=len)

def load_questions(path, digest):
    if path is None:
        return []
    data = read_json(path)
    if not isinstance(data, dict) or data.get("video_sha256") != digest:
        raise ValueError("Bộ hỏi đáp chưa được gắn đúng SHA256 của video. Xem HUONG_DAN_VIDEO.md.")
    return validate_questions(data.get("questions"))


def validate_questions(questions):
    if not isinstance(questions, list):
        raise ValueError("questions phải là danh sách câu hỏi.")
    seen = set()
    assigned = []
    for item in questions:
        if not isinstance(item, dict) or any(
            not isinstance(item.get(key), str) or not item[key].strip()
            for key in ("question", "answer")
        ):
            raise ValueError("Mỗi câu cần question và answer không rỗng.")
        aliases = item.get("aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(a, str) or not normalize(a) for a in aliases):
            raise ValueError("aliases phải là danh sách cách hỏi tương đương.")
        owner = item.get("character_id")
        if "character_id" in item and (not isinstance(owner, str) or owner not in CHARACTERS):
            raise ValueError("character_id của câu hỏi phải là một trong sáu nhân vật.")
        assigned.append("character_id" in item)
        for wording in [item["question"], *aliases]:
            normalized = normalize(wording)
            if not normalized or normalized in seen:
                raise ValueError("Có câu hỏi/cách hỏi trùng nhau hoặc không có chữ trong bộ hỏi đáp.")
            seen.add(normalized)
    if any(assigned) and not all(assigned):
        raise ValueError("Nếu phân câu hỏi theo nhân vật, mọi câu cần character_id.")
    return questions


def parse_numbered_questions(text):
    """Đọc nguyên văn các khối Câu N: câu hỏi, theo sau là lời đáp."""
    headers = list(re.finditer(r"^Câu\s+(\d+)\s*:\s*([^\n]+)", text, re.M))
    if not headers:
        raise ValueError("Tài liệu cần các mục Câu 1:, Câu 2: ... và lời đáp.")
    result = {}
    for index, header in enumerate(headers):
        number = int(header[1])
        answer = text[header.end():headers[index + 1].start()
                      if index + 1 < len(headers) else len(text)].strip()
        if number < 1 or number in result or not answer:
            raise ValueError("Số câu trong tài liệu bị trùng/không hợp lệ hoặc thiếu lời đáp.")
        result[number] = (header[2].strip(), answer)
    return result


def load_document_questions(path):
    """Kiểm tra nguồn TXT riêng, không gắn nội dung tài liệu thành lời video."""
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("source_file"), str) or not data["source_file"]:
        raise ValueError("Bộ hỏi đáp tài liệu cần source_file.")
    source_path = resolve_path(path, data["source_file"])
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if data.get("source_sha256") != digest:
        raise ValueError(f"Tài liệu {source_path.name} đã thay đổi; cần cập nhật lại bộ hỏi đáp theo nguồn mới (SHA256).")
    source_questions = parse_numbered_questions(source_path.read_text(encoding="utf-8-sig"))
    questions = validate_questions(data.get("questions"))
    seen = set()
    loaded = []
    for item in questions:
        number = item.get("source_question")
        if (isinstance(number, bool) or not isinstance(number, int) or number in seen
                or source_questions.get(number) != (item["question"], item["answer"])):
            raise ValueError(f"Câu hỏi/lời đáp chưa khớp nguyên văn tài liệu {source_path.name}.")
        if "character_id" not in item:
            raise ValueError("Câu hỏi tài liệu cần character_id của người trả lời.")
        seen.add(number)
        loaded.append({**item, "source_type": "document",
                       "source_label": f"{source_path.name} — Câu {number}"})
    if seen != set(source_questions):
        raise ValueError(f"Bộ hỏi đáp chưa có đủ các câu trong {source_path.name}.")
    return loaded


def load_story_questions(config_path, config, story_id, digest):
    story = config["stories"][story_id]
    questions = load_questions(resolve_path(config_path, story.get("questions")), digest)
    documents = config.get("document_questions", [])
    if documents:
        questions = [{**item, "character_id": item.get("character_id", story_id)} for item in questions]
        for document in documents:
            questions.extend(load_document_questions(resolve_path(config_path, document)))
        validate_questions(questions)
    return questions
