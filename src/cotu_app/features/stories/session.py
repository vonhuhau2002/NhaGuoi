"""Story selection state and demo UID mapping."""
from .characters import CHARACTERS

SIMULATED_UIDS = {
    "DEMO-00": "elder",
    **{f"DEMO-{i:02d}": f"person_{i}" for i in range(1, 6)},
}


class StorySession:
    """Trạng thái dùng chung cho nút chọn và sự kiện UID."""

    def __init__(self):
        self.character_id = "elder"
        self.story_id = "elder"

    def select_character(self, character_id):
        if character_id not in CHARACTERS:
            raise ValueError("Nhân vật không tồn tại")
        self.character_id = character_id
        self.story_id = character_id

    def scan_uid(self, uid):
        normalized = uid.strip().upper()
        character_id = SIMULATED_UIDS.get(normalized)
        if character_id is None:
            return False
        self.select_character(character_id)
        return True

    def elder_tells(self, story_id):
        if self.character_id != "elder" or story_id not in CHARACTERS or story_id == "elder":
            raise ValueError("Hãy chọn Già làng và một câu chuyện của nhân vật phụ")
        self.story_id = story_id

    @property
    def story(self):
        return CHARACTERS[self.story_id]["story"]
