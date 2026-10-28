"""Story knowledge and curated answer results."""
from dataclasses import dataclass

@dataclass
class Knowledge:
    video_sha256: str
    segments: list
    questions: list
    source: str


@dataclass
class Answer:
    text: str
    approved: bool = False
    suggestions: tuple = ()
    character_id: str | None = None
    source: str | None = None
