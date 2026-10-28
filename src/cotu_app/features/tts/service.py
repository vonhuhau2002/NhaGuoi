"""Speech jobs and a persistent ZeroTTS worker, separate from the UI."""
import argparse
import atexit
import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
from cotu_app.core.paths import BASE
from .voices import voice_for

class SpeechJob:
    """Một lượt đọc/chuẩn bị âm thanh, độc lập với đời sống của model."""

    def __init__(self, service, job_id):
        self.service, self.job_id = service, job_id
        self.returncode = None
        self.message = "Đang chuẩn bị âm thanh..."
        self.completed = self.total = 0
        self._done = threading.Event()

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if not self._done.wait(timeout):
            raise subprocess.TimeoutExpired("ZeroTTS", timeout)
        return self.returncode

    def finish(self, code, message):
        if not self._done.is_set():
            self.message, self.returncode = message, code
            self._done.set()

    def terminate(self):
        if self.poll() is None:
            try:
                self.service.send({"kind": "cancel", "id": self.job_id})
            except RuntimeError:
                pass  # Model đã chết vẫn phải cho phép đổi nhân vật/đóng cửa sổ.
            finally:
                self.finish(-15, "Đã dừng giọng đọc.")

    kill = terminate


class SpeechService:
    """Một tiến trình ZeroTTS dùng chung, giao tiếp bằng JSON từng dòng."""

    def __init__(self):
        if importlib.util.find_spec("zerotts") is None:
            raise RuntimeError("Chưa cài zerotts. Dùng .venv-video/bin/python để chạy ứng dụng.")
        self.jobs = {}
        self.sequence = 0
        self.preparation = None
        self._write_lock = threading.Lock()
        self._errors = tempfile.TemporaryFile(mode="w+b")
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-m", "cotu_app.features.tts.service", "--worker"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._errors,
                text=True, encoding="utf-8", bufsize=1, cwd=BASE,
            )
        except OSError:
            self._errors.close()
            raise
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def send(self, command):
        try:
            with self._write_lock:
                self.process.stdin.write(json.dumps(command, ensure_ascii=False) + "\n")
                self.process.stdin.flush()
        except (OSError, ValueError) as error:
            raise RuntimeError("Tiến trình ZeroTTS đã dừng; hãy thử lại.") from error

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                job = self.jobs.get(event.get("id"))
                if job is None:
                    continue
                if job.poll() is not None:
                    if "code" in event:
                        self.jobs.pop(job.job_id, None)
                    continue
                job.message = event.get("message", job.message)
                job.completed = event.get("completed", job.completed)
                job.total = event.get("total", job.total)
                if "code" in event:
                    job.finish(event["code"], job.message)
                    self.jobs.pop(job.job_id, None)
        finally:
            code = self.process.wait()
            self._errors.seek(0)
            lines = self._errors.read().decode("utf-8", errors="replace").splitlines()
            message = next((line for line in reversed(lines) if line.strip()), "")
            if code < 0:
                message = f"ZeroTTS bị dừng bởi tín hiệu {-code} (có thể thiếu RAM). {message}"
            for job in list(self.jobs.values()):
                job.finish(code or 1, message or "Tiến trình ZeroTTS đã dừng.")
            self.jobs.clear()

    def request(self, kind, **data):
        if kind == "warmup":
            previous = getattr(self, "warmup_job", None)
            if previous is not None and previous.poll() in (None, 0):
                return previous
        if kind == "prepare" and self.preparation is not None:
            signature, previous = self.preparation
            if signature == data and previous.poll() in (None, 0):
                return previous
            previous.terminate()
        self.sequence += 1
        job = SpeechJob(self, self.sequence)
        self.jobs[job.job_id] = job
        try:
            self.send({"kind": kind, "id": job.job_id, **data})
        except RuntimeError:
            self.jobs.pop(job.job_id, None)
            raise
        if kind == "prepare":
            self.preparation = (data, job)
        if kind == "warmup":
            self.warmup_job = job
        return job

    def close(self):
        if self.process.poll() is None:
            try:
                self.send({"kind": "shutdown"})
                self.process.wait(timeout=0.5)
            except (RuntimeError, subprocess.TimeoutExpired):
                self.process.terminate()
                try:
                    self.process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
        self._reader.join(timeout=1)
        self.process.stdin.close()
        self.process.stdout.close()
        self._errors.close()


_service = None


def speech_service():
    global _service
    if _service is None or _service.process.poll() is not None:
        if _service is not None:
            _service.close()
        _service = SpeechService()
    return _service


def shutdown_speech():
    global _service
    if _service is not None:
        _service.close()
        _service = None


atexit.register(shutdown_speech)


def start_speech(text, character_id, *, stream=False):
    voice, rate = voice_for(character_id)
    options = {"stream": True} if stream else {}
    return speech_service().request("speak", text=text, voice=voice, rate=rate, **options)


def warmup_speech():
    return speech_service().request("warmup")


def prepare_answers(questions, fallback="elder"):
    items = []
    for question in questions:
        voice, rate = voice_for(question.get("character_id", fallback))
        items.append({"text": question["answer"], "voice": voice, "rate": rate})
    return speech_service().request("prepare", items=items)


def speech_error(process):
    """Lấy thông báo cuối của tiến trình TTS và đóng log tạm."""
    if isinstance(process, SpeechJob):
        return process.message if process.returncode else ""
    errors = getattr(process, "tts_errors", None)
    if errors is None:
        return "Không rõ lỗi ZeroTTS."
    try:
        errors.seek(0)
        lines = errors.read().decode("utf-8", errors="replace").splitlines()
        message = next((line for line in reversed(lines) if line.strip()), "")
        if process.returncode is not None and process.returncode < 0:
            return f"ZeroTTS bị dừng bởi tín hiệu {-process.returncode} (có thể thiếu RAM). {message}".strip()
        return message or f"ZeroTTS thoát mã {process.returncode}; không có thông báo lỗi."
    finally:
        errors.close()


def play_text(text, voice, rate=1.0):
    from .worker import AudioEngine, play_cached
    engine = AudioEngine()
    play_cached(engine.render({"text": text, "voice": voice, "rate": rate}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--voice")
    parser.add_argument("--rate", type=float, default=1.0)
    args = parser.parse_args()
    try:
        if args.worker:
            from contextlib import redirect_stdout
            from .worker import serve
            output = sys.stdout
            with redirect_stdout(sys.stderr):
                serve(sys.stdin, output)
        else:
            if not args.voice:
                parser.error("cần --voice hoặc --worker")
            play_text(sys.stdin.read(), args.voice, args.rate)
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
