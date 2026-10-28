"""Bàn phím cảm ứng trong cùng cửa sổ Tk, dùng được khi toàn màn hình."""

import tkinter as tk
import unicodedata


TONES = {"Sắc": "\u0301", "Huyền": "\u0300", "Hỏi": "\u0309",
         "Ngã": "\u0303", "Nặng": "\u0323", "Bỏ dấu": ""}
TONE_MARKS = set(TONES.values()) - {""}


def toned_vowel(character, tone):
    """Đổi dấu thanh của một nguyên âm; giữ dấu mũ/móc và chữ hoa."""
    decomposed = unicodedata.normalize("NFD", character)
    if not decomposed or decomposed[0].lower() not in "aeiouy":
        return character
    base = "".join(part for part in decomposed if part not in TONE_MARKS)
    return unicodedata.normalize("NFC", base + tone)


class TouchKeyboard(tk.Frame):
    def __init__(self, parent, entry, submit, *, before=None, hide_when_open=(), **kwargs):
        super().__init__(parent, bg="#DFE8DC", padx=4, pady=4, **kwargs)
        self.entry = entry
        self.submit = submit
        self.before = before
        self.hide_when_open = hide_when_open
        self.hidden_layout = []
        self.shift = False
        self.numbers = False
        self.vietnamese = False
        self.rows = []
        for index in range(3):
            row = tk.Frame(self, bg=self["bg"])
            row.grid(row=index, column=0, sticky="nsew")
            self.rowconfigure(index, weight=1, uniform="keyboard_rows", minsize=56)
            self.rows.append(row)
        self.columnconfigure(0, weight=1)
        self.build_letters()

        controls = tk.Frame(self, bg=self["bg"])
        controls.grid(row=3, column=0, sticky="nsew")
        self.rowconfigure(3, weight=1, uniform="keyboard_rows", minsize=56)
        self.number_key = self.key(controls, "123", self.toggle_numbers, 0, size=12)
        self.vietnamese_key = self.key(controls, "Dấu Việt", self.toggle_vietnamese, 1, size=12, weight=2)
        self.key(controls, "←", lambda: self.move(-1), 2, size=16)
        self.key(controls, "→", lambda: self.move(1), 3, size=16)
        self.key(controls, "Xóa hết", self.clear, 4, weight=2, size=12)
        self.key(controls, "Dấu cách", lambda: self.insert(" "), 5, weight=3, size=12)
        self.key(controls, "Ẩn", self.hide, 6, size=12)
        self.key(controls, "Gửi", self.send, 7, weight=2, size=14, primary=True)
        tk.Label(self, text="Dấu Việt: chọn chữ và dấu thanh • Ví dụ: ơ + Hỏi → ở",
                 bg=self["bg"], fg="#263E37", font=("DejaVu Sans", 10)).grid(row=4, column=0)

    def key(self, row, text, command, column, *, size=20, weight=1, primary=False):
        row.columnconfigure(column, weight=weight, uniform="keys")
        row.rowconfigure(0, weight=1)
        button = tk.Button(row, text=text, command=command, takefocus=False,
                           font=("DejaVu Sans", size, "bold"), bg="#27705A" if primary else "#FFFDFA",
                           fg="white" if primary else "#263E37", activebackground="#F8E5B7",
                           activeforeground="#263E37", relief="flat", padx=2, pady=4,
                           borderwidth=0, highlightthickness=1, highlightbackground="#C3D0BD")
        button.grid(row=0, column=column, sticky="nsew", padx=3, pady=3)
        return button

    def build_letters(self):
        for row in self.rows:
            for column in range(row.grid_size()[0]):
                row.columnconfigure(column, weight=0, minsize=0, uniform="")
            for widget in row.winfo_children():
                widget.destroy()
        if self.vietnamese:
            for index, letter in enumerate("ăâêôơưđ"):
                self.key(self.rows[0], letter.upper() if self.shift else letter,
                         lambda value=letter: self.type_letter(value), index)
            self.key(self.rows[0], "⌫", self.backspace, 7)
            for index, (label, tone) in enumerate(TONES.items()):
                self.key(self.rows[1], label, lambda value=tone: self.add_tone(value), index, size=15)
            self.key(self.rows[2], "abc" if self.shift else "ABC", self.toggle_shift, 0, size=15)
            for index, letter in enumerate("aeiouy", 1):
                self.key(self.rows[2], letter.upper() if self.shift else letter,
                         lambda value=letter: self.type_letter(value), index)
            self.key(self.rows[2], "?", lambda: self.insert("?"), 7)
            return
        layout = ("1234567890", "!?.,:;()-/", "+=@#%&*_\"'") if self.numbers else (
            "qwertyuiop", "asdfghjkl", "zxcvbnm,.")
        for row_index, letters in enumerate(layout):
            row = self.rows[row_index]
            offset = 0
            if row_index == 2:
                self.key(row, "abc" if self.shift else "ABC", self.toggle_shift, 0, size=13)
                offset = 1
            for column, letter in enumerate(letters, offset):
                self.key(row, letter.upper() if self.shift else letter,
                         lambda value=letter: self.type_letter(value), column)
            if row_index == 0:
                self.key(row, "⌫", self.backspace, len(letters))

    def show(self):
        if self.winfo_manager():
            return
        self.hidden_layout = []
        for widget in (*self.hide_when_open, self.before):
            if widget is None or widget.winfo_manager() != "pack":
                continue
            siblings = widget.master.pack_slaves()
            index = siblings.index(widget)
            following = siblings[index + 1] if index + 1 < len(siblings) else None
            self.hidden_layout.append((widget, widget.pack_info(), following))
            widget.pack_forget()
        self.pack(fill="both", expand=True, pady=(2, 0))

    def hide(self):
        self.pack_forget()
        for widget, options, following in reversed(self.hidden_layout):
            if following is not None and following.winfo_manager() == "pack":
                options["before"] = following
            widget.pack(**options)
        self.hidden_layout = []

    def toggle(self):
        if self.winfo_manager():
            self.hide()
        else:
            self.show()

    def delete_selection(self):
        if self.entry.selection_present():
            self.entry.delete("sel.first", "sel.last")
            return True
        return False

    def insert(self, text):
        self.delete_selection()
        self.entry.insert("insert", text)
        self.entry.focus_set()
        self.entry.xview("insert")

    def type_letter(self, letter):
        self.insert(letter.upper() if self.shift else letter)

    def backspace(self):
        if not self.delete_selection():
            cursor = self.entry.index("insert")
            if cursor > 0:
                self.entry.delete(cursor - 1, cursor)
        self.entry.focus_set()
        self.entry.xview("insert")

    def clear(self):
        self.entry.delete(0, "end")
        self.entry.focus_set()

    def move(self, direction):
        cursor = self.entry.index("insert")
        self.entry.selection_clear()
        self.entry.icursor(max(0, min(len(self.entry.get()), cursor + direction)))
        self.entry.focus_set()
        self.entry.xview("insert")

    def add_tone(self, tone):
        cursor = self.entry.index("insert")
        if cursor > 0:
            original = self.entry.get()[cursor - 1]
            replacement = toned_vowel(original, tone)
            if replacement != original:
                self.entry.selection_clear()
                self.entry.delete(cursor - 1, cursor)
                self.entry.insert(cursor - 1, replacement)
                self.entry.icursor(cursor)
        self.entry.focus_set()

    def toggle_shift(self):
        self.shift = not self.shift
        self.build_letters()

    def toggle_numbers(self):
        self.numbers = not self.numbers or self.vietnamese
        self.vietnamese = False
        self.number_key.configure(text="ABC" if self.numbers else "123")
        self.vietnamese_key.configure(text="Dấu Việt")
        self.build_letters()

    def toggle_vietnamese(self):
        self.vietnamese = not self.vietnamese
        self.numbers = False
        self.number_key.configure(text="123")
        self.vietnamese_key.configure(text="ABC" if self.vietnamese else "Dấu Việt")
        self.build_letters()

    def send(self):
        self.hide()
        self.submit()
