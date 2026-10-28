"""Nhà Rông Cơ Tu: sáu nhân vật và mô phỏng RFID, chưa dùng phần cứng.

Chạy: python3 -m nharong.app_rfid
Kiểm tra logic không cần màn hình: python3 -m nharong.app_rfid --self-test
Nội dung năm nhân vật phụ được dùng lại từ app2.py.
"""

import sys
import tkinter as tk
from tkinter import ttk

from cotu_app.features.stories.characters import VILLAGERS


CHARACTERS = {
    "elder": {
        "name": "Già làng",
        "role": "Người dẫn chuyện",
        "story": (
            "Xin chào các bạn nhỏ! Ta là Già làng.\n\n"
            "Hãy chọn một người bạn để khám phá câu chuyện của họ. "
            "Khi chọn Già làng, các bạn có thể chọn câu chuyện bên dưới "
            "để ta kể lại."
        ),
    },
    **{f"person_{i}": dict(person) for i, person in enumerate(VILLAGERS, 1)},
}

# UID giả lập hoàn toàn, không phải UID của thẻ thật.
# UID thẻ thật được lưu riêng trong cấu hình cục bộ, không đưa vào ví dụ.
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


class NhaRongRFIDApp:
    def __init__(self, root):
        self.root = root
        self.session = StorySession()
        root.title("Nhà Rông Cơ Tu — Giả lập RFID")
        root.geometry("1000x700")
        root.minsize(640, 480)
        root.configure(bg="#EFE2CB")
        root.bind("<F11>", self.toggle_fullscreen)
        root.bind("<Escape>", lambda event: root.attributes("-fullscreen", False))

        outer = ttk.Frame(root, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="NHÀ RÔNG CƠ TU", font=("DejaVu Sans", 20, "bold")).pack()
        ttk.Label(outer, text="CHẾ ĐỘ GIẢ LẬP • Chưa kết nối đầu đọc RFID • Truyện mẫu").pack(pady=(3, 10))

        cards = ttk.Frame(outer)
        cards.pack(fill="x")
        self.buttons = {}
        uid_by_character = {value: key for key, value in SIMULATED_UIDS.items()}
        for index, (character_id, person) in enumerate(CHARACTERS.items()):
            row, col = divmod(index, 3)
            cards.columnconfigure(col, weight=1)
            button = ttk.Button(
                cards,
                text=f"{person['name']}\n{uid_by_character[character_id]}",
                command=lambda cid=character_id: self.select_character(cid),
            )
            button.grid(row=row, column=col, sticky="nsew", padx=3, pady=3, ipady=7)
            self.buttons[character_id] = button

        scan = ttk.LabelFrame(outer, text="Giả lập quét thẻ", padding=8)
        scan.pack(fill="x", pady=8)
        scan.columnconfigure(1, weight=1)
        ttk.Label(scan, text="UID:").grid(row=0, column=0, padx=(0, 6))
        self.uid = tk.StringVar(value="DEMO-01")
        entry = ttk.Entry(scan, textvariable=self.uid)
        entry.grid(row=0, column=1, sticky="ew")
        entry.bind("<Return>", self.scan_uid)
        ttk.Button(scan, text="Quét giả lập", command=self.scan_uid).grid(row=0, column=2, padx=(6, 0))
        ttk.Label(scan, text="Dùng DEMO-00 đến DEMO-05; có thể quét lại cùng UID.").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(5, 0)
        )

        self.elder_controls = ttk.Frame(outer)
        self.elder_controls.pack(fill="x", pady=(0, 8))
        self.villager_ids = [cid for cid in CHARACTERS if cid != "elder"]
        self.story_choice = ttk.Combobox(
            self.elder_controls, state="readonly",
            values=[CHARACTERS[cid]["name"] for cid in self.villager_ids],
        )
        self.story_choice.current(0)
        self.story_choice.pack(side="left", fill="x", expand=True)
        self.elder_button = ttk.Button(self.elder_controls, text="Già làng kể truyện này", command=self.elder_tells)
        self.elder_button.pack(side="left", padx=(6, 0))

        self.title = ttk.Label(outer, font=("DejaVu Sans", 14, "bold"), wraplength=600)
        self.title.pack(fill="x", pady=4)
        self.narrator = ttk.Label(outer)
        self.narrator.pack(fill="x", pady=(0, 6))
        text_frame = ttk.Frame(outer)
        text_frame.pack(fill="both", expand=True)
        self.text = tk.Text(text_frame, wrap="word", state="disabled", height=6,
                            font=("DejaVu Sans", 12), padx=12, pady=12, bg="#FFF8EB")
        scrollbar = ttk.Scrollbar(text_frame, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.status = tk.StringVar(value="Sẵn sàng. Chọn nhân vật hoặc nhập UID giả lập.")
        ttk.Label(outer, textvariable=self.status, wraplength=600).pack(fill="x", pady=(8, 0))
        self.render()

    def render(self):
        character = CHARACTERS[self.session.character_id]
        story = CHARACTERS[self.session.story_id]
        self.title.configure(text=f"Câu chuyện: {story['name']}")
        self.narrator.configure(text=f"Người kể: {character['name']}")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.session.story)
        self.text.configure(state="disabled")
        self.text.yview_moveto(0)
        for cid, button in self.buttons.items():
            marker = "✓ " if cid == self.session.character_id else ""
            demo_uid = next(uid for uid, value in SIMULATED_UIDS.items() if value == cid)
            button.configure(text=f"{marker}{CHARACTERS[cid]['name']}\n{demo_uid}")
        is_elder = self.session.character_id == "elder"
        self.elder_button.configure(state="normal" if is_elder else "disabled")
        self.story_choice.configure(state="readonly" if is_elder else "disabled")

    def select_character(self, character_id):
        self.session.select_character(character_id)
        self.render()
        self.status.set(f"Đã chọn {CHARACTERS[character_id]['name']} bằng nút bấm.")

    def scan_uid(self, event=None):
        uid = self.uid.get().strip().upper()
        if not self.session.scan_uid(uid):
            self.status.set(f"UID chưa đăng ký: {uid or '(trống)'}. Hãy dùng DEMO-00 đến DEMO-05.")
            return
        self.render()
        self.status.set(f"Quét giả lập {uid}: {CHARACTERS[self.session.character_id]['name']}.")

    def elder_tells(self):
        index = self.story_choice.current()
        if index < 0:
            return
        self.session.elder_tells(self.villager_ids[index])
        self.render()
        self.status.set("Già làng đang kể câu chuyện đã chọn bằng văn bản.")

    def toggle_fullscreen(self, event=None):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))


