"""Giao diện cảm ứng cho ứng dụng video; chỉ dùng Tkinter, chạy ngoại tuyến."""

from cotu_app.core.paths import IMAGES_DIR
import tkinter as tk

from cotu_app.features.stories.characters import CHARACTERS
from .keyboard import TouchKeyboard
from . import theme
from cotu_app.core.branding import APP_NAME, APP_TAGLINE, CHAT_NAME


class TouchQuestionList(tk.Frame):
    """Câu hỏi tự xuống dòng, vùng chạm lớn, cuộn được bằng chuột/cảm ứng."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=VideoInterface.PAPER, **kwargs)
        self.canvas = tk.Canvas(self, bg=VideoInterface.PAPER, highlightthickness=0,
                                width=1, height=1)
        self.canvas.pack(fill="both", expand=True)
        self.content = tk.Frame(self.canvas, bg=VideoInterface.PAPER)
        self.window = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self.items = []
        self.selected = ()
        self.dragging = False
        self.press_y = 0
        self.canvas.bind("<Configure>", self.resize)
        self.content.bind("<Configure>", lambda event: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        for widget in (self, self.canvas, self.content):
            self.bind_scroll(widget)

    def bind_scroll(self, widget):
        widget.bind("<Button-4>", lambda event: self.scroll(-1))
        widget.bind("<Button-5>", lambda event: self.scroll(1))
        widget.bind("<MouseWheel>", lambda event: self.scroll(-1 if event.delta > 0 else 1))
        widget.bind("<ButtonPress-1>", self.touch_start, add="+")
        widget.bind("<B1-Motion>", self.touch_move, add="+")

    def touch_start(self, event):
        self.dragging = False
        self.press_y = event.y_root
        self.canvas.scan_mark(0, event.y_root - self.canvas.winfo_rooty())

    def touch_move(self, event):
        if abs(event.y_root - self.press_y) >= 8:
            self.dragging = True
            self.canvas.scan_dragto(0, event.y_root - self.canvas.winfo_rooty(), gain=1)
            return "break"

    def scroll(self, direction):
        self.canvas.yview_scroll(direction, "units")
        return "break"

    def resize(self, event):
        self.canvas.itemconfigure(self.window, width=event.width)
        for button in self.items:
            button.configure(wraplength=max(60, event.width - 26))

    def insert(self, index, text):
        position = len(self.items)
        button = tk.Button(self.content, text=f"{position + 1:02d}  {text.split(' • ')[-1]}", anchor="w", justify="left",
                           bg=theme.SOFT, fg=VideoInterface.INK, activebackground="#F8E5B7",
                           activeforeground=VideoInterface.INK, relief="flat", borderwidth=0,
                           highlightthickness=2, highlightbackground=theme.SOFT,
                           highlightcolor=VideoInterface.ORANGE, cursor="hand2",
                           font=(VideoInterface.FONT, 11), padx=9, pady=14,
                           wraplength=max(60, self.canvas.winfo_width() - 26),
                           command=lambda: self.choose(position))
        button.pack(fill="x", pady=(0, 8))
        self.items.append(button)
        self.bind_scroll(button)

    def delete(self, first, last=None):
        for button in self.items:
            button.destroy()
        self.items.clear()
        self.selected = ()
        self.canvas.yview_moveto(0)

    def curselection(self):
        return self.selected

    def selection_set(self, index):
        self.selected = (index,)
        for position, button in enumerate(self.items):
            button.configure(bg=VideoInterface.GREEN if position == index else theme.SOFT,
                             fg="white" if position == index else VideoInterface.INK)

    def choose(self, index):
        if self.dragging:
            self.dragging = False
            return
        self.selection_set(index)
        self.event_generate("<<ListboxSelect>>")

    def yview(self, *args):
        return self.canvas.yview(*args)


class VideoInterface:
    BG, PAPER, INK, MUTED = theme.BG, theme.SURFACE, theme.INK, theme.MUTED
    GREEN, ORANGE, LINE, FONT = theme.PRIMARY, theme.ACCENT, theme.LINE, theme.FONT

    def build_interface(self):
        tk, ttk, root = self.tk, self.ttk, self.root
        self.compact = root.winfo_screenheight() <= 600
        from cotu_app.core.paths import BASE
        version_file = BASE / "release.json"
        version = ""
        if version_file.is_file():
            import json
            version = " · v" + json.loads(version_file.read_text(encoding="utf-8"))["version"]
        root.title(APP_NAME + " · Khám phá văn hóa Cơ Tu" + version)
        root.geometry("800x480" if self.compact else "1100x720")
        root.minsize(800, 480)
        root.configure(bg=self.BG)
        root.option_add("*Font", (self.FONT, 11))
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<F11>", self.toggle_fullscreen)
        root.bind("<Escape>", lambda event: root.attributes("-fullscreen", False))
        self.configure_styles()

        self.header = tk.Frame(root, bg=self.PAPER, padx=12, pady=4)
        self.header.pack(fill="x")
        mark = tk.Canvas(self.header, width=40, height=42, bg=self.PAPER, highlightthickness=0)
        mark.pack(side="left", padx=(0, 10))
        mark.create_polygon(3, 22, 20, 3, 37, 22, fill=self.GREEN, outline="")
        mark.create_rectangle(9, 22, 31, 33, fill="#D9B176", outline="")
        mark.create_line(12, 33, 12, 40, fill=self.GREEN, width=3)
        mark.create_line(28, 33, 28, 40, fill=self.GREEN, width=3)
        brand = tk.Frame(self.header, bg=self.PAPER)
        brand.pack(side="left")
        self.label(brand, APP_NAME.upper(), size=19, bold=True, bg=self.PAPER).pack(anchor="w")
        self.label(brand, "Không gian văn hóa Cơ Tu", size=9, fg=self.MUTED,
                   bg=self.PAPER).pack(anchor="w")
        self.button(self.header, "Toàn màn hình", self.toggle_fullscreen, side="right")
        if not self.compact:
            self.label(self.header, APP_TAGLINE, size=11, bg=self.PAPER,
                       fg=self.MUTED).pack(side="right", padx=24)

        self.navigation = tk.Frame(root, bg=self.PAPER, padx=8, pady=6)
        self.navigation.pack(side="bottom", fill="x")
        self.nav_buttons = {}
        self.footer = tk.Frame(root, bg=self.BG, padx=14, pady=2)
        self.footer.pack(side="bottom", fill="x")
        self.status = tk.StringVar(value="Chọn một người bạn hoặc quét thẻ để bắt đầu.")
        self.status_label = tk.Label(self.footer, textvariable=self.status, bg=self.BG,
                                    fg=self.MUTED, anchor="w", height=1,
                                    font=(self.FONT, 10))
        self.status_label.pack(fill="x")
        root.bind("<Configure>", self.resize_status, add="+")
        self.tabs = ttk.Notebook(root, style="Story.TNotebook", takefocus=False)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        self.video_tab, self.qa_tab, self.setup_tab = (
            ttk.Frame(self.tabs, style="Story.TFrame", padding=0) for _ in range(3))
        for frame, title in ((self.video_tab, "Nghe chuyện"),
                             (self.qa_tab, "Hỏi đáp"), (self.setup_tab, "Thiết lập")):
            self.tabs.add(frame, text=title)
        self.tabs.bind("<<NotebookTabChanged>>", self.tab_changed)
        self.tabs.bind("<<NotebookTabChanged>>", lambda event: self.update_navigation(), add="+")
        self.ids = list(CHARACTERS)
        self.portraits = self.load_portraits()
        self.build_video_tab()
        self.build_question_tab()
        self.build_setup_tab()
        self.refresh_navigation()
        self.status.trace_add("write", self.update_status_color)
        self.refresh_details()
        self.show("Em muốn tìm hiểu điều gì?\n\nChọn một người bạn, rồi chạm câu hỏi mẫu hoặc hỏi bằng mic.")

    def configure_styles(self):
        theme.configure_styles(self.root)

    def refresh_navigation(self):
        for button in self.nav_buttons.values():
            button.destroy()
        self.nav_buttons.clear()
        for index, tab in enumerate(self.tabs.tabs()):
            self.navigation.columnconfigure(index, weight=1, uniform="navigation")
            title = self.tabs.tab(tab, "text")
            label = "Trò chuyện" if title == CHAT_NAME else title
            button = self.tk.Button(self.navigation, text=label, height=2,
                font=(self.FONT, 11, "bold"), bg=self.PAPER, fg=self.MUTED,
                activebackground=theme.SOFT, activeforeground=self.GREEN,
                relief="flat", bd=0, pady=4, highlightthickness=2,
                highlightbackground=self.PAPER, highlightcolor=self.ORANGE,
                cursor="hand2", command=lambda selected=tab: self.tabs.select(selected))
            button.grid(row=0, column=index, sticky="ew", padx=4)
            self.nav_buttons[tab] = button
        self.update_navigation()

    def update_navigation(self):
        current = self.tabs.select()
        for tab, button in self.nav_buttons.items():
            selected = tab == current
            label = "Trò chuyện" if self.tabs.tab(tab, "text") == CHAT_NAME else self.tabs.tab(tab, "text")
            button.configure(text=("•  " if selected else "") + label,
                             bg=self.GREEN if selected else self.PAPER,
                             fg="white" if selected else self.MUTED,
                             highlightbackground=self.GREEN if selected else self.PAPER)

    def label(self, parent, text="", *, size=10, bold=False, bg=None, fg=None, **kwargs):
        return self.tk.Label(parent, text=text, bg=bg or self.BG, fg=fg or self.INK,
                             font=(self.FONT, size, "bold" if bold else "normal"), **kwargs)

    def button(self, parent, text, command, style="Story.TButton", side="left"):
        button = self.ttk.Button(parent, text=text, command=command, style=style, cursor="hand2")
        button.pack(side=side, padx=4)
        return button

    def load_portraits(self):
        """Tách ảnh có sẵn bằng Tk, không thêm phụ thuộc Pillow."""
        portraits = {}
        try:
            sheet = self.tk.PhotoImage(master=self.root,
                                       file=str(IMAGES_DIR / "village_characters.png"))
            width, height = sheet.width() // 3, sheet.height() // 2
            target = 54 if self.compact else 84
            factor = max(1, (max(width, height) + target - 1) // target)
            for index, cid in enumerate(self.ids):
                row, col = divmod(index, 3)
                tile = self.tk.PhotoImage(master=self.root)
                tile.tk.call(str(tile), "copy", str(sheet), "-from",
                             col * width, row * height, (col + 1) * width, (row + 1) * height)
                portraits[cid] = tile.subsample(factor)
        except (OSError, self.tk.TclError):
            # Nút tên nhân vật vẫn hoạt động nếu thiếu ảnh minh họa.
            pass
        return portraits

    def build_video_tab(self):
        tk = self.tk
        self.video_tab.columnconfigure(1, weight=1)
        self.video_tab.rowconfigure(0, weight=1)
        sidebar = tk.Frame(self.video_tab, bg=self.PAPER, padx=6, pady=6,
                           highlightthickness=1, highlightbackground=self.LINE)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.label(sidebar, "CHỌN NGƯỜI BẠN", size=9, bold=True, bg=self.PAPER,
                   fg=self.MUTED).grid(row=0, column=0, columnspan=2, pady=(0, 8))
        self.character_buttons = {}
        for index, cid in enumerate(self.ids):
            row, col = divmod(index, 2)
            sidebar.columnconfigure(col, weight=1, uniform="cards")
            sidebar.rowconfigure(row + 1, weight=1, uniform="cards")
            button = tk.Button(
                sidebar, text=CHARACTERS[cid]["name"], image=self.portraits.get(cid, ""),
                compound="top", wraplength=82 if self.compact else 114,
                font=(self.FONT, 10, "bold"),
                bg=self.PAPER, fg=self.INK, activebackground="#F8E5B7",
                activeforeground=self.INK, relief="flat", borderwidth=0,
                highlightthickness=2, highlightbackground=self.PAPER,
                highlightcolor=self.ORANGE, padx=4, pady=3, cursor="hand2",
                command=lambda selected=cid: self.select(selected))
            button.grid(row=row + 1, column=col, sticky="nsew", padx=2, pady=2)
            self.character_buttons[cid] = button

        main = tk.Frame(self.video_tab, bg=self.BG)
        main.grid(row=0, column=1, sticky="nsew")
        title_row = tk.Frame(main, bg=self.BG)
        title_row.pack(fill="x", pady=(0, 5))
        self.character_title = self.label(title_row, size=13 if self.compact else 18, bold=True)
        self.character_title.pack(side="left")
        self.button(title_row, "Cùng hỏi đáp", lambda: self.tabs.select(self.qa_tab), "Primary.TButton", side="right")
        controls = tk.Frame(main, bg=self.BG)
        controls.pack(side="bottom", fill="x", pady=(6, 0))
        for text, command, style in (("Tiếp tục", self.resume, "Primary.TButton"),
                                      ("Tạm dừng", self.pause, "Story.TButton"),
                                      ("Kể lại", self.play, "Story.TButton"),
                                      ("Dừng", self.stop_playback, "Story.TButton")):
            self.button(controls, text, command, style)
        self.surface = tk.Frame(main, bg="#182C26", highlightthickness=1,
                                highlightbackground=self.LINE)
        self.surface.pack(fill="both", expand=True)
        self.cover = tk.Canvas(self.surface, background="#F4ECD9", highlightthickness=0)
        self.cover.place(relwidth=1, relheight=1)
        self.cover.bind("<Configure>", self.draw_cover)
        self.cover.bind("<Button-1>", lambda event: self.start_story())
        self.cover.configure(cursor="hand2")

    def draw_cover(self, event=None):
        """Minh họa nhà sàn bằng Canvas, tự co giãn với màn hình."""
        canvas = self.cover
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 10 or h < 10:
            return
        canvas.create_oval(w * .05, h * .12, w * .05 + h * .28, h * .40,
                           fill="#F0C469", outline="")
        canvas.create_oval(-w * .3, h * .68, w * .8, h * 1.8, fill="#D6DEC3", outline="")
        canvas.create_oval(w * .48, h * .74, w * 1.4, h * 1.7, fill="#BDD0B0", outline="")
        x, y, s = w * .25, h * .53, min(w * .30, h * .78)
        canvas.create_polygon(x - s * .48, y + s * .02, x, y - s * .52,
                              x + s * .48, y + s * .02, fill="#A85334", outline="")
        canvas.create_polygon(x - s * .38, y - s * .02, x, y - s * .43,
                              x + s * .38, y - s * .02, fill="#D99555", outline="")
        canvas.create_rectangle(x - s * .31, y, x + s * .31, y + s * .25,
                                fill="#DBB176", outline="")
        for offset in (-.24, .24):
            canvas.create_line(x + s * offset, y + s * .25, x + s * offset, y + s * .43,
                               fill="#765333", width=5)
        canvas.create_rectangle(x - s * .06, y + s * .05, x + s * .07, y + s * .25,
                                fill="#74543A", outline="")
        canvas.create_line(x, y + s * .26, x + s * .10, y + s * .44,
                           fill="#765333", width=5)
        text_x = w * .70
        canvas.create_text(text_x, h * .28, text="Về Nhà Gươi nghe chuyện", fill=self.GREEN,
                           font=(self.FONT, 11 if self.compact else 17, "bold"))
        canvas.create_text(text_x, h * .49, text="Chạm nhân vật bên trái\nhoặc quét thẻ của em.",
                           fill=self.INK, justify="center", width=w * .49,
                           font=(self.FONT, 10 if self.compact else 12))
        canvas.create_text(text_x, h * .74, text="Chạm để bắt đầu", fill=self.ORANGE,
                           font=(self.FONT, 10 if self.compact else 12, "bold"))

    def build_question_tab(self):
        tk, ttk = self.tk, self.ttk
        top = tk.Frame(self.qa_tab, bg=self.BG)
        top.pack(fill="x", pady=(0, 8))
        self.label(top, "Em muốn tìm hiểu gì?", size=15, bold=True).pack(side="left")
        self.mic_button = self.button(top, "Hỏi bằng mic", self.listen, "Mic.TButton", side="right")
        self.button(top, "Dừng đọc", self.stop_speech, side="right")
        entry_row = tk.Frame(self.qa_tab, bg=self.BG)
        entry_row.pack(fill="x", pady=(0, 8))
        self.label(entry_row, "Câu hỏi", bold=True).pack(side="left", padx=(0, 8))
        self.question = tk.StringVar()
        self.question_entry = ttk.Entry(entry_row, textvariable=self.question, style="Story.TEntry",
                                        font=(self.FONT, 14), exportselection=False, width=1)
        self.question_entry.pack(side="left", fill="x", expand=True)
        self.question_entry.bind("<Return>", lambda event: self.submit_typed_question())
        self.question_entry.bind("<ButtonRelease-1>", self.open_question_keyboard, add="+")
        self.button(entry_row, "Bàn phím", self.toggle_question_keyboard)
        self.button(entry_row, "Gửi", self.submit_typed_question, "Primary.TButton")
        self.audio_status = tk.StringVar(value="Chọn câu hỏi để xem và nghe trả lời.")
        self.audio_label = self.label(self.qa_tab, textvariable=self.audio_status, size=9,
                                      fg=self.MUTED, anchor="w")
        self.audio_label.pack(fill="x", pady=(0, 8))
        body = tk.Frame(self.qa_tab, bg=self.BG)
        self.question_body = body
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=2, uniform="qa")
        body.columnconfigure(1, weight=3, uniform="qa")
        body.rowconfigure(0, weight=1)
        for column, title in ((0, "CÂU HỎI GỢI Ý"), (1, "CÂU TRẢ LỜI")):
            panel = tk.Frame(body, bg=self.PAPER, padx=10, pady=8,
                             highlightthickness=1, highlightbackground=self.LINE)
            panel.grid(row=0, column=column, sticky="nsew", padx=(0, 8) if column == 0 else 0)
            self.label(panel, title, size=9, bold=True, fg=self.GREEN,
                       bg=self.PAPER).pack(anchor="w", pady=(0, 8))
            scroll = ttk.Scrollbar(panel, style="Story.Vertical.TScrollbar")
            scroll.pack(side="right", fill="y")
            if column == 0:
                self.questions = TouchQuestionList(panel)
                self.questions.canvas.configure(yscrollcommand=scroll.set)
                self.questions.pack(fill="both", expand=True)
                self.questions.bind("<<ListboxSelect>>", self.choose_question)
                scroll.configure(command=self.questions.yview)
            else:
                self.output = tk.Text(panel, width=1, height=1, wrap="word", state="disabled",
                                      bg=self.PAPER, fg=self.INK, font=(self.FONT, 12),
                                      relief="flat", highlightthickness=0, padx=4,
                                      spacing1=4, spacing3=8, yscrollcommand=scroll.set)
                self.output.pack(fill="both", expand=True)
                scroll.configure(command=self.output.yview)
        self.question_keyboard = TouchKeyboard(self.qa_tab, self.question_entry, self.ask,
                                               before=body, hide_when_open=(top, self.audio_label))

    def open_question_keyboard(self, event=None):
        # Bàn phím thuộc chính cửa sổ nên không bị lớp fullscreen che khuất.
        if self.root.attributes("-fullscreen"):
            self.question_keyboard.show()

    def toggle_question_keyboard(self):
        self.question_keyboard.toggle()

    def submit_typed_question(self):
        self.question_keyboard.hide()
        self.ask()

    def build_setup_tab(self):
        tk, ttk = self.tk, self.ttk
        # Settings can exceed 480px; keep every control reachable by scrolling.
        canvas = tk.Canvas(self.setup_tab, bg=self.BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self.setup_tab, command=canvas.yview,
                               style="Story.Vertical.TScrollbar")
        scroll.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        form = tk.Frame(canvas, bg=self.BG)
        window = canvas.create_window(0, 0, window=form, anchor="nw")
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        form.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        self.label(form, "Góc thầy cô", size=17, bold=True).pack(anchor="w")
        self.label(form, "Chọn nhân vật để gán nội dung và thiết bị.", fg=self.MUTED).pack(anchor="w", pady=(2, 10))
        self.choice = ttk.Combobox(form, state="readonly", style="Story.TCombobox", width=24,
                                   values=[CHARACTERS[c]["name"] for c in self.ids])
        self.choice.current(0)
        self.choice.pack(anchor="w", fill="x")
        self.choice.bind("<<ComboboxSelected>>", self.select_for_setup)
        self.details = tk.StringVar()
        self.label(form, textvariable=self.details, bg=self.PAPER, anchor="w",
                   justify="left", wraplength=700, padx=12, pady=12, size=10).pack(fill="x", pady=10)
        files = tk.Frame(form, bg=self.BG)
        files.pack(fill="x")
        for title, key in (("Chọn video", "video"), ("Chọn lời thoại", "transcript"),
                           ("Bộ hỏi đáp", "questions")):
            self.button(files, title, lambda k=key: self.select_file(k))
        self.button(files, "Nạp nội dung", self.learn, "Primary.TButton")
        enrollment = tk.Frame(form, bg=self.BG)
        enrollment.pack(fill="x", pady=10)
        self.assign_button = self.button(enrollment, "Gán thẻ cho nhân vật", self.enroll)
        self.assign_button.configure(state="disabled")
        self.button(enrollment, "Hủy gán", self.cancel_enrollment)
        mic_row = tk.Frame(form, bg=self.BG)
        mic_row.pack(fill="x", pady=(0, 10))
        self.microphone = tk.StringVar(value="" if self.config.get("microphone") is None
                                       else str(self.config["microphone"]))
        self.label(mic_row, "Mic (số/tên)").pack(side="left")
        ttk.Entry(mic_row, textvariable=self.microphone, width=20,
                  style="Story.TEntry").pack(side="left", padx=8)
        self.button(mic_row, "Lưu mic", self.save_microphone)
        self.button(mic_row, "Đóng ứng dụng", self.close, side="right")
        self.label(form, "Để trống để dùng mic mặc định. F11: toàn màn hình · Esc: thu nhỏ.",
                   fg=self.MUTED, size=10, wraplength=700).pack(anchor="w", pady=(0, 12))

    def refresh_character_ui(self):
        self.character_title.configure(text=CHARACTERS[self.cid]["name"])
        for cid, button in self.character_buttons.items():
            selected = cid == self.cid
            button.configure(bg=theme.SELECTED if selected else self.PAPER,
                             highlightbackground=self.ORANGE if selected else self.PAPER)

    def select_for_setup(self, event=None):
        # Chọn để gán file không phát video hoặc rời màn hình thiết lập.
        self.stop_playback()
        self.invalidate()
        self.pending = None
        self.cid = self.ids[self.choice.current()]
        self.refresh_details()
        self.status.set("Đã chọn nhân vật. Thầy cô có thể chọn video, lời thoại hoặc bộ hỏi đáp.")

    def start_story(self):
        self.select(self.cid)

    def toggle_fullscreen(self, event=None):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def resize_status(self, event):
        # A single fixed-height line keeps content still while status changes.
        pass

    def update_status_color(self, *args):
        recording = "MIC ĐANG THU" in self.status.get()
        self.status_label.configure(bg="#F8E6DD" if recording else self.BG,
                                    fg=self.ORANGE if recording else self.MUTED)
        self.mic_button.configure(text="Đang nghe..." if recording else "Hỏi bằng mic")
