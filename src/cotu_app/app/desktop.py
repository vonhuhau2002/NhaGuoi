"""Main desktop application: coordinate the independent feature modules."""
import argparse
import ctypes
import ctypes.util
import importlib.util
import multiprocessing as mp
import os
from pathlib import Path
import queue
import subprocess
import sys
from cotu_app.core.paths import BASE, CONFIG_DIR, MODEL_DIR, RUN_DIR
from cotu_app.core.files import write_json, resolve_path
from cotu_app.core.settings import CONFIG, load_config
from cotu_app.features.stories.characters import CHARACTERS
from cotu_app.features.stories.answers import answer_question
from cotu_app.features.stories.questions import load_story_questions, question_title
from cotu_app.features.video.content import video_digest
from cotu_app.features.rfid.cards import assign_card, load_cards
from cotu_app.features.rfid.reader import reader_process
from cotu_app.features.gpio.buttons import StoryButtons, button_mapping, test_buttons
from cotu_app.features.chatbot.integration import (chatbot_tab_changed, close_chatbot,
    mount_chatbot, open_chatbot, reload_curated, sync_character)
from cotu_app.features.tts.voices import load_voice_styles, voice_for
from cotu_app.features.tts.output import (OUTPUT_FILE, choose_output_device,
    choose_output_format, test_output_tone)
from cotu_app.features.tts.service import (prepare_answers, shutdown_speech,
    speech_error, start_speech)
from cotu_app.ui.video import VideoInterface
from .media_worker import speech_worker
from cotu_app.core.branding import CHAT_NAME

CARDS = CONFIG_DIR / "rfid_cards.json"

