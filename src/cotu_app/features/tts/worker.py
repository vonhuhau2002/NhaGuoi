"""Model giữ trong RAM; WAV lưu bền vững, tác vụ đọc ưu tiên hơn tạo sẵn."""

from fractions import Fraction
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import queue
import tempfile
import threading
import wave
from .streaming import AudioResampler, Cancelled

from cotu_app.core.paths import MODEL_DIR, TTS_CACHE_DIR
from .output import AudioDeviceSelectionError, choose_output_device, choose_output_format

CACHE_DIR = TTS_CACHE_DIR
CACHE_VERSION = 1


class AudioEngine:
    def __init__(self, model_dir=MODEL_DIR, cache_dir=CACHE_DIR):
        self.model_dir, self.cache_dir = Path(model_dir), Path(cache_dir)
        self.model = None
        # Không đọc hàng GB trọng số mỗi câu. Đổi model/voice pack tự đổi khóa.
        manifest = [(str(path.relative_to(self.model_dir)), path.stat().st_size,
                     path.stat().st_mtime_ns)
                    for path in sorted(self.model_dir.rglob("*")) if path.is_file()]
        self.fingerprint = hashlib.sha256(json.dumps(
            [CACHE_VERSION, version("zerotts"), manifest]).encode()).hexdigest()

    def path_for(self, item):
        key = json.dumps([self.fingerprint, item["text"], item["voice"],
                          float(item["rate"])], ensure_ascii=False)
        return self.cache_dir / (hashlib.sha256(key.encode()).hexdigest() + ".wav")

    def cached(self, item):
        path = self.path_for(item)
        try:
            with wave.open(str(path), "rb") as audio:
                valid = (audio.getnchannels() == 1 and audio.getsampwidth() == 2
                         and audio.getframerate() == 48000 and audio.getnframes() > 0
                         and path.stat().st_size >= 44 + audio.getnframes() * 2)
            return path if valid else None
        except (OSError, EOFError, wave.Error):
            return None

    def get_model(self, progress):
        if self.model is None:
            progress("Đang chuẩn bị giọng đọc lần đầu...")
            from zerotts import ZeroTTS
            self.model = ZeroTTS.from_pretrained(
                self.model_dir, local_files_only=True, warmup=False,
                # A single inference thread leaves CPU room for audio/UI.
                # On this Pi it also outperformed the 4-thread benchmark.
                intra_op_num_threads=1,
            )
        return self.model

    def render(self, item, cancelled=lambda: False, progress=lambda message: None, *, on_audio=None):
        def check():
            if cancelled():
                raise Cancelled()

        check()
        cached = self.cached(item)
        if cached:
            return cached
        import numpy as np
        from scipy.signal import resample_poly
        from zerotts import normalize_vi_text
        from zerotts.chunking import chunk_text, clean_segment_punctuation, normalize_punctuation

        tts = self.get_model(progress)
        check()
        if item["voice"] not in tts.list_voices():
            raise ValueError(f"Giọng ZeroTTS không tồn tại: {item['voice']}")
        normalized = normalize_punctuation(normalize_vi_text(item["text"]))
        segments = [clean_segment_punctuation(part)
                    for part in chunk_text(normalized, max_chunk_sec=10)]
        parts = []
        ratio = Fraction(48000, tts.sample_rate) / Fraction(item["rate"]).limit_denominator(1000)
        resampler = AudioResampler(ratio) if on_audio is not None else None

        def deliver(samples, *, final=False):
            samples = resampler.push(samples, final=final)
            if samples.size:
                pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
                parts.append(pcm)
                on_audio(pcm)

        progress("Đang tạo âm thanh câu trả lời...")
        for segment in segments:
            check()
            if not segment:
                continue
            # API stream cho phép nhường việc tạo nền khi có câu hỏi mới.
            stream = tts.synthesize_stream(segment, voice=item["voice"],
                                           first_chunk_frames=2 if on_audio is not None else 8,
                                           max_chunk_frames=8)
            try:
                for audio in stream:
                    check()
                    if on_audio is not None:
                        deliver(audio)
                    else:
                        parts.append(audio.reshape(-1))
            finally:
                stream.close()
        check()
        if on_audio is not None:
            deliver(np.empty(0, dtype=np.float32), final=True)
        if not parts or not any(part.size for part in parts):
            raise RuntimeError("ZeroTTS không tạo được mẫu âm thanh nào.")
        samples = np.concatenate(parts)
        if on_audio is None:
            if ratio != 1:
                samples = resample_poly(samples, ratio.numerator, ratio.denominator)
            samples = (np.clip(samples, -1, 1) * 32767).astype("<i2")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Chỉ công bố WAV đã hoàn tất; dừng ứng dụng không để lại cache nửa chừng.
        descriptor, temporary = tempfile.mkstemp(suffix=".tmp", dir=self.cache_dir)
        try:
            with os.fdopen(descriptor, "wb") as target:
                with wave.open(target, "wb") as audio:
                    audio.setnchannels(1)
                    audio.setsampwidth(2)
                    audio.setframerate(48000)
                    audio.writeframes(samples.tobytes())
            check()
            path = self.path_for(item)
            os.replace(temporary, path)
            return path
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def play_cached(path, cancelled=lambda: False):
    """Prepare the complete waveform before opening the speaker."""
    import numpy as np
    import sounddevice as sd

    if cancelled():
        raise Cancelled()
    try:
        device = choose_output_device(sd)
    except AudioDeviceSelectionError:
        # PortAudio giữ danh sách từ lúc import. TTS sống lâu cần làm mới
        # khi USB vừa cắm/rút. Chỉ luồng phát dùng sounddevice trong tiến
        # trình này, và lượt phát trước đã đóng stream, nên có thể khởi
        # tạo lại PortAudio an toàn mà không đụng model hay Whisper.
        sd._terminate()
        sd._initialize()
        device = choose_output_device(sd)
    rate, dtype, channels = choose_output_format(
        sd, device, sd.query_devices(device)["max_output_channels"])
    with wave.open(str(path), "rb") as audio:
        source_rate = audio.getframerate()
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
    if rate != source_rate:
        # Cached WAVs already use the USB speaker's 48 kHz format. Import
        # SciPy only for devices that actually require resampling; its cold
        # import on the SD card must not delay the first cached answer.
        from scipy.signal import resample_poly
        ratio = Fraction(rate, source_rate)
        samples = resample_poly(samples.astype(np.float32), ratio.numerator, ratio.denominator)
    if dtype == "float32":
        samples = samples.astype(np.float32) / 32768
    else:
        samples = np.clip(samples, -32768, 32767).astype(np.int16)
    samples = np.repeat(samples[:, None], channels, axis=1)
    if cancelled():
        raise Cancelled()
    block = max(1, int(rate * 0.04))
    with sd.OutputStream(device=device, samplerate=rate, channels=channels,
                         dtype=dtype, blocksize=0, latency="high") as output:
        for offset in range(0, len(samples), block):
            if cancelled():
                output.abort()
                raise Cancelled()
            output.write(samples[offset:offset + block])


