

from tkinter import messagebox
import tkinter as tk
import subprocess
import shutil

BG = "#F4E6CC"
BROWN = "#60391F"
DARK = "#382719"
WHITE = "#FFF9EE"
GOLD = "#D9AB62"
GREEN = "#557347"

CHARACTERS = [
    {
        "name": "Nhân vật 1",
        "role": "Người giữ lửa",
        "color": "#B65D35",
        "story": (
            "Xin chào các bạn! Tôi là người giữ lửa. "
            "Ngọn lửa mang đến hơi ấm và giúp mọi người "
            "quây quần bên nhau. Chúng ta hãy cùng học "
            "cách sẻ chia, quan tâm và giúp đỡ cộng đồng."
        ),
    },
    {
        "name": "Nhân vật 2",
        "role": "Người dẫn đường",
        "color": "#54784B",
        "story": (
            "Xin chào các bạn! Tôi yêu thiên nhiên và "
            "những con đường trong núi rừng. Khi khám phá "
            "quê hương, chúng ta hãy quan sát cẩn thận, "
            "bảo vệ cây xanh và giữ gìn môi trường."
        ),
    },
    {
        "name": "Nhân vật 3",
        "role": "Người dệt vải",
        "color": "#B18032",
        "story": (
            "Xin chào các bạn! Những hoa văn trên vải "
            "có thể kể nhiều câu chuyện về cuộc sống. "
            "Các nghề thủ công truyền thống cần được "
            "trân trọng và truyền lại cho thế hệ sau."
        ),
    },
    {
        "name": "Nhân vật 4",
        "role": "Người làm nhạc cụ",
        "color": "#8260A0",
        "story": (
            "Xin chào các bạn! Âm nhạc giúp mọi người "
            "gắn kết với nhau trong những dịp gặp gỡ "
            "và lễ hội. Hãy cùng lắng nghe, tìm hiểu "
            "và trân trọng những giá trị văn hóa."
        ),
    },
    {
        "name": "Nhân vật 5",
        "role": "Người kể chuyện",
        "color": "#287D91",
        "story": (
            "Xin chào các bạn! Những câu chuyện được "
            "truyền lại giúp chúng ta hiểu hơn về "
            "quê hương và gia đình. Hãy lắng nghe "
            "người đi trước và tìm hiểu văn hóa "
            "Cơ Tu bằng sự tôn trọng."
        ),
    },
]


class NhaRongApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nhà Rông Cơ Tu")
        self.root.geometry("1000x650")
        self.root.minsize(700, 500)
        self.root.configure(bg=BG)

        self.selected = None
        self.speech = None
        self.fullscreen = False
        self.buttons = []

        self.build_ui()
        self.show_welcome()

        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def build_ui(self):
        header = tk.Frame(self.root, bg=BROWN)
        header.pack(fill="x")

        tk.Label(
            header,
            text="⌂",
            font=("DejaVu Sans", 34, "bold"),
            bg=BROWN,
            fg=GOLD,
            padx=15,
        ).pack(side="left")

        title_frame = tk.Frame(header, bg=BROWN)
        title_frame.pack(side="left", fill="y", pady=9)

        tk.Label(
            title_frame,
            text="NHÀ RÔNG CƠ TU",
            font=("DejaVu Sans", 22, "bold"),
            bg=BROWN,
            fg="#FFE0A0",
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="KHÔNG GIAN VĂN HÓA VÀ KỂ CHUYỆN",
            font=("DejaVu Sans", 10),
            bg=BROWN,
            fg=WHITE,
        ).pack(anchor="w")

        tk.Button(
            header,
            text="Toàn màn hình",
            command=self.toggle_fullscreen,
            bg="#875B38",
            fg=WHITE,
            activebackground=GOLD,
            relief="flat",
            padx=12,
            pady=9,
        ).pack(side="right", padx=12, pady=12)

        tk.Label(
            self.root,
            text="Xin chào các bạn nhỏ! Hãy chọn một nhân vật.",
            font=("DejaVu Sans", 15, "bold"),
            bg=BG,
            fg=BROWN,
        ).pack(anchor="w", padx=18, pady=(13, 5))

        # Năm thẻ nhân vật
        cards = tk.Frame(self.root, bg=BG)
        cards.pack(fill="x", padx=12, pady=5)

        for i, person in enumerate(CHARACTERS):
            cards.grid_columnconfigure(i, weight=1, uniform="person")

            card = tk.Frame(
                cards,
                bg=WHITE,
                highlightthickness=2,
                highlightbackground=person["color"],
            )
            card.grid(row=0, column=i, sticky="nsew", padx=4)

            portrait = tk.Canvas(
                card,
                width=100,
                height=95,
                bg=WHITE,
                highlightthickness=0,
            )
            portrait.pack(pady=(7, 2))
            self.draw_person(portrait, person["color"], i)

            tk.Label(
                card,
                text=person["name"],
                font=("DejaVu Sans", 10, "bold"),
                bg=WHITE,
                fg=DARK,
            ).pack(padx=2)

            tk.Label(
                card,
                text=person["role"],
                font=("DejaVu Sans", 9),
                bg=WHITE,
                fg=person["color"],
                wraplength=140,
                justify="center",
            ).pack(padx=3, pady=4)

            button = tk.Button(
                card,
                text="CHỌN",
                font=("DejaVu Sans", 10, "bold"),
                bg=person["color"],
                fg=WHITE,
                activebackground=GOLD,
                activeforeground=DARK,
                relief="flat",
                cursor="hand2",
                command=lambda n=i: self.show_story(n),
            )
            button.pack(fill="x", padx=7, pady=(3, 8))
            self.buttons.append(button)

        # Vùng câu chuyện
        story_box = tk.Frame(
            self.root,
            bg=WHITE,
            highlightthickness=1,
            highlightbackground="#D4B68A",
        )
        story_box.pack(
            fill="both", expand=True, padx=16, pady=10
        )

        self.story_title = tk.Label(
            story_box,
            text="LỜI CHÀO CỦA GIÀ LÀNG",
            font=("DejaVu Sans", 16, "bold"),
            bg=WHITE,
            fg=BROWN,
            anchor="w",
        )
        self.story_title.pack(fill="x", padx=15, pady=(12, 6))

        self.story_text = tk.Label(
            story_box,
            text="",
            font=("DejaVu Sans", 13),
            bg=WHITE,
            fg=DARK,
            justify="left",
            anchor="nw",
            wraplength=900,
        )
        self.story_text.pack(
            fill="both", expand=True, padx=15, pady=5
        )

        # Nút điều khiển
        controls = tk.Frame(self.root, bg=BG)
        controls.pack(fill="x", padx=16, pady=(0, 12))

        self.make_control(
            controls, "Về lời chào", self.show_welcome, BROWN
        )
        self.make_control(
            controls, "▶ Đọc truyện", self.read_story, GREEN
        )
        self.make_control(
            controls, "■ Dừng đọc", self.stop_speech, "#A34535"
        )

        tk.Label(
            controls,
            text="Nhấn F11 để toàn màn hình",
            font=("DejaVu Sans", 9),
            bg=BG,
            fg=BROWN,
        ).pack(side="right", padx=5)

    def make_control(self, parent, text, command, color):
        tk.Button(
            parent,
            text=text,
            command=command,
            font=("DejaVu Sans", 10, "bold"),
            bg=color,
            fg=WHITE,
            activebackground=GOLD,
            relief="flat",
            padx=12,
            pady=9,
        ).pack(side="left", padx=(0, 7))

    def draw_person(self, canvas, color, index):
        # Minh họa nhân vật dạng hoạt hình đơn giản.
        # Có thể thay bằng ảnh chân dung sau này.
        canvas.create_oval(
            10, 5, 90, 85, fill="#F0DFC3", outline=""
        )

        # Tóc
        canvas.create_oval(
            31, 17, 69, 59, fill="#382719", outline=""
        )

        # Mặt
        canvas.create_oval(
            35, 24, 65, 56, fill="#D99A70", outline=""
        )

        # Mắt
        canvas.create_oval(42, 36, 46, 40, fill="#382719")
        canvas.create_oval(54, 36, 58, 40, fill="#382719")

        # Miệng
        canvas.create_arc(
            44, 39, 57, 51,
            start=200, extent=140,
            style="arc", outline="#8A4938", width=2
        )

        # Trang phục
        canvas.create_polygon(
            35, 54, 65, 54, 78, 87, 22, 87,
            fill=color, outline=""
        )

        # Hoa văn trang trí
        canvas.create_line(
            38, 62, 62, 62, fill=GOLD, width=3
        )
        canvas.create_line(
            43, 70, 57, 70, fill=WHITE, width=2
        )

        # Biểu tượng riêng cho từng nhân vật
        symbols = ["✦", "❋", "◇", "♫", "❝"]
        canvas.create_text(
            77, 15,
            text=symbols[index],
            font=("DejaVu Sans", 16, "bold"),
            fill=color,
        )

    def show_welcome(self):
        self.stop_speech()
        self.selected = None

        self.story_title.config(text="LỜI CHÀO CỦA GIÀ LÀNG")
        self.story_text.config(
            text=(
                "Xin chào các bạn nhỏ!\n\n"
                "Ta là già làng. Nhà rông là nơi "
                "cộng đồng gặp gỡ và cùng gìn giữ "
                "những giá trị văn hóa.\n\n"
                "Hãy chọn một nhân vật để nghe "
                "câu chuyện và bắt đầu hành trình "
                "khám phá của mình!"
            )
        )

        for button in self.buttons:
            button.config(relief="flat")

    def show_story(self, index):
        self.stop_speech()
        self.selected = index
        person = CHARACTERS[index]

        self.story_title.config(
            text=person["name"] + " — " + person["role"]
        )
        self.story_text.config(text=person["story"])

        for i, button in enumerate(self.buttons):
            button.config(
                relief="sunken" if i == index else "flat"
            )

    def read_story(self):
        if self.selected is None:
            text = (
                "Xin chào các bạn nhỏ. "
                "Ta là già làng. Hãy chọn một nhân vật "
                "để nghe câu chuyện nhé."
            )
        else:
            person = CHARACTERS[self.selected]
            text = person["name"] + ". " + person["story"]

        if not shutil.which("espeak-ng"):
            messagebox.showerror(
                "Thiếu bộ đọc tiếng nói",
                "Hãy cài espeak-ng trên Raspberry Pi."
            )
            return

        self.stop_speech()

        try:
            self.speech = subprocess.Popen(
                ["espeak-ng", "-v", "vi", "-s", "140", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as error:
            messagebox.showerror("Lỗi phát âm thanh", str(error))

    def stop_speech(self):
        if self.speech and self.speech.poll() is None:
            self.speech.terminate()
            try:
                self.speech.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.speech.kill()
        self.speech = None

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def exit_fullscreen(self, event=None):
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)

    def close_app(self):
        self.stop_speech()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = NhaRongApp(root)
    root.mainloop()