class VideoApp(VideoInterface):
    def __init__(self, root, config_path=CONFIG, no_rfid=False, buttons=False):
        import tkinter as tk
        from tkinter import ttk
        import vlc

        self.root, self.tk, self.ttk, self.vlc = root, tk, ttk, vlc
        self.config_path = Path(config_path).resolve()
        self.config = load_config(self.config_path)
        self.cards = load_cards(CARDS)
        self.cid = "elder"
        self.knowledge = None
        self.visible_questions = []
        self.pending = None
        self.busy = False
        self.speech = None
        self.tts_preparation = None
        self.closed = False
        self.playback_watch = False
        self.reader_ready = False
        self.button_events = queue.Queue(maxsize=16)
        self.story_buttons = None
        self.context = mp.get_context("spawn")
        self.revision = self.context.Value("i", 0)
        self.results = self.context.Queue()
        self.jobs = self.context.Queue()
        self.rfid_events = self.context.Queue()
        self.reader_stop = self.context.Event()
        self.reader = None
        self.worker = None
        self.instance = vlc.Instance("--no-video-title-show", "--quiet")
        if self.instance is None:
            raise RuntimeError("Không khởi tạo được libVLC. Kiểm tra cài đặt VLC.")
        self.player = self.instance.media_player_new()
        self.build_interface()
        mount_chatbot(self, self.config)
        root.update_idletasks()
        if sys.platform == "win32":
            self.player.set_hwnd(self.surface.winfo_id())
        elif sys.platform.startswith("linux"):
            self.player.set_xwindow(self.surface.winfo_id())
        else:
            raise RuntimeError("Bản nhúng video này hỗ trợ Raspberry Pi/Linux X11 và Windows.")
        self.player.video_set_mouse_input(False)
        self.player.video_set_key_input(False)
        self.worker = self.context.Process(target=speech_worker, args=(self.jobs, self.results, self.revision), daemon=True)
        self.worker.start()
        if not no_rfid:
            self.reader = self.context.Process(target=reader_process, args=(self.rfid_events, self.reader_stop), daemon=True)
            self.reader.start()
        if buttons:
            try:
                self.story_buttons = StoryButtons(button_mapping(self.config, CHARACTERS), self.button_events)
                self.status.set("Đã bật 4 nút GPIO. Bấm nút để nghe câu chuyện tương ứng.")
            except Exception as error:
                message = f"Lỗi nút GPIO: {error}. Xem mục 7 trong docs/HUONG_DAN_VIDEO.md."
                self.status.set(message)
                print(message, file=sys.stderr)
        self.poll_id = root.after(100, self.poll)

    def invalidate(self):
        panel = getattr(self, "chat_panel", None)
        if panel is not None:
            panel.reset()
        with self.revision.get_lock():
            self.revision.value += 1
        self.busy = False
        self.mic_button.configure(state="normal")
        self.knowledge = None
        self.visible_questions = []
        self.questions.delete(0, "end")
        self.question.set("")
        self.show("")
        self.stop_speech()

    def select(self, cid):
        self.stop_playback()
        self.invalidate()
        self.pending = None
        self.cid = cid
        self.choice.current(self.ids.index(cid))
        self.refresh_details()
        self.tabs.select(self.video_tab)
        self.play()
        self.learn()

    def refresh_details(self):
        sync_character(self)
        self.refresh_character_ui()
        story = self.config["stories"][self.cid]
        voice, rate = voice_for(self.cid)
        uid = next((key for key, value in self.cards.items() if value == self.cid), "chưa gán")
        filename = lambda value, fallback: Path(value).name if value else fallback
        self.details.set(f"{CHARACTERS[self.cid]['name']} · Thẻ: {uid}\n"
                         f"Video: {filename(story.get('video'), 'chưa chọn')}\n"
                         f"Lời thoại: {filename(story.get('transcript'), 'nhận dạng từ video')}\n"
                         f"Bộ hỏi đáp: {filename(story.get('questions'), 'chưa có')}")

    def play(self):
        if self.busy:
            self.status.set("Hãy chờ tác vụ hiện tại xong trước khi phát video.")
            return
        video = resolve_path(self.config_path, self.config["stories"][self.cid].get("video"))
        if video is None or not video.is_file() or video.suffix.lower() != ".mp4":
            self.status.set("Chưa có MP4. Vào Thiết lập → Chọn video cho nhân vật đang chọn.")
            return
        self.stop_speech()
        self.player.stop()
        media = self.instance.media_new(str(video))
        self.player.set_media(media)
        media.release()
        self.cover.place_forget()
        self.playback_watch = True
        if self.player.play() == -1:
            self.playback_watch = False
            self.cover.place(relwidth=1, relheight=1)
            self.status.set("Không phát được video. Kiểm tra VLC, đường dẫn và âm thanh.")
        else:
            self.status.set(f"Đang phát: {video.name}")

    def pause(self):
        self.player.set_pause(1)

    def resume(self):
        if self.busy:
            self.status.set("Hãy chờ nạp nội dung hoặc nhận dạng xong rồi tiếp tục nghe chuyện nhé.")
            return
        if not self.playback_watch:
            self.start_story()
            return
        self.cover.place_forget()
        self.stop_speech()
        self.player.set_pause(0)

    def stop_playback(self):
        self.player.stop()
        self.playback_watch = False
        self.cover.place(relwidth=1, relheight=1)

    def submit(self, kind):
        if self.busy:
            self.status.set("Đang xử lý. Hãy chờ hoặc chọn nhân vật khác để hủy tác vụ cũ.")
            return
        self.busy = True
        self.mic_button.configure(state="disabled")
        self.jobs.put((self.revision.value, kind, str(self.config_path), self.config, self.cid))
        self.status.set("Đang chuẩn bị mic..." if kind == "listen" else "Đang nạp nội dung video...")

    def learn(self):
        # Không xóa bộ hiện hành nếu tác vụ đang chạy.
        if not self.busy:
            self.knowledge = None
            self.questions.delete(0, "end")
            self.show("Đang nạp nội dung của video hiện tại...")
        self.submit("learn")

    def listen(self):
        if self.knowledge is None:
            self.status.set("Hãy nạp bộ hỏi đáp hoặc học lời thoại trước khi hỏi bằng mic.")
            return
        if self.busy:
            return
        self.pause()
        self.stop_speech()
        self.submit("listen")

    def ask(self):
        if self.busy:
            self.status.set("Hãy chờ nhận dạng/học nội dung hoàn tất.")
            return
        self.pause()
        self.stop_speech()
        result = answer_question(self.question.get(), self.knowledge)
        if not result.approved and self.question.get().strip() and open_chatbot(self, self.question.get()):
            return
        speaker = result.character_id or self.cid
        narrator = f"{CHARACTERS[speaker]['name']} trả lời:\n" if result.approved else ""
        citation = f"Nguồn: {result.source}\n\n" if result.source else ""
        self.show(f"Câu hỏi: {self.question.get()}\n\n{citation}{narrator}{result.text}")
        if result.approved:
            try:
                self.speech = start_speech(result.text, speaker)
                self.status.set(f"Đang chuẩn bị phát câu trả lời của {CHARACTERS[speaker]['name']}...")
            except (OSError, ValueError, RuntimeError) as error:
                self.status.set(f"Đã có đáp án trên màn hình; lỗi đọc: {error}")

    def choose_question(self, event=None):
        selected = self.questions.curselection()
        if selected and self.knowledge:
            self.question.set(question_title(self.visible_questions[selected[0]]))
            self.ask()

    def show(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def stop_speech(self):
        if self.speech is not None:
            if self.speech.poll() is None:
                self.speech.terminate()
                try:
                    self.speech.wait(timeout=0.3)
                except subprocess.TimeoutExpired:
                    self.speech.kill()
                    self.speech.wait(timeout=1)
            if hasattr(self.speech, "tts_errors"):
                self.speech.tts_errors.close()
            self.speech = None

    def select_file(self, key):
        from tkinter import filedialog
        types = {"video": [("Video MP4", "*.mp4")],
                 "transcript": [("Lời thoại TXT/SRT", "*.txt *.srt")],
                 "questions": [("Bộ hỏi đáp JSON", "*.json")]}
        value = filedialog.askopenfilename(parent=self.root, filetypes=types[key])
        if not value:
            return
        updated = json.loads(json.dumps(self.config))
        story = updated["stories"][self.cid]
        story[key] = str(Path(value).resolve())
        if key == "video":
            story["transcript"], story["questions"] = "", ""
        try:
            write_json(self.config_path, updated)
        except OSError as error:
            self.status.set(f"Không lưu được cấu hình: {error}")
            return
        self.stop_playback()
        self.invalidate()
        self.config = updated
        reload_curated(self)
        self.refresh_details()
        self.status.set("Đã lưu. Vào Thiết lập → Nạp nội dung hoặc chọn lại nhân vật.")

    def save_microphone(self):
        value = self.microphone.get().strip()
        updated = dict(self.config)
        updated["microphone"] = int(value) if value.isdecimal() else value or None
        try:
            write_json(self.config_path, updated)
        except OSError as error:
            self.status.set(f"Không lưu được mic: {error}")
            return
        self.invalidate()
        self.config = updated
        self.status.set("Đã lưu mic. Bấm Nạp nội dung rồi thử Hỏi bằng mic.")

    def enroll(self):
        if self.reader_ready:
            self.pending = self.cid
            self.status.set(f"Rút thẻ, chờ 2 giây rồi quét thẻ để gán cho {CHARACTERS[self.cid]['name']}.")

    def cancel_enrollment(self):
        self.pending = None
        self.status.set("Đã hủy gán thẻ.")

    def tab_changed(self, event=None):
        chatbot_tab_changed(self)
        if hasattr(self, "question_keyboard") and self.tabs.select() != str(self.qa_tab):
            self.question_keyboard.hide()
        if self.pending and self.tabs.select() != str(self.setup_tab):
            self.cancel_enrollment()
        if self.tabs.select() == str(self.qa_tab):
            self.pause()

    def handle_uid(self, uid):
        from tkinter import messagebox
        if self.pending:
            target = self.pending
            self.pending = None
            owner = self.cards.get(uid)
            previous = next((key for key, value in self.cards.items() if value == target), None)
            if (owner and owner != target) or (previous and previous != uid):
                if not messagebox.askyesno("Đổi gán thẻ", "Thay gán cũ bằng thẻ và nhân vật này?", parent=self.root):
                    return
            try:
                self.cards = assign_card(self.cards, uid, target, CARDS)
            except (OSError, ValueError) as error:
                self.status.set(f"Không lưu được thẻ: {error}")
                return
            self.refresh_details()
            self.status.set("Đã gán thẻ. Rút ra rồi quét lại để phát video.")
        elif uid in self.cards:
            self.select(self.cards[uid])
        else:
            self.status.set(f"Thẻ {uid} chưa gán. Chọn nhân vật, vào Thiết lập → Gán thẻ.")

    def handle_result(self, event):
        kind, epoch, payload = event
        if epoch != self.revision.value:
            return
        if kind == "progress":
            self.status.set(payload)
            return
        task, value, error = payload
        self.busy = False
        self.mic_button.configure(state="normal")
        if error:
            self.status.set(error)
            return
        if task == "learn":
            self.knowledge = value
            try:
                self.tts_preparation = prepare_answers(value.questions, self.cid)
            except (OSError, ValueError, RuntimeError) as error:
                self.tts_preparation = None
                self.audio_status.set(f"Chưa chuẩn bị được âm thanh: {error}")
            self.visible_questions = sorted(
                value.questions,
                key=lambda item: (list(CHARACTERS).index(item.get("character_id", self.cid)),
                                  item.get("source_type") != "document"),
            )
            for item in self.visible_questions:
                owner = item.get("character_id")
                title = question_title(item)
                label = f"{CHARACTERS[owner]['name']} • {title}" if owner else title
                if item.get("source_type") == "document":
                    label = "Mẫu chuyện • " + label
                self.questions.insert("end", label)
            self.show(("Già làng sẵn sàng nghe em hỏi!\n\n" if value.questions
                       else "Đã nạp lời thoại; cần thêm bộ hỏi đáp để trả lời bằng giọng nói.\n\n")
                      + (f"Có {len(value.questions)} câu hỏi mẫu. Chạm một câu bên trái để nghe trả lời.\n\n"
                         if value.questions else "Chưa có câu hỏi mẫu. Nhờ thầy cô thêm bộ hỏi đáp nhé.\n\n")
                      + "Em cũng có thể gõ câu hỏi hoặc bấm Hỏi bằng mic. Chờ dòng MIC ĐANG THU rồi nói nhé!\n\n"
                      + f"Nguồn nội dung: {value.source}. Lời thoại tự động cần thầy cô kiểm tra.")
            self.status.set(f"Đã nạp {len(value.questions)} câu hỏi. Sẵn sàng hỏi đáp." if value.questions
                            else "Đã nạp lời thoại. Chưa có bộ hỏi đáp: vào Thiết lập → Bộ hỏi đáp.")
        else:
            self.question.set(value)
            self.ask()

    def poll(self):
        for events, handler in ((self.rfid_events, self.handle_reader_event), (self.results, self.handle_result),
                                (self.button_events, self.handle_button)):
            for _ in range(20):
                try:
                    handler(events.get_nowait())
                except queue.Empty:
                    break
        if self.playback_watch:
            state = self.player.get_state()
            if state == self.vlc.State.Ended:
                self.playback_watch = False
                self.status.set("Câu chuyện đã kết thúc! Chạm Hỏi đáp để cùng tìm hiểu thêm.")
            elif state == self.vlc.State.Error:
                self.playback_watch = False
                self.status.set("VLC báo lỗi phát video. Kiểm tra MP4 và đầu ra âm thanh.")
        if self.speech is not None and self.speech.poll() is not None:
            if self.speech.returncode:
                self.status.set(f"Không đọc được đáp án: {speech_error(self.speech)}")
            else:
                speech_error(self.speech)
                self.status.set("Đã đọc xong câu trả lời.")
            self.speech = None
        audio_messages = []
        if self.speech is not None:
            audio_messages.append(self.speech.message)
            if self.chat_tab is not None and self.tabs.select() == str(self.chat_tab):
                self.status.set(self.speech.message)
        if self.tts_preparation is not None:
            preparation = self.tts_preparation
            if preparation.poll() is None:
                audio_messages.append(f"Âm thanh có sẵn {preparation.completed}/{preparation.total} · "
                                      f"{preparation.message}")
            elif preparation.returncode:
                audio_messages.append(f"Lỗi chuẩn bị âm thanh: {preparation.message}")
            else:
                audio_messages.append(f"Sẵn sàng nghe {preparation.total} câu trả lời.")
        if audio_messages:
            self.audio_status.set(" | ".join(audio_messages))
        if self.worker is not None and not self.worker.is_alive():
            self.busy = False
            self.mic_button.configure(state="disabled")
            self.status.set("Tiến trình nhận dạng đã dừng. Kiểm tra RAM/thư viện rồi mở lại ứng dụng.")
        self.poll_id = self.root.after(100, self.poll)

    def handle_button(self, cid):
        if not self.closed and cid in button_mapping(self.config, CHARACTERS):
            self.select(cid)

    def handle_reader_event(self, event):
        kind, value = event
        if kind == "uid":
            self.handle_uid(value)
        else:
            self.reader_ready = kind == "ready"
            self.assign_button.configure(state="normal" if self.reader_ready else "disabled")
            self.status.set(value if self.reader_ready else f"Lỗi RFID: {value}")

    def close(self):
        if self.closed:
            return
        self.closed = True
        close_chatbot(self)
        self.root.after_cancel(self.poll_id)
        if self.story_buttons is not None:
            self.story_buttons.close()
        with self.revision.get_lock():
            self.revision.value += 1
        self.stop_speech()
        self.stop_playback()
        shutdown_speech()
        self.reader_stop.set()
        self.jobs.put(None)
        for process in (self.reader, self.worker):
            if process is not None:
                process.join(timeout=0.3)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=0.5)
        for events in (self.jobs, self.results, self.rfid_events):
            events.cancel_join_thread()
            events.close()
        self.player.release()
        self.instance.release()
        self.root.destroy()


