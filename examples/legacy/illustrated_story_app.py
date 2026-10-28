# -*- coding: utf-8 -*-
"""
Ứng dụng kể chuyện Nhà Rông Cơ Tu
- Giao diện màu gỗ, kem và xanh lá
- 5 nhân vật minh họa bằng Canvas
- Đọc tiếng Việt: espeak-ng (Raspberry Pi/Linux) hoặc pyttsx3 (Windows, nếu đã cài)
- Chuẩn bị cho tích hợp RFID/RF: xử lý sự kiện nhân vật qua select_character(index)
"""

import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox

# Bảng màu lấy cảm hứng từ gỗ, đất và cây rừng
BG = "#EFE2CB"
PANEL = "#FFF8EB"
WOOD = "#5B3826"
WOOD_DARK = "#38251B"
WOOD_LIGHT = "#8A5B3D"
TAN = "#D9B783"
GOLD = "#E7C47A"
GREEN = "#526B43"
GREEN_DARK = "#354A30"
TERRA = "#A65338"
MUTED = "#786653"
BORDER = "#D7C09B"
WHITE = "#FFFFFF"

FONT = "DejaVu Sans" if sys.platform != "win32" else "Arial"

CHARACTERS = [
    {
        "name": "Người giữ lửa",
        "role": "Giữ hơi ấm cộng đồng",
        "color": "#B65D35",
        "symbol": "✦",
        "story": (
            "Xin chào các bạn! Tôi là người giữ lửa. "
            "Ngọn lửa mang đến hơi ấm và giúp mọi người quây quần bên nhau. "
            "Chúng ta hãy cùng học cách sẻ chia, quan tâm và giúp đỡ cộng đồng."
        ),
    },
    {
        "name": "Người dẫn đường",
        "role": "Yêu núi rừng",
        "color": "#54784B",
        "symbol": "❋",
        "story": (
            "Xin chào các bạn! Tôi yêu thiên nhiên và những con đường trong núi rừng. "
            "Khi khám phá quê hương, chúng ta hãy quan sát cẩn thận, bảo vệ cây xanh "
            "và giữ gìn môi trường."
        ),
    },
    {
        "name": "Người dệt vải",
        "role": "Gìn giữ hoa văn",
        "color": "#B18032",
        "symbol": "◇",
        "story": (
            "Xin chào các bạn! Những hoa văn trên vải có thể kể nhiều câu chuyện "
            "về cuộc sống. Các nghề thủ công truyền thống cần được trân trọng "
            "và truyền lại cho thế hệ sau."
        ),
    },
    {
        "name": "Người làm nhạc cụ",
        "role": "Âm thanh lễ hội",
        "color": "#8260A0",
        "symbol": "♫",
        "story": (
            "Xin chào các bạn! Âm nhạc giúp mọi người gắn kết với nhau trong những "
            "dịp gặp gỡ và lễ hội. Hãy cùng lắng nghe, tìm hiểu và trân trọng "
            "những giá trị văn hóa."
        ),
    },
    {
        "name": "Người kể chuyện",
        "role": "Truyền lại ký ức",
        "color": "#287D91",
        "symbol": "❝",
        "story": (
            "Xin chào các bạn! Những câu chuyện được truyền lại giúp chúng ta hiểu "
            "hơn về quê hương và gia đình. Hãy lắng nghe người đi trước và tìm hiểu "
            "văn hóa Cơ Tu bằng sự tôn trọng."
        ),
    },
]


class NhaRongApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nhà Rông Cơ Tu | Không gian kể chuyện")
        self.root.geometry("1120x760")
        self.root.minsize(760, 600)
        self.root.configure(bg=BG)

        self.selected = None
        self.speech = None
        self.speech_engine = None
        self.speech_thread = None
        self.fullscreen = False
        self.buttons = []
        self.card_frames = []
        self._speech_backend = None

        self.build_ui()
        self.show_welcome()

        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.bind("<Configure>", self._resize_story)
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=WOOD, height=94)
        header.pack(fill="x")
        header.pack_propagate(False)

        mark = tk.Canvas(header, width=74, height=78, bg=WOOD, highlightthickness=0)
        mark.pack(side="left", padx=(16, 8), pady=7)
        self.draw_house_mark(mark)

        heading = tk.Frame(header, bg=WOOD)
        heading.pack(side="left", fill="both", expand=True, pady=13)
        tk.Label(
            heading, text="NHÀ RÔNG CƠ TU",
            font=(FONT, 22, "bold"), bg=WOOD, fg="#FFE5AD"
        ).pack(anchor="w")
        tk.Label(
            heading, text="KHÔNG GIAN VĂN HÓA • LẮNG NGHE • KẾT NỐI",
            font=(FONT, 9, "bold"), bg=WOOD, fg="#F5E8D2"
        ).pack(anchor="w", pady=(4, 0))

        self.fullscreen_button = self.make_button(
            header, "⛶ Toàn màn hình", self.toggle_fullscreen,
            bg=WOOD_LIGHT, fg=WHITE, padx=14, pady=10
        )
        self.fullscreen_button.pack(side="right", padx=16, pady=20)

        # Intro strip
        intro = tk.Frame(self.root, bg=BG)
        intro.pack(fill="x", padx=20, pady=(15, 9))
        tk.Label(
            intro, text="HÀNH TRÌNH KỂ CHUYỆN",
            font=(FONT, 15, "bold"), bg=BG, fg=WOOD
        ).pack(anchor="w")
        tk.Label(
            intro, text="Chọn một người bạn trong làng để lắng nghe câu chuyện của họ.",
            font=(FONT, 10), bg=BG, fg=MUTED
        ).pack(anchor="w", pady=(3, 0))

        # Main content: character rail and story panel
        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(fill="both", expand=True, padx=18, pady=(2, 12))
        self.main.grid_columnconfigure(0, weight=5, uniform="main")
        self.main.grid_columnconfigure(1, weight=7, uniform="main")
        self.main.grid_rowconfigure(0, weight=1)

        left = tk.Frame(self.main, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        left_head = tk.Frame(left, bg=BG)
        left_head.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        tk.Label(
            left_head, text="NGƯỜI TRONG LÀNG",
            font=(FONT, 10, "bold"), bg=BG, fg=WOOD
        ).pack(side="left")
        tk.Label(
            left_head, text="05 NHÂN VẬT",
            font=(FONT, 8, "bold"), bg=BG, fg=GREEN
        ).pack(side="right")

        self.cards_container = tk.Frame(left, bg=BG)
        self.cards_container.grid(row=1, column=0, sticky="nsew")
        for col in range(2):
            self.cards_container.grid_columnconfigure(col, weight=1, uniform="cards")
        for row in range(3):
            self.cards_container.grid_rowconfigure(row, weight=1, uniform="cardrows")

        for i, person in enumerate(CHARACTERS):
            card = tk.Frame(
                self.cards_container, bg=PANEL, bd=0,
                highlightthickness=2, highlightbackground=BORDER
            )
            row, col = divmod(i, 2)
            card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            card.grid_columnconfigure(0, weight=1)
            self.card_frames.append(card)

            portrait = tk.Canvas(card, width=94, height=90, bg=PANEL, highlightthickness=0)
            portrait.pack(pady=(7, 1))
            self.draw_person(portrait, person["color"], i)

            tk.Label(
                card, text=person["name"], font=(FONT, 9, "bold"),
                bg=PANEL, fg=WOOD_DARK, wraplength=150, justify="center"
            ).pack(fill="x", padx=4, pady=(2, 1))
            tk.Label(
                card, text=person["role"], font=(FONT, 8),
                bg=PANEL, fg=MUTED, wraplength=150, justify="center"
            ).pack(fill="x", padx=4, pady=(0, 6))

            btn = self.make_button(
                card, "CHỌN NHÂN VẬT", lambda n=i: self.select_character(n),
                bg=person["color"], fg=WHITE, padx=5, pady=7, small=True
            )
            btn.pack(fill="x", padx=7, pady=(0, 8))
            self.buttons.append(btn)

        # The fifth card spans both columns for a balanced final row
        self.card_frames[4].grid_configure(column=0, columnspan=2, padx=4, pady=4)
        # Keep the fifth card visually compact and centered
        self.card_frames[4].configure(height=150)
        self.card_frames[4].grid_propagate(True)

        # Story panel
        self.story_panel = tk.Frame(
            self.main, bg=PANEL, highlightthickness=1, highlightbackground=BORDER
        )
        self.story_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.story_panel.grid_rowconfigure(2, weight=1)
        self.story_panel.grid_columnconfigure(0, weight=1)

        story_top = tk.Frame(self.story_panel, bg=WOOD)
        story_top.grid(row=0, column=0, sticky="ew")
        tk.Label(
            story_top, text="✦  GÓC KỂ CHUYỆN",
            font=(FONT, 11, "bold"), bg=WOOD, fg="#FFE5AD"
        ).pack(anchor="w", padx=17, pady=(13, 4))
        self.story_subtitle = tk.Label(
            story_top, text="Lời chào từ già làng",
            font=(FONT, 9), bg=WOOD, fg="#F5E8D2"
        )
        self.story_subtitle.pack(anchor="w", padx=18, pady=(0, 13))

        self.story_title = tk.Label(
            self.story_panel, text="LỜI CHÀO CỦA GIÀ LÀNG",
            font=(FONT, 16, "bold"), bg=PANEL, fg=WOOD,
            anchor="w", justify="left", wraplength=520
        )
        self.story_title.grid(row=1, column=0, sticky="ew", padx=18, pady=(18, 8))

        text_wrap = tk.Frame(self.story_panel, bg="#F8EEDC", highlightthickness=1, highlightbackground="#E6D4B6")
        text_wrap.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 12))
        text_wrap.grid_rowconfigure(0, weight=1)
        text_wrap.grid_columnconfigure(0, weight=1)

        self.story_text = tk.Text(
            text_wrap, wrap="word", height=8, bd=0,
            font=(FONT, 12), bg="#F8EEDC", fg=WOOD_DARK,
            padx=16, pady=15, spacing1=4, spacing3=7,
            relief="flat", cursor="arrow", state="disabled"
        )
        self.story_text.grid(row=0, column=0, sticky="nsew")
        self.story_scroll = tk.Scrollbar(text_wrap, command=self.story_text.yview)
        self.story_scroll.grid(row=0, column=1, sticky="ns")
        self.story_text.configure(yscrollcommand=self.story_scroll.set)

        self.status_label = tk.Label(
            self.story_panel, text="● Sẵn sàng lắng nghe",
            font=(FONT, 9, "bold"), bg=PANEL, fg=GREEN, anchor="w"
        )
        self.status_label.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 9))

        controls = tk.Frame(self.story_panel, bg=PANEL)
        controls.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 16))
        controls.grid_columnconfigure(0, weight=1)
        controls.grid_columnconfigure(1, weight=1)

        self.read_button = self.make_button(
            controls, "▶  NGHE KỂ CHUYỆN", self.read_story,
            bg=GREEN, fg=WHITE, padx=8, pady=12
        )
        self.read_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.stop_button = self.make_button(
            controls, "■  DỪNG ĐỌC", self.stop_speech,
            bg=TERRA, fg=WHITE, padx=8, pady=12
        )
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        # Footer
        footer = tk.Frame(self.root, bg=WOOD_DARK, height=30)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        tk.Label(
            footer, text="VĂN HÓA ĐƯỢC GÌN GIỮ QUA MỖI CÂU CHUYỆN",
            font=(FONT, 8, "bold"), bg=WOOD_DARK, fg="#E9D4B2"
        ).pack(side="left", padx=18, pady=6)
        tk.Button(
            footer, text="Về lời chào", command=self.show_welcome,
            font=(FONT, 8, "bold"), bg=WOOD_DARK, fg="#FFE5AD",
            activebackground=WOOD_LIGHT, activeforeground=WHITE,
            relief="flat", cursor="hand2"
        ).pack(side="right", padx=16)

    def make_button(self, parent, text, command, bg, fg, padx=10, pady=8, small=False):
        return tk.Button(
            parent, text=text, command=command,
            font=(FONT, 8 if small else 9, "bold"),
            bg=bg, fg=fg, activebackground=GOLD, activeforeground=WOOD_DARK,
            relief="flat", bd=0, padx=padx, pady=pady,
            cursor="hand2", takefocus=True
        )

    def draw_house_mark(self, canvas):
        # Biểu tượng cách điệu của mái nhà cộng đồng, không phải bản phục dựng chính xác.
        canvas.create_polygon(8, 38, 37, 7, 66, 38, fill=GOLD, outline="")
        canvas.create_polygon(17, 38, 37, 17, 57, 38, fill=WOOD_LIGHT, outline="")
        canvas.create_rectangle(22, 38, 52, 65, fill="#D5B17B", outline="")
        canvas.create_rectangle(33, 46, 42, 65, fill=WOOD_DARK, outline="")
        for x in (25, 49):
            canvas.create_line(x, 42, x, 62, fill=WOOD, width=2)
        canvas.create_line(14, 68, 60, 68, fill=GOLD, width=2)

    def draw_person(self, canvas, color, index):
        # Minh họa biểu tượng nhân vật để thay thế tạm thời; có thể đổi thành ảnh thật sau này.
        canvas.create_oval(8, 4, 86, 82, fill="#F0E2C9", outline="")
        canvas.create_oval(29, 13, 65, 51, fill=WOOD_DARK, outline="")
        canvas.create_oval(33, 20, 61, 49, fill="#D99A70", outline="")
        canvas.create_oval(39, 31, 43, 35, fill=WOOD_DARK, outline="")
        canvas.create_oval(51, 31, 55, 35, fill=WOOD_DARK, outline="")
        canvas.create_arc(41, 33, 54, 44, start=200, extent=140, style="arc", outline="#8A4938", width=2)
        canvas.create_polygon(33, 49, 61, 49, 75, 82, 19, 82, fill=color, outline="")
        canvas.create_line(35, 58, 59, 58, fill=GOLD, width=3)
        canvas.create_line(39, 66, 55, 66, fill="#FFF8EB", width=2)
        canvas.create_text(72, 14, text=CHARACTERS[index]["symbol"], font=(FONT, 15, "bold"), fill=color)

    def set_story(self, text):
        self.story_text.configure(state="normal")
        self.story_text.delete("1.0", "end")
        self.story_text.insert("1.0", text)
        self.story_text.configure(state="disabled")
        self.story_text.yview_moveto(0)

    def show_welcome(self):
        self.stop_speech(update_status=False)
        self.selected = None
        self.story_subtitle.config(text="Lời chào từ già làng")
        self.story_title.config(text="CHÀO MỪNG ĐẾN VỚI NHÀ RÔNG")
        self.set_story(
            "Xin chào các bạn nhỏ!\n\n"
            "Ta là già làng. Nhà rông là nơi cộng đồng gặp gỡ, chia sẻ "
            "và cùng gìn giữ những giá trị văn hóa.\n\n"
            "Hãy chọn một người bạn trong làng ở bên trái để nghe câu chuyện "
            "của họ. Mỗi nhân vật có một câu chuyện riêng đang chờ được khám phá.\n\n"
            "Khi sẵn sàng, hãy nhấn “Nghe kể chuyện”."
        )
        for i, card in enumerate(self.card_frames):
            card.configure(highlightbackground=BORDER)
            self.buttons[i].configure(text="CHỌN NHÂN VẬT")
        self.status_label.config(text="● Sẵn sàng lắng nghe", fg=GREEN)

    def select_character(self, index):
        # Điểm tích hợp tương lai: RFID/RF chỉ cần gọi select_character(index).
        self.stop_speech(update_status=False)
        self.selected = index
        person = CHARACTERS[index]
        self.story_subtitle.config(text="Câu chuyện của người bạn trong làng")
        self.story_title.config(text=person["name"].upper())
        self.set_story(person["story"])
        for i, card in enumerate(self.card_frames):
            selected = i == index
            card.configure(highlightbackground=GOLD if selected else BORDER)
            self.buttons[i].configure(text="✓ ĐANG CHỌN" if selected else "CHỌN NHÂN VẬT")
        self.status_label.config(text="● Đã chọn nhân vật — sẵn sàng nghe", fg=GREEN)

    def read_story(self):
        if self.selected is None:
            text = (
                "Xin chào các bạn nhỏ. Ta là già làng. "
                "Hãy chọn một nhân vật để nghe câu chuyện nhé."
            )
        else:
            person = CHARACTERS[self.selected]
            text = person["name"] + ". " + person["story"]

        self.stop_speech(update_status=False)
        self.status_label.config(text="◉ Đang chuẩn bị giọng đọc...", fg=WOOD_LIGHT)
        self.root.update_idletasks()

        # Linux/Raspberry Pi: ưu tiên espeak-ng. Windows: dùng pyttsx3 nếu có.
        if shutil.which("espeak-ng"):
            self._speech_backend = "espeak-ng"
            try:
                self.speech = subprocess.Popen(
                    ["espeak-ng", "-v", "vi", "-s", "140", text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.status_label.config(text="◖ Đang đọc truyện...", fg=GREEN)
                self._poll_speech()
            except OSError as error:
                self.status_label.config(text="Không thể phát âm thanh", fg=TERRA)
                messagebox.showerror("Lỗi phát âm thanh", str(error))
            return

        # Windows / máy không có espeak-ng
        try:
            import pyttsx3
        except ImportError:
            self.status_label.config(text="Chưa cài bộ đọc tiếng nói", fg=TERRA)
            messagebox.showerror(
                "Chưa có bộ đọc tiếng nói",
                "Không tìm thấy espeak-ng hoặc pyttsx3.\n\n"
                "Windows: mở Terminal và chạy:\npy -m pip install pyttsx3\n\n"
                "Raspberry Pi OS: chạy:\nsudo apt update && sudo apt install espeak-ng"
            )
            return

        self._speech_backend = "pyttsx3"
        self.status_label.config(text="◖ Đang đọc truyện...", fg=GREEN)

        def speak_windows():
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 145)
                # Chọn giọng tiếng Việt nếu máy có sẵn; nếu không, dùng giọng mặc định.
                voices = engine.getProperty("voices")
                for voice in voices:
                    details = (voice.id + " " + voice.name).lower()
                    if "vietnam" in details or "vi-vn" in details or "vi_vn" in details:
                        engine.setProperty("voice", voice.id)
                        break
                self.speech_engine = engine
                engine.say(text)
                engine.runAndWait()
                self.root.after(0, lambda: self.status_label.config(
                    text="● Đã đọc xong câu chuyện", fg=GREEN
                ))
            except Exception as error:
                self.root.after(0, lambda err=str(error): messagebox.showerror("Lỗi đọc truyện", err))
                self.root.after(0, lambda: self.status_label.config(
                    text="Không thể phát âm thanh", fg=TERRA
                ))
            finally:
                self.speech_engine = None

        self.speech_thread = threading.Thread(target=speak_windows, daemon=True)
        self.speech_thread.start()

    def _poll_speech(self):
        if self.speech is None:
            return
        if self.speech.poll() is None:
            self.root.after(250, self._poll_speech)
        else:
            self.speech = None
            self.status_label.config(text="● Đã đọc xong câu chuyện", fg=GREEN)

    def stop_speech(self, update_status=True):
        if self.speech and self.speech.poll() is None:
            try:
                self.speech.terminate()
                self.speech.wait(timeout=1)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self.speech.kill()
                except OSError:
                    pass
        self.speech = None
        if self.speech_engine is not None:
            try:
                self.speech_engine.stop()
            except Exception:
                pass
        if update_status and hasattr(self, "status_label"):
            self.status_label.config(text="■ Đã dừng đọc", fg=TERRA)

    def _resize_story(self, event=None):
        # Cập nhật wraplength khi cửa sổ thay đổi kích thước.
        if not hasattr(self, "story_title") or not hasattr(self, "story_panel"):
            return
        try:
            width = max(220, self.story_panel.winfo_width() - 42)
            self.story_title.configure(wraplength=width)
        except tk.TclError:
            pass

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
        return "break"

    def exit_fullscreen(self, event=None):
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)
        return "break"

    def close_app(self):
        self.stop_speech(update_status=False)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = NhaRongApp(root)
    root.mainloop()
