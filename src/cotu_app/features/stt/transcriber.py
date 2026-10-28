"""Lazy CPU/int8 Whisper recognition, reused across application jobs."""


class WhisperTranscriber:
    def __init__(self):
        self.model = None
        self.model_name = None

    def transcribe(self, path, model_name="base", check=lambda: None, progress=lambda text: None):
        check()
        if self.model is None or self.model_name != model_name:
            progress("Đang nạp mô hình tiếng Việt; lần đầu cần mạng để tải mô hình...")
            from faster_whisper import WhisperModel
            self.model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=4)
            self.model_name = model_name
        check()
        progress("Đang nhận dạng tiếng Việt. Vẫn có thể đổi thẻ hoặc đóng ứng dụng.")
        segments, _ = self.model.transcribe(str(path), language="vi", beam_size=5,
                                           vad_filter=True, condition_on_previous_text=False)
        output = []
        for segment in segments:
            check()
            if segment.text.strip():
                output.append({"start": segment.start, "text": segment.text.strip()})
        return output
