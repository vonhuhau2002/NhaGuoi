"""Application configuration validation without UI or device access."""
from cotu_app.core.paths import CONFIG_DIR
from cotu_app.core.files import read_json
from cotu_app.features.stories.characters import CHARACTERS
from cotu_app.features.gpio.buttons import button_mapping
from cotu_app.features.chatbot.config import chatbot_options

CONFIG = CONFIG_DIR / "video_stories.json"

def load_config(path):
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("stories"), dict):
        raise ValueError("Cấu hình cần có đối tượng stories.")
    if set(data["stories"]) != set(CHARACTERS):
        raise ValueError("stories cần đủ elder và person_1 đến person_5.")
    documents = data.get("document_questions", [])
    if not isinstance(documents, list) or any(
        not isinstance(value, str) or not value.strip() for value in documents
    ):
        raise ValueError("document_questions phải là danh sách đường dẫn bộ hỏi đáp tài liệu.")
    for story in data["stories"].values():
        if not isinstance(story, dict) or any(
            not isinstance(story.get(key, ""), str)
            for key in ("video", "transcript", "questions")
        ):
            raise ValueError("video, transcript, questions phải là đường dẫn dạng chuỗi.")
    seconds = data.get("record_seconds", 8)
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 2 <= seconds <= 30:
        raise ValueError("record_seconds phải từ 2 đến 30 giây.")
    if not isinstance(data.get("whisper_model", "base"), str) or not data.get("whisper_model", "base"):
        raise ValueError("whisper_model cần tên mô hình hoặc đường dẫn mô hình.")
    device = data.get("microphone")
    if device is not None and (isinstance(device, bool) or not isinstance(device, (str, int))):
        raise ValueError("microphone cần null, số thiết bị hoặc tên mic.")
    button_mapping(data, CHARACTERS)
    chatbot_options(data)
    return data