def self_test():
    session = StorySession()
    assert len(CHARACTERS) == len(SIMULATED_UIDS) == 6
    for uid, cid in list(SIMULATED_UIDS.items()) + list(reversed(list(SIMULATED_UIDS.items()))):
        assert session.scan_uid(f" {uid.lower()} ")
        assert session.character_id == session.story_id == cid
        assert session.story == CHARACTERS[cid]["story"]
    assert len({person["story"] for person in CHARACTERS.values()}) == 6
    session.scan_uid("DEMO-00")
    for cid in list(CHARACTERS)[1:]:
        session.elder_tells(cid)
        assert session.character_id == "elder" and session.story == CHARACTERS[cid]["story"]
    before = (session.character_id, session.story_id, session.story)
    for uid in ("", "UNKNOWN", "1001"):
        assert not session.scan_uid(uid)
        assert before == (session.character_id, session.story_id, session.story)
    assert session.scan_uid("DEMO-02") and session.scan_uid("DEMO-02")
    assert session.story_id == "person_2"
    try:
        session.elder_tells("person_1")
    except ValueError:
        pass
    else:
        raise AssertionError("Nhân vật phụ không được dùng chế độ Già làng")
    print("PASS: 6 UID, chuyển truyện hai chiều, Già làng kể 5 truyện, UID lạ và quét lại.")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        root = tk.Tk()
        app = NhaRongRFIDApp(root)
        root.mainloop()
