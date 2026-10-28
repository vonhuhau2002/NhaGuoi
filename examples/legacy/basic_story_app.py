
import tkinter as tk
from tkinter import messagebox

# ==========================================
# NHA RONG CO TU - PHIEN BAN GIAO DIEN 1
# Python + Tkinter
# ==========================================

BG = "#F4E8D3"
BROWN = "#704323"
DARK = "#422B1D"
GOLD = "#D7A65B"
WHITE = "#FFFDF8"
GREEN = "#55734B"
MUTED = "#866F5A"

# Cac cau chuyen mau de thu nghiem giao dien.
# Sau nay thay bang noi dung da duoc xac minh.
CHARACTERS = [
    {
        "name": "Nhan vat 1",
        "role": "Nguoi giu lua",
        "story": (
            "Chao cac ban! Toi la Nhan vat 1.\n\n"
            "DAY LA CAU CHUYEN MAU SO 1.\n\n"
            "Trong buon lang, moi nguoi cung "
            "giu gin nep song va chia se cong viec. "
            "Hay cung nhau tim hieu nhung gia tri "
            "van hoa cua nguoi Co Tu!"
        ),
        "color": "#A95D36",
    },
    {
        "name": "Nhan vat 2",
        "role": "Nguoi dan duong",
        "story": (
            "Chao cac ban! Toi la Nhan vat 2.\n\n"
            "DAY LA CAU CHUYEN MAU SO 2.\n\n"
            "Khi di trong rung, chung ta can "
            "quan sat, hoc hoi va ton trong "
            "thien nhien. Moi chuyen di deu "
            "mang lai mot bai hoc moi."
        ),
        "color": "#55734B",
    },
    {
        "name": "Nhan vat 3",
        "role": "Nguoi det vai",
        "story": (
            "Chao cac ban! Toi la Nhan vat 3.\n\n"
            "DAY LA CAU CHUYEN MAU SO 3.\n\n"
            "Nhung hoa van va mau sac co the "
            "ke nhieu cau chuyen ve con nguoi, "
            "gia dinh va que huong. Chung ta "
            "hay cung nhau gin giu nghe truyen thong."
        ),
        "color": "#9B7444",
    },
    {
        "name": "Nhan vat 4",
        "role": "Nguoi lam nhac cu",
        "story": (
            "Chao cac ban! Toi la Nhan vat 4.\n\n"
            "DAY LA CAU CHUYEN MAU SO 4.\n\n"
            "Am nhac giup moi nguoi gan ket "
            "voi nhau. Moi nhac cu deu co "
            "cach tao ra am thanh rieng. "
            "Chung ta hay cung lang nghe!"
        ),
        "color": "#80609A",
    },
    {
        "name": "Nhan vat 5",
        "role": "Nguoi ke chuyen",
        "story": (
            "Chao cac ban! Toi la Nhan vat 5.\n\n"
            "DAY LA CAU CHUYEN MAU SO 5.\n\n"
            "Nhung cau chuyen duoc nguoi lon "
            "truyen lai giup the he tre hieu "
            "hon ve que huong. Hay lang nghe "
            "va hoc hoi tu nhung nguoi di truoc!"
        ),
        "color": "#39768A",
    },
]


class NhaRongApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nha Rong Co Tu")
        self.root.configure(bg=BG)
        self.root.geometry("800x480")
        self.root.minsize(640, 400)

        self.selected = None
        self.fullscreen = False

        self.build_interface()
        self.show_welcome()

        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)

    def build_interface(self):
        # Thanh tieu de
        header = tk.Frame(self.root, bg=BROWN, height=66)
        header.pack(fill="x")
        header.pack_propagate(False)

        emblem = tk.Label(
            header,
            text="NR",
            font=("DejaVu Sans", 20, "bold"),
            bg=GOLD,
            fg=DARK,
            width=4,
        )
        emblem.pack(side="left", padx=(12, 10), pady=8)

        title_box = tk.Frame(header, bg=BROWN)
        title_box.pack(side="left", fill="y", pady=8)

        tk.Label(
            title_box,
            text="NHA RONG CO TU",
            font=("DejaVu Sans", 17, "bold"),
            bg=BROWN,
            fg=WHITE,
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="KHONG GIAN VAN HOA VA KE CHUYEN",
            font=("DejaVu Sans", 8),
            bg=BROWN,
            fg="#F0D9B5",
        ).pack(anchor="w")

        fullscreen_btn = tk.Button(
            header,
            text="Toan man hinh",
            font=("DejaVu Sans", 9),
            bg="#875B38",
            fg=WHITE,
            activebackground=GOLD,
            activeforeground=DARK,
            relief="flat",
            padx=10,
            pady=8,
            command=self.toggle_fullscreen,
        )
        fullscreen_btn.pack(side="right", padx=12, pady=12)

        # Loi chao
        welcome = tk.Frame(self.root, bg=BG)
        welcome.pack(fill="x", padx=16, pady=(10, 5))

        tk.Label(
            welcome,
            text="CHAO MUNG DEN VOI BUON LANG!",
            font=("DejaVu Sans", 13, "bold"),
            bg=BG,
            fg=BROWN,
        ).pack(anchor="w")

        tk.Label(
            welcome,
            text="Chon mot nhan vat de nghe gia lang ke chuyen.",
            font=("DejaVu Sans", 10),
            bg=BG,
            fg=MUTED,
        ).pack(anchor="w", pady=(2, 0))

        # Khu vuc 5 nhan vat
        cards = tk.Frame(self.root, bg=BG)
        cards.pack(fill="x", padx=12, pady=7)

        self.character_buttons = []

        for index, character in enumerate(CHARACTERS):
            cards.grid_columnconfigure(index, weight=1, uniform="cards")

            card = tk.Frame(
                cards,
                bg=WHITE,
                highlightthickness=2,
                highlightbackground="#E2D0B7",
            )
            card.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=3,
                ipady=3,
            )

            # Hinh dai dien dang vong tron mau
            avatar = tk.Canvas(
                card,
                width=55,
                height=48,
                bg=WHITE,
                highlightthickness=0,
            )
            avatar.pack(pady=(5, 1))

            avatar.create_oval(
                8, 2, 47, 41,
                fill=character["color"],
                outline="",
            )
            avatar.create_text(
                27, 21,
                text=str(index + 1),
                fill=WHITE,
                font=("DejaVu Sans", 17, "bold"),
            )

            tk.Label(
                card,
                text=character["name"],
                font=("DejaVu Sans", 9, "bold"),
                bg=WHITE,
                fg=DARK,
            ).pack(padx=2, pady=(2, 1))

            tk.Label(
                card,
                text=character["role"],
                font=("DejaVu Sans", 8),
                bg=WHITE,
                fg=MUTED,
                wraplength=125,
                justify="center",
            ).pack(padx=2, pady=(0, 5))

            button = tk.Button(
                card,
                text="CHON",
                font=("DejaVu Sans", 9, "bold"),
                bg=character["color"],
                fg=WHITE,
                activebackground=GOLD,
                activeforeground=DARK,
                relief="flat",
                padx=5,
                pady=7,
                cursor="hand2",
                command=lambda i=index: self.show_story(i),
            )
            button.pack(fill="x", padx=5, pady=(0, 5))

            self.character_buttons.append(button)

        # Khung noi dung cau chuyen
        story_frame = tk.Frame(
            self.root,
            bg=WHITE,
            highlightthickness=1,
            highlightbackground="#DDC7A8",
        )
        story_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(4, 7),
        )

        self.story_title = tk.Label(
            story_frame,
            text="LOI CHAO CUA GIA LANG",
            font=("DejaVu Sans", 12, "bold"),
            bg=WHITE,
            fg=BROWN,
            anchor="w",
        )
        self.story_title.pack(fill="x", padx=12, pady=(8, 3))

        self.story_text = tk.Label(
            story_frame,
            text="",
            font=("DejaVu Sans", 10),
            bg=WHITE,
            fg=DARK,
            justify="left",
            anchor="nw",
            wraplength=740,
        )
        self.story_text.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(0, 5),
        )

        # Thanh dieu khien
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=12, pady=(0, 8))

        tk.Button(
            footer,
            text="VE LOI CHAO",
            font=("DejaVu Sans", 9, "bold"),
            bg=BROWN,
            fg=WHITE,
            activebackground=GOLD,
            activeforeground=DARK,
            relief="flat",
            padx=14,
            pady=8,
            command=self.show_welcome,
        ).pack(side="left")

        tk.Label(
            footer,
            text="Cham vao nhan vat de bat dau",
            font=("DejaVu Sans", 9),
            bg=BG,
            fg=MUTED,
        ).pack(side="right", padx=5)

    def show_welcome(self):
        self.selected = None

        self.story_title.config(text="LOI CHAO CUA GIA LANG")
        self.story_text.config(
            text=(
                "Xin chao cac ban nho!\n\n"
                "Ta la gia lang. Hay chon mot trong "
                "nam nhan vat phia tren de nghe cau "
                "chuyen mau cua nhan vat do.\n\n"
                "Chuc cac ban co mot hanh trinh "
                "kham pha that vui!"
            )
        )

        for button in self.character_buttons:
            button.config(relief="flat")

    def show_story(self, index):
        self.selected = index
        character = CHARACTERS[index]

        self.story_title.config(
            text=character["name"].upper()
            + " - "
            + character["role"].upper()
        )
        self.story_text.config(text=character["story"])

        for i, button in enumerate(self.character_buttons):
            if i == index:
                button.config(relief="sunken")
            else:
                button.config(relief="flat")

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def exit_fullscreen(self, event=None):
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)


if __name__ == "__main__":
    root = tk.Tk()
    app = NhaRongApp(root)
    root.mainloop()
