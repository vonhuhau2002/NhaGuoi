"""One place for source, resources, configuration and writable data paths.

Installed releases continue to understand the shared directory created by v1.0.0.
"""

import os
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]
_installed_data = os.environ.get("NHARONG_DATA_DIR")
DATA = Path(_installed_data).resolve() if _installed_data else BASE / "data"
CONFIG_DIR = DATA if _installed_data else BASE / "config"
CHATBOT_CONFIG_DIR = BASE / "config/chatbot"
IMAGES_DIR = BASE / "resources/images"
MODEL_DIR = BASE / ".venv-video/models/zerotts"
CACHE_DIR = DATA / "cache" if _installed_data else BASE / "var/cache"
RUN_DIR = DATA / "run" if _installed_data else BASE / "var/run"
TTS_CACHE_DIR = (DATA / ".tts_cache" if _installed_data and (DATA / ".tts_cache").is_dir()
                 else CACHE_DIR / "tts")


def video_cache_dir(config_path):
    path = Path(config_path).resolve()
    if path == (CONFIG_DIR / "video_stories.json").resolve():
        old = DATA / ".video_cache"
        return old if _installed_data and old.is_dir() else CACHE_DIR / "video"
    # Keep independent caches for user-supplied configurations and test fixtures.
    return path.parent / ".video_cache"
