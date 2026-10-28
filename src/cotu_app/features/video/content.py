"""Load video transcripts and cache recognition results."""
import hashlib
import json
from pathlib import Path
import re
from cotu_app.core.files import read_json, write_json, resolve_path
from cotu_app.core.paths import video_cache_dir
from cotu_app.features.stories.questions import load_story_questions
from cotu_app.features.stories.models import Knowledge

def video_digest(path, check=lambda: None):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            check()
            digest.update(chunk)
    check()
    return digest.hexdigest()


def read_transcript(path):
    """Nạp TXT hoặc SRT đã duyệt. TXT không có mốc thời gian."""
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig").strip()
    if path.suffix.lower() != ".srt":
        return [{"start": None, "text": line.strip()} for line in text.splitlines() if line.strip()]
    segments = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = block.splitlines()
        for index, line in enumerate(lines):
            match = re.match(r"(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})\s*-->", line)
            if match:
                hours, minutes, seconds, millis = map(int, match.groups())
                caption = " ".join(lines[index + 1:]).strip()
                if caption:
                    segments.append({"start": hours * 3600 + minutes * 60 + seconds + millis / 1000,
                                     "text": caption})
                break
    if text and not segments:
        raise ValueError("Không đọc được mốc thời gian trong phụ đề SRT.")
    return segments


def learn_video(config_path, config, story_id, transcribe, check=lambda: None):
    story = config["stories"][story_id]
    video = resolve_path(config_path, story.get("video"))
    if video is None or video.suffix.lower() != ".mp4" or not video.is_file():
        raise ValueError("Chưa có MP4 cho nhân vật này. Bấm Chọn video trong mục Thiết lập.")
    digest = video_digest(video, check)
    # Bộ câu hỏi chỉ định nhưng sai/thiếu phải báo lỗi, không dùng âm thầm bộ khác.
    questions = load_story_questions(config_path, config, story_id, digest)
    transcript = resolve_path(config_path, story.get("transcript"))
    if transcript:
        segments = read_transcript(transcript)
        source = "bộ hỏi đáp và bản lời thoại cung cấp" if questions else "bản lời thoại cung cấp"
    elif questions:
        # Dùng ngay bộ đã duyệt; không bắt buộc tải ASR hoặc chờ học lại video.
        segments, source = [], "bộ hỏi đáp đã duyệt"
    else:
        settings = {"video": digest, "model": config.get("whisper_model", "base"),
                    "language": "vi", "version": 1}
        key = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
        cache = video_cache_dir(config_path) / f"{key}.json"
        try:
            saved = read_json(cache)
            segments = saved["segments"]
            if saved["settings"] != settings or not isinstance(segments, list) or any(
                not isinstance(s, dict) or not isinstance(s.get("text"), str)
                or not isinstance(s.get("start"), (int, float)) for s in segments
            ):
                raise ValueError("Cache không hợp lệ")
        except (OSError, ValueError, KeyError, TypeError):
            segments = transcribe(video)
            check()
            if not segments:
                raise ValueError("Không nhận được lời thoại. Kiểm tra âm thanh hoặc cung cấp TXT/SRT.")
            write_json(cache, {"settings": settings, "segments": segments})
        source = "nhận dạng tự động, cần kiểm tra"
    check()
    if not segments and not questions:
        raise ValueError("Lời thoại và bộ hỏi đáp đều rỗng.")
    documents = sorted({item["source_label"].rsplit(" — Câu ", 1)[0]
                        for item in questions if item.get("source_type") == "document"})
    if documents:
        source += "; tài liệu bổ sung: " + ", ".join(documents)
    return Knowledge(digest, segments, questions, source)
