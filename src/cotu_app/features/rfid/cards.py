"""Persistent UID to character assignment."""
import json
from cotu_app.features.stories.characters import CHARACTERS

def load_cards(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or any(
        not isinstance(uid, str) or not uid.isdecimal() or cid not in CHARACTERS
        for uid, cid in data.items()
    ):
        raise ValueError("File gán thẻ không đúng định dạng")
    if len(set(data.values())) != len(data):
        raise ValueError("Một nhân vật đang được gán nhiều thẻ trong file")
    return data


def assign_card(cards, uid, cid, path):
    """Mỗi nhân vật một thẻ; chỉ cập nhật bộ nhớ sau khi lưu thành công."""
    uid = str(uid).strip()
    if not uid.isdecimal() or cid not in CHARACTERS:
        raise ValueError("UID hoặc nhân vật không hợp lệ")
    updated = {key: value for key, value in cards.items() if value != cid and key != uid}
    updated[uid] = cid
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return updated
