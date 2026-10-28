"""Alternative text story application using the same feature services."""
import math
import multiprocessing as mp
import os
from pathlib import Path
import queue
import shutil
import subprocess
import struct
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox, ttk
import wave
from cotu_app.core.branding import APP_NAME
from cotu_app.core.paths import CONFIG_DIR, IMAGES_DIR, RUN_DIR
from cotu_app.features.stories.characters import CHARACTERS
from cotu_app.features.stories.session import StorySession
from cotu_app.features.stories.sample_questions import questions_for
from cotu_app.features.rfid.cards import load_cards, assign_card
from cotu_app.features.rfid.reader import import_rfid_reader, reader_process
from cotu_app.features.chatbot.integration import (chatbot_tab_changed, close_chatbot,
    mount_chatbot, open_chatbot, sync_character)
from cotu_app.features.tts.service import shutdown_speech, speech_error, start_speech

CARDS_FILE = CONFIG_DIR / "rfid_cards.json"

def create_tick(path):
    """Tiếng tích 70 ms, có đường bao để tránh tiếng nổ ở đầu/cuối."""
    rate = 44100
    count = int(rate * 0.07)
    samples = b"".join(
        struct.pack("<h", int(23000 * math.sin(2 * math.pi * 1800 * i / rate)
                              * min(1, i / (rate * 0.003)) * (1 - i / count) ** 2))
        for i in range(count)
    )
    with wave.open(str(path), "wb") as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(rate)
        sound.writeframes(samples)


