"""Validate the six configured voices and reading rates."""
from functools import lru_cache
import json
from cotu_app.core.paths import CONFIG_DIR
from cotu_app.features.stories.characters import CHARACTERS

VOICES_FILE = CONFIG_DIR / "tts_voices.json"

@lru_cache(maxsize=1)
def load_voice_styles():
    voices = json.loads(VOICES_FILE.read_text(encoding="utf-8"))
    if not isinstance(voices, dict) or set(voices) != set(CHARACTERS):
        raise ValueError("tts_voices.json cần đủ sáu nhân vật.")
    styles = {}
    for cid, value in voices.items():
        if not isinstance(value, dict) or set(value) != {"voice", "rate"}:
            raise ValueError(f"Giọng {cid} cần voice và rate.")
        voice, rate = value["voice"], value["rate"]
        if not isinstance(voice, str) or not voice or voice == "random_male":
            raise ValueError(f"Giọng {cid} không hợp lệ.")
        if isinstance(rate, bool) or not isinstance(rate, (float, int)) or not 0.8 <= rate <= 1.15:
            raise ValueError(f"Tốc độ đọc của {cid} cần từ 0.8 đến 1.15.")
        styles[cid] = (voice, float(rate))
    if len(set(styles.values())) != len(styles):
        raise ValueError("Mỗi nhân vật cần một kiểu giọng riêng.")
    return styles


def voice_for(character_id):
    return load_voice_styles()[character_id]
