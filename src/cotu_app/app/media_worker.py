"""Background orchestration: video content loading and spoken questions."""
from pathlib import Path
import tempfile
from cotu_app.core.errors import Cancelled
from cotu_app.features.stt.microphone import record_microphone
from cotu_app.features.stt.transcriber import WhisperTranscriber
from cotu_app.features.video.content import learn_video

def speech_worker(jobs, results, revision):
    """Một tiến trình giữ ASR; không đụng Tkinter, bỏ kết quả khi đổi thẻ."""
    recognizer = WhisperTranscriber()
    while True:
        job = jobs.get()
        if job is None:
            return
        epoch, kind, config_path, config, story_id = job

        def check():
            if revision.value != epoch:
                raise Cancelled()

        def progress(message):
            check()
            results.put(("progress", epoch, message))

        def transcribe(path):
            return recognizer.transcribe(path, config.get("whisper_model", "base"), check, progress)

        try:
            check()
            if kind == "learn":
                progress("Đang nạp nội dung của đúng video...")
                value = learn_video(config_path, config, story_id, transcribe, check)
            else:
                with tempfile.TemporaryDirectory(prefix="nharong-mic-") as folder:
                    path = Path(folder) / "question.wav"
                    seconds = config.get("record_seconds", 8)
                    record_microphone(config.get("microphone"), seconds, path, check,
                                      lambda: progress(f"MIC ĐANG THU — hãy hỏi trong {seconds:g} giây."))
                    value = " ".join(segment["text"] for segment in transcribe(path))
            check()
            results.put(("done", epoch, (kind, value, None)))
        except Cancelled:
            continue
        except Exception as error:
            results.put(("done", epoch, (kind, None, f"{type(error).__name__}: {error}")))