class LiveApp:
    def __init__(self, root):
        self.root = root
        self.session = StorySession()
        self.cards = load_cards(CARDS_FILE)
        self.sound_directory = tempfile.TemporaryDirectory(prefix="nharong-tick-")
        self.tick_path = Path(self.sound_directory.name) / "tick.wav"
        create_tick(self.tick_path)
        self.tick_process = None
        self.tick_player = shutil.which("aplay") or shutil.which("paplay")
        self.pending = None
        self.speech = None
        self.speech_kind = None
        self.completed_story = None
        self.manual_finish = False
        self.answer_text = ""
        self.events = mp.Queue()
        self.stop = mp.Event()
        self.reader_ready = False
        root.title(APP_NAME + " · Nghe chuyện")
        root.geometry("800x480")
        root.minsize(760, 440)
        root.configure(bg="#EFE5D5")
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<F11>", self.toggle_fullscreen)
        root.bind("<Escape>", lambda event: root.attributes("-fullscreen", False))
        if root.winfo_screenwidth() <= 1024:
            root.attributes("-fullscreen", True)
        root.option_add("*Font", ("DejaVu Sans", 12))
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TNotebook", background="#EFE5D5", borderwidth=0)
        style.configure("TNotebook.Tab", font=("DejaVu Sans", 13, "bold"), padding=(18, 11))
        style.map("TNotebook.Tab", background=[("selected", "#FFF9EF")],
                  foreground=[("selected", "#593A29")])
        style.configure("Touch.TFrame", background="#FFF9EF")

        header = tk.Frame(root, bg="#593A29", height=58)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=APP_NAME.upper(), bg="#593A29", fg="#FFE3A8",
                 font=("DejaVu Sans", 17, "bold")).pack(side="left", padx=14)
        self.touch_button(header, "Thoát", self.close, color="#96513C").pack(side="right", padx=(4, 8), pady=5)
        self.touch_button(header, "Toàn màn hình", self.toggle_fullscreen, color="#79583E").pack(side="right", pady=5)

        self.status = tk.StringVar(value="Đang khởi tạo đầu đọc...")
        status_bar = tk.Label(root, textvariable=self.status, bg="#E4D3B9", fg="#493222",
                              font=("DejaVu Sans", 11), wraplength=740, height=2,
                              anchor="w", justify="left", padx=12)
        status_bar.pack(side="bottom", fill="x")
        root.bind("<Configure>", lambda event: status_bar.configure(
            wraplength=max(300, root.winfo_width() - 30)) if event.widget == root else None)

        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=5)
        reading = ttk.Frame(self.tabs, style="Touch.TFrame", padding=10)
        setup = ttk.Frame(self.tabs, style="Touch.TFrame", padding=10)
        elder = ttk.Frame(self.tabs, style="Touch.TFrame", padding=10)
        self.setup_tab = setup
        self.tabs.add(reading, text="Nghe truyện")
        self.tabs.add(setup, text="Gán thẻ")
        self.tabs.add(elder, text="Già làng kể")
        self.tabs.bind("<<NotebookTabChanged>>", self.tab_changed)
        self.ids = list(CHARACTERS)
        self.enrollment_id = self.ids[0]
        self.portraits, self.small_portraits = self.load_portraits()

        self.title = tk.Label(reading, font=("DejaVu Sans", 16, "bold"),
                              bg="#FFF9EF", fg="#593A29", anchor="w")
        self.title.pack(fill="x", pady=(0, 6))
        controls = tk.Frame(reading, bg="#FFF9EF")
        controls.pack(side="bottom", fill="x", pady=(8, 0))
        self.touch_button(controls, "▶ Đọc lại", self.speak).pack(side="left", padx=(0, 8))
        self.touch_button(controls, "■ Dừng đọc", self.stop_speech, color="#A4513D").pack(side="left")
        self.qa_button = self.touch_button(controls, "Hỏi thêm", self.open_questions, color="#79583E")
        self.qa_button.pack(side="left", padx=8)
        self.auto_speak = tk.BooleanVar(value=True)
        tk.Checkbutton(controls, text="Tự đọc khi quét", variable=self.auto_speak,
                       bg="#FFF9EF", activebackground="#FFF9EF", font=("DejaVu Sans", 12),
                       padx=10, pady=10).pack(side="right")
        text_frame = tk.Frame(reading, bg="#FFF9EF", highlightthickness=2, highlightbackground="#C49A5D")
        text_frame.pack(fill="both", expand=True)
        portrait_frame = tk.Frame(text_frame, bg="#EFE1C7", width=124)
        portrait_frame.pack(side="left", fill="y", padx=(0, 8))
        portrait_frame.pack_propagate(False)
        self.portrait = tk.Label(portrait_frame, bg="#EFE1C7")
        self.portrait.pack(pady=(8, 4))
        self.portrait_caption = tk.Label(portrait_frame, bg="#EFE1C7", fg="#593A29",
                                         wraplength=116, font=("DejaVu Sans", 11, "bold"))
        self.portrait_caption.pack(fill="x")
        tk.Label(portrait_frame, text="Minh họa AI\nTruyện mẫu", bg="#EFE1C7", fg="#725B42",
                 font=("DejaVu Sans", 9)).pack(side="bottom", pady=5)
        scroll_controls = tk.Frame(text_frame, bg="#FFF9EF")
        scroll_controls.pack(side="right", fill="y", padx=(8, 0))
        self.text = tk.Text(text_frame, wrap="word", state="disabled", height=3,
                            font=("DejaVu Sans", 15), padx=12, pady=10, spacing3=8,
                            relief="flat", bg="#F5EBD9", fg="#38291E")
        self.text.pack(fill="both", expand=True)
        self.touch_button(scroll_controls, "▲", lambda: self.text.yview_scroll(-1, "pages")).pack(fill="x", pady=(0, 8))
        self.touch_button(scroll_controls, "▼", lambda: self.text.yview_scroll(1, "pages")).pack(fill="x")

        tk.Label(setup, text="1. Chọn nhân vật     2. Bấm Gán thẻ     3. Quét thẻ",
                 bg="#FFF9EF", fg="#593A29", font=("DejaVu Sans", 12, "bold")).pack(anchor="w", pady=(0, 5))
        grid = tk.Frame(setup, bg="#FFF9EF")
        grid.pack(fill="both", expand=True)
        self.enrollment_buttons = {}
        for index, cid in enumerate(self.ids):
            row, col = divmod(index, 3)
            grid.columnconfigure(col, weight=1, uniform="characters")
            grid.rowconfigure(row, weight=1)
            button = self.touch_button(grid, "", lambda selected=cid: self.choose_enrollment(selected), color="#E7D8C0")
            button.configure(fg="#493222", font=("DejaVu Sans", 12, "bold"), wraplength=220)
            if cid in self.small_portraits:
                button.configure(image=self.small_portraits[cid], compound="left", padx=4, wraplength=160)
            button.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)
            self.enrollment_buttons[cid] = button
        self.uid_label = tk.StringVar(value="UID vừa quét: chưa có")
        tk.Label(setup, textvariable=self.uid_label, bg="#FFF9EF", fg="#6B543D",
                 font=("DejaVu Sans", 10)).pack(anchor="w", pady=4)
        actions = tk.Frame(setup, bg="#FFF9EF")
        actions.pack(fill="x")
        self.assign_button = self.touch_button(actions, "Gán thẻ đã chọn", self.enroll)
        self.assign_button.configure(state="disabled")
        self.assign_button.pack(side="left", padx=(0, 8))
        self.touch_button(actions, "Hủy gán", self.cancel, color="#A4513D").pack(side="left")
        self.touch_button(actions, "Thử tiếng tích", self.play_tick, color="#79583E").pack(side="right")

        tk.Label(elder, text="Chạm một câu chuyện để Già làng kể", bg="#FFF9EF",
                 fg="#593A29", font=("DejaVu Sans", 14, "bold")).pack(anchor="w", pady=(0, 8))
        story_grid = tk.Frame(elder, bg="#FFF9EF")
        story_grid.pack(fill="both", expand=True)
        for index, cid in enumerate(self.ids[1:]):
            row, col = divmod(index, 2)
            story_grid.columnconfigure(col, weight=1, uniform="stories")
            story_grid.rowconfigure(row, weight=1)
            button = self.touch_button(story_grid, CHARACTERS[cid]["name"],
                                       lambda selected=cid: self.elder_tells(selected), color="#79583E")
            if cid in self.small_portraits:
                button.configure(image=self.small_portraits[cid], compound="left")
            button.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        self.questions_tab = ttk.Frame(self.tabs, style="Touch.TFrame", padding=8)
        self.tabs.add(self.questions_tab, text="Hỏi đáp")
        self.question_hint = tk.Label(self.questions_tab, text="", bg="#FFF9EF", fg="#593A29",
                                      font=("DejaVu Sans", 12, "bold"), anchor="w", wraplength=720)
        self.question_hint.pack(fill="x", pady=(0, 6))
        qa_body = tk.Frame(self.questions_tab, bg="#FFF9EF")
        qa_body.pack(fill="both", expand=True)
        self.question_list = tk.Frame(qa_body, bg="#FFF9EF", width=260)
        self.question_list.pack(side="left", fill="y", padx=(0, 8))
        self.question_list.pack_propagate(False)
        answer_frame = tk.Frame(qa_body, bg="#F5EBD9", highlightthickness=2, highlightbackground="#C49A5D")
        answer_frame.pack(fill="both", expand=True)
        qa_controls = tk.Frame(answer_frame, bg="#F5EBD9")
        qa_controls.pack(side="bottom", fill="x")
        self.touch_button(qa_controls, "▲", lambda: self.answer.yview_scroll(-1, "pages")).pack(side="left")
        self.touch_button(qa_controls, "▼", lambda: self.answer.yview_scroll(1, "pages")).pack(side="left", padx=4)
        self.touch_button(qa_controls, "Đọc lại", self.repeat_answer).pack(side="left")
        self.touch_button(qa_controls, "Dừng", self.stop_speech, color="#A4513D").pack(side="left", padx=4)
        self.answer = tk.Text(answer_frame, wrap="word", state="disabled", height=3, width=1,
                              font=("DejaVu Sans", 14), bg="#F5EBD9", fg="#38291E",
                              relief="flat", padx=10, pady=8, spacing3=6)
        self.answer.pack(fill="both", expand=True)
        self.refresh_assignments()
        self.render()
        mount_chatbot(self)
        self.worker = mp.Process(target=reader_process, args=(self.events, self.stop), daemon=True)
        self.worker.start()
        self.poll_id = root.after(100, self.poll)

    def load_portraits(self):
        path = IMAGES_DIR / "village_characters.png"
        portraits, small = {}, {}
        if not path.exists():
            return portraits, small
        try:
            sheet = tk.PhotoImage(file=str(path), master=self.root)
            width, height = sheet.width() // 3, sheet.height() // 2
            for index, cid in enumerate(self.ids):
                row, col = divmod(index, 3)
                tile = tk.PhotoImage(master=self.root)
                tile.tk.call(str(tile), "copy", str(sheet), "-from",
                             col * width, row * height, (col + 1) * width, (row + 1) * height)
                portraits[cid] = tile.subsample(max(1, math.ceil(width / 112)))
                small[cid] = tile.subsample(max(1, math.ceil(width / 42)))
        except tk.TclError as error:
            print(f"Không tải được ảnh minh họa: {error}", file=sys.stderr)
        return portraits, small

    def refresh_questions(self):
        available = questions_for(self.session.character_id, self.session.story_id, self.completed_story)
        for child in self.question_list.winfo_children():
            child.destroy()
        self.answer_text = ""
        self.set_answer("Chạm một câu hỏi để nghe Già làng giải thích thêm." if available else
                        "Phần hỏi đáp chỉ dành cho Già làng sau khi kể xong một câu chuyện. "
                        "Mở mục Già làng kể và chọn truyện trước nhé.")
        if available:
            name = CHARACTERS[self.session.story_id]["name"]
            self.question_hint.configure(text=f"Cùng tìm hiểu: {name} • Câu hỏi có sẵn")
            for question, answer in available:
                button = self.touch_button(self.question_list, question,
                                           lambda q=question, a=answer: self.answer_question(q, a), color="#79583E")
                button.configure(wraplength=230, anchor="w", justify="left", font=("DejaVu Sans", 11, "bold"), pady=9)
                button.pack(fill="both", expand=True, pady=3)
            self.qa_button.configure(text="Hỏi thêm", state="normal")
        else:
            self.question_hint.configure(text="Hỏi Già làng • Nghe truyện xong rồi cùng tìm hiểu")
            can_finish = self.manual_finish and self.session.character_id == "elder" and self.session.story_id != "elder"
            self.qa_button.configure(text="Đã đọc xong" if can_finish else "Hỏi thêm",
                                     state="normal" if can_finish else "disabled")

    def set_answer(self, text):
        self.answer.configure(state="normal")
        self.answer.delete("1.0", "end")
        self.answer.insert("1.0", text)
        self.answer.configure(state="disabled")
        self.answer.yview_moveto(0)

    def open_questions(self):
        if self.manual_finish and self.session.character_id == "elder":
            self.completed_story = self.session.story_id
            self.manual_finish = False
            self.refresh_questions()
        if questions_for(self.session.character_id, self.session.story_id, self.completed_story):
            self.tabs.select(self.questions_tab)

    def answer_question(self, question, answer):
        if (question, answer) not in questions_for(self.session.character_id, self.session.story_id, self.completed_story):
            return
        self.answer_text = answer
        self.set_answer(f"{question}\n\nGià làng giải thích:\n{answer}")
        self.speak(answer, kind="answer")

    def repeat_answer(self):
        if self.answer_text:
            self.speak(self.answer_text, kind="answer")

    @staticmethod
    def touch_button(parent, text, command, color="#527348"):
        return tk.Button(parent, text=text, command=command, bg=color, fg="white",
                         activebackground="#C69958", activeforeground="#30241C",
                         font=("DejaVu Sans", 12, "bold"), relief="flat", bd=0,
                         padx=14, pady=12, cursor="hand2", highlightthickness=1,
                         highlightbackground="#C49A5D")

    def toggle_fullscreen(self, event=None):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def tab_changed(self, event=None):
        chatbot_tab_changed(self)
        if self.pending is not None and self.tabs.select() != str(self.setup_tab):
            self.cancel()

    def choose_enrollment(self, cid):
        if self.pending is not None:
            self.cancel()
        self.enrollment_id = cid
        self.refresh_assignments()

    def refresh_assignments(self):
        by_character = {cid: uid for uid, cid in self.cards.items()}
        for cid, button in self.enrollment_buttons.items():
            selected = cid == self.enrollment_id
            button.configure(text=f"{'✓ ' if selected else ''}{CHARACTERS[cid]['name']}\n{by_character.get(cid, 'Chưa gán thẻ')}",
                             bg="#527348" if selected else "#E7D8C0",
                             fg="white" if selected else "#493222")

    def enroll(self):
        if not self.reader_ready:
            return
        self.stop_speech()
        self.pending = self.enrollment_id
        self.status.set(f"Đang chờ gán cho {CHARACTERS[self.pending]['name']}. Rút thẻ đang đặt, chờ 2 giây rồi quét thẻ cần gán.")

    def cancel(self):
        self.pending = None
        self.status.set("Đã hủy gán. Quét thẻ đã đăng ký để nghe truyện.")

    def handle_uid(self, uid):
        self.play_tick()
        self.uid_label.set(f"UID vừa quét: {uid}")
        if self.pending is not None:
            target = self.pending
            owner = self.cards.get(uid)
            previous = next((key for key, value in self.cards.items() if value == target), None)
            if (owner and owner != target) or (previous and previous != uid):
                if not messagebox.askyesno("Thay đổi gán thẻ", "Thẻ hoặc nhân vật này đã được gán. Chuyển thẻ này sang nhân vật đang chọn và thay thẻ cũ?", parent=self.root):
                    self.pending = None
                    self.status.set("Đã hủy thay đổi gán thẻ.")
                    return
            try:
                self.cards = assign_card(self.cards, uid, target, CARDS_FILE)
            except (OSError, ValueError) as error:
                self.status.set(f"Không lưu được thẻ: {error}. Hãy thử gán lại.")
                self.pending = None
                return
            self.pending = None
            self.refresh_assignments()
            self.status.set(f"Đã lưu thẻ cho {CHARACTERS[target]['name']}.")
        else:
            target = self.cards.get(uid)
            if target is None:
                self.status.set("Thẻ chưa được gán. Chọn nhân vật và bấm Gán thẻ tiếp theo.")
                return
            self.status.set(f"Đã nhận diện {CHARACTERS[target]['name']}.")
        self.stop_speech()
        self.session.select_character(target)
        self.render()
        if self.auto_speak.get():
            self.speak()

    def play_tick(self):
        if self.tick_process is not None and self.tick_process.poll() is None:
            return
        if self.tick_player:
            try:
                self.tick_process = subprocess.Popen(
                    [self.tick_player, str(self.tick_path)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return
            except OSError:
                pass
        self.root.bell()

    def render(self):
        sync_character(self, reset=True)
        self.completed_story = None
        self.manual_finish = not self.auto_speak.get()
        narrator = CHARACTERS[self.session.character_id]["name"]
        story_name = CHARACTERS[self.session.story_id]["name"]
        self.title.configure(text=story_name if narrator == story_name else f"Già làng kể: {story_name}")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.session.story)
        self.text.configure(state="disabled")
        self.text.yview_moveto(0)
        self.portrait.configure(image=self.portraits.get(self.session.character_id, ""))
        self.portrait_caption.configure(text=narrator)
        self.refresh_questions()

    def elder_tells(self, story_id):
        self.session.select_character("elder")
        self.session.elder_tells(story_id)
        self.render()
        self.tabs.select(0)
        self.speak()

    def speak(self, text=None, kind="story"):
        self.stop_speech()
        if kind == "story":
            self.completed_story = None
            self.manual_finish = False
            self.refresh_questions()
        try:
            self.speech = start_speech(
                text if text is not None else self.session.story,
                self.session.character_id,
            )
            self.speech_kind = kind
        except (OSError, ValueError, RuntimeError) as error:
            if kind == "story":
                self.manual_finish = True
                self.refresh_questions()
            self.status.set(f"Không phát được giọng đọc: {error}")

    def stop_speech(self):
        if self.speech is not None and self.speech.poll() is None:
            self.speech.terminate()
            try:
                self.speech.wait(timeout=0.3)
            except subprocess.TimeoutExpired:
                self.speech.kill()
                self.speech.wait()
        if self.speech is not None and hasattr(self.speech, "tts_errors"):
            self.speech.tts_errors.close()
        self.speech = None
        self.speech_kind = None

    def poll(self):
        if self.tick_process is not None and self.tick_process.poll() is not None:
            if self.tick_process.returncode:
                self.root.bell()
                self.status.set("Không phát được tiếng tích. Kiểm tra loa và đầu ra âm thanh trên Pi.")
            self.tick_process = None
        # Giới hạn số sự kiện mỗi lượt để giao diện luôn có thể phản hồi.
        for _ in range(20):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "uid":
                self.handle_uid(value)
            elif kind == "ready":
                self.reader_ready = True
                self.assign_button.configure(state="normal")
                self.status.set(value)
            else:
                self.reader_ready = False
                self.assign_button.configure(state="disabled")
                self.status.set(f"Lỗi RFID: {value}. Kiểm tra kết nối/thư viện rồi mở lại ứng dụng.")
        if self.speech is not None and self.speech.poll() is not None:
            if self.speech.returncode:
                self.status.set(f"Không đọc được: {speech_error(self.speech)}")
                if self.speech_kind == "story":
                    self.manual_finish = True
                    self.refresh_questions()
            elif self.speech_kind == "story" and self.session.character_id == "elder" and self.session.story_id != "elder":
                speech_error(self.speech)
                self.completed_story = self.session.story_id
                self.refresh_questions()
                self.status.set("Già làng đã kể xong. Chạm Hỏi thêm để tìm hiểu câu chuyện.")
            else:
                speech_error(self.speech)
            self.speech = None
            self.speech_kind = None
        self.poll_id = self.root.after(100, self.poll)

    def close(self):
        close_chatbot(self)
        self.root.after_cancel(self.poll_id)
        self.stop_speech()
        shutdown_speech()
        if self.tick_process is not None and self.tick_process.poll() is None:
            self.tick_process.kill()
            self.tick_process.wait()
        self.sound_directory.cleanup()
        self.stop.set()
        self.worker.join(timeout=0.4)
        if self.worker.is_alive():
            self.worker.terminate()
            self.worker.join(timeout=0.4)
        self.events.close()
        self.root.destroy()


if __name__ == "__main__":
    mp.freeze_support()
    if "--check-rfid" in sys.argv:
        try:
            reader_class = import_rfid_reader()
        except RuntimeError as error:
            print(error, file=sys.stderr)
            sys.exit(1)
        print(f"Python: {sys.executable}")
        print(f"Thư viện RFID: {sys.modules[reader_class.__module__].__file__}")
        print("Import thành công; chưa mở SPI/GPIO hoặc đọc thẻ.")
        sys.exit(0)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    os.chdir(RUN_DIR)
    root = tk.Tk()
    try:
        app = LiveApp(root)
        if "--chatbot" in sys.argv:
            open_chatbot(app)
    except (OSError, ValueError) as error:
        messagebox.showerror("Không mở được dữ liệu thẻ", f"{CARDS_FILE}\n{error}\nFile được giữ nguyên để kiểm tra.")
        root.destroy()
    else:
        root.mainloop()
