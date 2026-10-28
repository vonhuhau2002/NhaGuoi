from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import re


from cotu_app.core.paths import BASE, CHATBOT_CONFIG_DIR

ROOT = BASE / "data/chatbot"


def load_env(path=None):
    """Small KEY=VALUE reader; environment wins. No interpolation or execution."""
    if path is None:
        path = Path(os.environ.get("NHARONG_CHATBOT_ENV", str(CHATBOT_CONFIG_DIR / ".env")))
    if not path.exists():
        return
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key.strip()):
            raise ValueError(f".env dòng {number}: cần KEY=VALUE.")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default="", repr=False)
    model: str = "gemini-3.1-flash-lite"
    thinking_level: str = "minimal"
    timeout: float = 15
    total_timeout: float = 35
    min_interval: float = 6
    max_output_tokens: int = 384
    context_chars: int = 6000
    cache_size: int = 64
    cache_ttl: float = 900

    def __post_init__(self):
        if not re.fullmatch(r"gemini-[a-zA-Z0-9.\-]+", self.model):
            raise ValueError("GEMINI_MODEL phải là model ID Gemini, không phải URL.")
        if self.thinking_level not in {"minimal", "low", "medium", "high", "auto"}:
            raise ValueError("Thinking level không hợp lệ.")
        for name in ("timeout", "total_timeout", "cache_ttl", "min_interval"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0 or (name != "min_interval" and value == 0):
                raise ValueError(f"Cấu hình {name} không hợp lệ.")
        if self.timeout > 60 or self.total_timeout > 120:
            raise ValueError("Timeout socket ≤ 60 s; deadline ≤ 120 s.")
        if not all(isinstance(value, int) and value > 0 for value in (
                self.max_output_tokens, self.context_chars, self.cache_size)):
            raise ValueError("Ngân sách token/context và dung lượng cache phải là số nguyên dương.")

    @classmethod
    def from_env(cls):
        load_env()
        return cls(
            api_key=os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
            thinking_level=os.getenv("GEMINI_THINKING_LEVEL", "minimal"),
            timeout=float(os.getenv("CHATBOT_TIMEOUT_SECONDS", "15")),
            total_timeout=float(os.getenv("CHATBOT_TOTAL_TIMEOUT_SECONDS", "35")),
            min_interval=float(os.getenv("CHATBOT_MIN_INTERVAL_SECONDS", "6")),
        )


def chatbot_options(config):
    options = config.get("chatbot", {})
    if not isinstance(options, dict):
        raise ValueError("chatbot phải là đối tượng cấu hình.")
    enabled, mode = options.get("enabled", True), options.get("mode", "approved")
    if not isinstance(enabled, bool) or mode not in {"approved", "research"}:
        raise ValueError("chatbot cần enabled true/false và mode approved/research.")
    return {"enabled": enabled, "mode": mode}