def initialize_x11():
    """libVLC yêu cầu XInitThreads trước Tk/XOpenDisplay trên Linux."""
    if sys.platform.startswith("linux"):
        name = ctypes.util.find_library("X11")
        if not name or not ctypes.CDLL(name).XInitThreads():
            raise RuntimeError("Không khởi tạo được X11 cho video nhúng. Hãy dùng phiên desktop X11/XWayland.")


def use_project_environment():
    """Chạy trực tiếp trên Pi vẫn dùng venv và PortAudio đã cài trong dự án."""
    if not sys.platform.startswith("linux"):
        return
    launcher = BASE / "run_video.sh"
    python = BASE / ".venv-video" / "bin" / "python"
    if (os.environ.get("NHARONG_VIDEO_ENV") != str(BASE)
            and launcher.is_file() and python.is_file()):
        os.execv("/bin/sh", ["/bin/sh", str(launcher), *sys.argv[1:]])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--no-rfid", action="store_true", help="Chạy thử bằng nút chọn nhân vật")
    parser.add_argument("--chatbot", action="store_true", help=f"Mở ứng dụng tại tab {CHAT_NAME}")
    parser.add_argument("--buttons", action="store_true", help="Bật 4 nút vật lý GPIO trên Raspberry Pi 5")
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument("--test-buttons", action="store_true", help="Thử 4 nút ở Terminal, Ctrl+C để thoát")
    parser.add_argument("--list-mics", action="store_true")
    parser.add_argument("--check-audio", action="store_true", help="Kiểm tra loa/ngõ ra cho ZeroTTS")
    parser.add_argument("--test-audio", action="store_true", help="Phát tiếng thử qua loa ZeroTTS, không nạp model")
    parser.add_argument("--test-tts", action="store_true", help="Đọc một câu thử bằng ZeroTTS qua loa đã chọn")
    parser.add_argument("--prepare-tts", action="store_true", help="Tạo sẵn WAV của bộ hỏi đáp; không mở loa/giao diện")
    parser.add_argument("--set-audio-device", metavar="ID", help="Lưu ngõ ra ZeroTTS (số PortAudio, alsa:1 hoặc alsa-name:tên loa)")
    parser.add_argument("--video-sha256", type=Path, help="In SHA256 để gắn đúng bộ hỏi đáp với MP4")
    checks.add_argument("--check", action="store_true", help="Kiểm tra cấu hình/thư viện, không mở thiết bị")
    args = parser.parse_args(argv)
    try:
        if args.video_sha256:
            print(video_digest(args.video_sha256))
            return 0
        if args.list_mics:
            import sounddevice as sd
            print(sd.query_devices())
            return 0
        if args.check_audio:
            import sounddevice as sd
            outputs = [(index, item) for index, item in enumerate(sd.query_devices())
                       if item["max_output_channels"] > 0]
            if not outputs:
                print("Pi không thấy thiết bị phát âm thanh (ALSA/PortAudio).", file=sys.stderr)
                return 1
            for index, item in outputs:
                print(f"#{index}: {item['name']} ({item['max_output_channels']} kênh ra)")
            selected = choose_output_device(sd)
            sample_rate, dtype, channels = choose_output_format(
                sd, selected, sd.query_devices(selected)["max_output_channels"])
            print(f"ZeroTTS sẽ dùng thiết bị #{selected}: {dtype}, {sample_rate} Hz, {channels} kênh")
            return 0
        if args.test_audio:
            device, sample_rate, dtype, channels = test_output_tone()
            print(f"Đã gửi tiếng thử tới loa #{device}: {dtype}, {sample_rate} Hz, {channels} kênh. "
                  "Nếu không nghe thấy, kiểm tra âm lượng/ngõ ra hệ thống.")
            return 0
        if args.test_tts:
            print("Đang nạp ZeroTTS và đọc câu thử bằng giọng Già làng; vui lòng chờ...", flush=True)
            process = start_speech("Xin chào, đây là câu trả lời thử của Già làng.", "elder")
            try:
                code = process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                speech_error(process)
                raise RuntimeError("ZeroTTS quá 180 giây chưa đọc xong; kiểm tra RAM và tải CPU.")
            except KeyboardInterrupt:
                process.terminate()
                process.wait()
                speech_error(process)
                return 130
            detail = speech_error(process)
            if code:
                raise RuntimeError(detail.removeprefix("RuntimeError: "))
            print("ZeroTTS đã gửi câu thử tới loa. Nếu vẫn im lặng, kiểm tra âm lượng/ngõ ra hệ thống.")
            return 0
        if args.set_audio_device:
            import sounddevice as sd
            chosen = choose_output_device(sd, requested=args.set_audio_device)
            write_json(OUTPUT_FILE, {"output_device": args.set_audio_device})
            print(f"Đã lưu ngõ ra ZeroTTS: {args.set_audio_device} → PortAudio #{chosen}")
            return 0
        config = load_config(args.config)
        if args.prepare_tts:
            questions, seen = [], set()
            for cid, story in config["stories"].items():
                bank = resolve_path(args.config, story.get("questions"))
                if bank is None and not config.get("document_questions"):
                    continue
                video = resolve_path(args.config, story.get("video"))
                for item in load_story_questions(args.config, config, cid, video_digest(video)):
                    owner = item.get("character_id", cid)
                    key = (item["answer"], owner)
                    if key not in seen:
                        seen.add(key)
                        questions.append({**item, "character_id": owner})
            if not questions:
                raise ValueError("Chưa có bộ hỏi đáp để tạo âm thanh.")
            job = prepare_answers(questions)
            last = None
            try:
                while job.poll() is None:
                    message = f"{job.completed}/{job.total} · {job.message}"
                    if message != last:
                        print(message, flush=True)
                        last = message
                    try:
                        job.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        pass
                print(job.message, flush=True)
                if job.returncode:
                    raise RuntimeError(job.message)
                return 0
            finally:
                shutdown_speech()
        if args.test_buttons:
            return test_buttons(button_mapping(config, CHARACTERS), CHARACTERS)
        load_cards(CARDS)
        if args.check:
            modules = ["vlc", "faster_whisper", "sounddevice", "zerotts"]
            if args.buttons:
                modules.extend(("gpiozero", "lgpio"))
            missing = [name for name in modules
                       if importlib.util.find_spec(name) is None]
            print(f"Python: {sys.executable}\nCấu hình: {args.config.resolve()}")
            print("Thiếu module: " + (", ".join(missing) or "không"))
            print("ZeroTTS model: " + (str(MODEL_DIR) if (MODEL_DIR / "config.json").is_file()
                                         else "chưa tải; xem docs/HUONG_DAN_VIDEO.md"))
            for cid, (voice, rate) in load_voice_styles().items():
                print(f"  {CHARACTERS[cid]['name']}: {voice} (nhịp {rate:.2f})")
            for cid, story in config["stories"].items():
                path = resolve_path(args.config, story.get("video"))
                print(f"{cid}: {path} — {'có file' if path and path.is_file() else 'chưa có MP4'}")
            print("Nút GPIO: " + ("bật" if args.buttons else "tắt; thêm --buttons để bật"))
            for cid, pin in button_mapping(config, CHARACTERS).items():
                print(f"  GPIO{pin} → {CHARACTERS[cid]['name']} ({cid})")
            print("Chưa mở màn hình, RFID, GPIO hay mic; chưa kiểm tra libVLC hoặc tốc độ ASR.")
            return 1 if missing or not (MODEL_DIR / "config.json").is_file() else 0
        initialize_x11()
        args.config = args.config.resolve()
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        os.chdir(RUN_DIR)
        import tkinter as tk
        root = tk.Tk()
        try:
            app = VideoApp(root, args.config, args.no_rfid, args.buttons)
            if args.chatbot:
                open_chatbot(app)
        except Exception:
            root.destroy()
            raise
        root.mainloop()
        return 0
    except Exception as error:
        print(f"Không chạy được: {type(error).__name__}: {error}", file=sys.stderr)
        print("Xem docs/HUONG_DAN_VIDEO.md để cài thư viện và chuẩn bị video/mic.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    use_project_environment()
    mp.freeze_support()
    sys.exit(main())