class AudioWorker:
    def __init__(self, engine, emit, player=play_cached):
        self.engine, self.emit, self.player = engine, emit, player
        self.jobs = {}
        self.lock = threading.RLock()
        self.pending_speech = set()
        self.current_speech = None
        self.tasks = queue.PriorityQueue()
        self.playback = queue.Queue()
        self.sequence = 0
        self.stopped = threading.Event()
        self.threads = [threading.Thread(target=target, daemon=True)
                        for target in (self.synthesize, self.play)]

    def start(self):
        for thread in self.threads:
            thread.start()

    def report(self, job, message, **extra):
        with self.lock:
            if not job["cancel"].is_set():
                self.emit({"id": job["id"], "message": message, **extra})

    def finish(self, job, code, message):
        with self.lock:
            if self.jobs.pop(job["id"], None) is not None:
                self.emit({"id": job["id"], "code": code, "message": message})

    def enqueue(self, priority, job, item):
        self.sequence += 1
        self.tasks.put((priority, self.sequence, job, item))

    def submit(self, command):
        with self.lock:
            kind = command["kind"]
            if kind == "cancel":
                job = self.jobs.get(command["id"])
                if job:
                    job["cancel"].set()
                    self.finish(job, -15, "Đã dừng.")
                return
            job = {**command, "cancel": threading.Event(), "completed": 0}
            self.jobs[job["id"]] = job
            if kind == "speak":
                if self.current_speech is not None:
                    self.current_speech["cancel"].set()
                    self.finish(self.current_speech, -15, "Đã dừng giọng cũ.")
                self.current_speech = job
                cached = self.engine.cached(command)
                if cached:
                    self.playback.put((job, cached))
                else:
                    self.pending_speech.add(job["id"])
                    self.enqueue(0, job, command)
            elif kind == "prepare":
                # Chỉ xếp một câu mỗi lượt để ưu tiên câu hỏi mới.
                job["items"] = list({self.engine.path_for(item): item
                                     for item in command["items"]}.values())
                job["total"] = len(job["items"])
                if job["total"]:
                    self.enqueue(10, job, job["items"][0])
                    self.report(job, "Đang chuẩn bị âm thanh câu trả lời...",
                                completed=0, total=job["total"])
                else:
                    self.finish(job, 0, "Không có câu trả lời cần chuẩn bị.")
            elif kind == "warmup":
                self.enqueue(5, job, None)

    def synthesize(self):
        while not self.stopped.is_set():
            try:
                priority, _, job, item = self.tasks.get(timeout=0.1)
            except queue.Empty:
                continue
            background = job["kind"] == "prepare"

            def cancelled():
                return (self.stopped.is_set() or job["cancel"].is_set()
                        or (background and bool(self.pending_speech)))

            try:
                if job["kind"] == "warmup":
                    if not cancelled():
                        self.engine.get_model(lambda message: self.report(job, message)).warmup()
                        self.finish(job, 0, "Giọng đọc đã sẵn sàng.")
                    continue
                # This Pi generates speech slower than the speaker consumes it.
                # Even legacy stream requests must wait for a complete WAV;
                # otherwise each tiny chunk is followed by a synthesis gap.
                path = self.engine.render(item, cancelled,
                                          lambda message: self.report(job, message))
                if background:
                    with self.lock:
                        job["completed"] += 1
                        self.report(job, f"Âm thanh sẵn sàng {job['completed']}/{job['total']}.",
                                    completed=job["completed"], total=job["total"])
                        if job["completed"] == job["total"]:
                            self.finish(job, 0, f"Đã chuẩn bị đủ {job['total']} câu trả lời.")
                        elif not job["cancel"].is_set():
                            self.enqueue(10, job, job["items"][job["completed"]])
                elif not cancelled():
                    self.playback.put((job, path))
            except Cancelled:
                if background and not job["cancel"].is_set() and not self.stopped.is_set():
                    with self.lock:
                        self.enqueue(priority, job, item)
            except Exception as error:
                self.finish(job, 1, f"{type(error).__name__}: {error}")
            finally:
                if not background:
                    with self.lock:
                        self.pending_speech.discard(job["id"])

    def play(self):
        while not self.stopped.is_set():
            try:
                job, path = self.playback.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self.report(job, "Đang đọc câu trả lời...")
                self.player(path, lambda: job["cancel"].is_set() or self.stopped.is_set())
                self.finish(job, 0, "Đã đọc xong.")
            except Cancelled:
                self.finish(job, -15, "Đã dừng giọng đọc.")
            except Exception as error:
                job["cancel"].set()
                self.finish(job, 1, f"Phát âm thanh: {error}")

    def close(self):
        self.stopped.set()
        with self.lock:
            for job in self.jobs.values():
                job["cancel"].set()
        for thread in self.threads:
            thread.join(timeout=0.2)


def serve(source, output):
    output_lock = threading.Lock()

    def emit(event):
        with output_lock:
            output.write(json.dumps(event, ensure_ascii=False) + "\n")
            output.flush()

    worker = AudioWorker(AudioEngine(), emit)
    worker.start()
    try:
        for line in source:
            command = json.loads(line)
            if command["kind"] == "shutdown":
                break
            worker.submit(command)
    finally:
        worker.close()
