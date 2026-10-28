"""Select the speaker and supported PortAudio output format."""
import json
import os
import re
from cotu_app.core.paths import CONFIG_DIR

OUTPUT_FILE = CONFIG_DIR / "tts_output.json"

def output_preference():
    """Biến môi trường ghi đè cấu hình chung cho cả hai ứng dụng."""
    override = os.environ.get("NHARONG_TTS_OUTPUT_DEVICE", "").strip()
    if override:
        return override
    if not OUTPUT_FILE.is_file():
        return ""
    data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    value = data.get("output_device") if isinstance(data, dict) else None
    if not isinstance(value, str):
        raise ValueError("tts_output.json cần output_device dạng chuỗi.")
    return value.strip()


class AudioDeviceSelectionError(RuntimeError):
    """Không tìm được duy nhất loa đã chọn trong danh sách PortAudio."""


def _hardware_endpoint(name):
    match = re.search(r"\b(?:plug)?hw:(\d+),(\d+)\b", name, re.I)
    return tuple(map(int, match.groups())) if match else None


def _unique_output(matches, requested, outputs):
    if len(matches) == 1:
        return matches[0][0]
    if len(matches) > 1:
        # Một loa có thể có thêm tên/đường ra ảo. Chọn ngõ phần cứng khi
        # chỉ có một endpoint vật lý; không đoán nếu có hai loa USB thật.
        physical = [(index, item) for index, item in matches
                    if _hardware_endpoint(item["name"]) is not None]
        endpoints = {_hardware_endpoint(item["name"]) for _, item in physical}
        if len(endpoints) == 1:
            return physical[0][0]
        names = "; ".join(f"#{index}: {item['name']}" for index, item in matches)
        raise AudioDeviceSelectionError(
            f"Có nhiều ngõ ra khớp '{requested}': {names}. Chọn loa bằng --set-audio-device.")
    names = "; ".join(f"#{index}: {item['name']}" for index, item in outputs)
    raise AudioDeviceSelectionError(
        f"Không tìm thấy loa '{requested}'. Ngõ ra hiện có: {names or 'không có'}. "
        "Kiểm tra kết nối USB và --check-audio.")


def choose_output_device(sd, requested=None):
    """Chọn ngõ ra đã cấu hình; không tự chuyển sang USB/card khác khi mất loa."""
    devices = sd.query_devices()
    outputs = [(index, item) for index, item in enumerate(devices)
               if item["max_output_channels"] > 0]
    if not outputs:
        raise AudioDeviceSelectionError("Pi không thấy thiết bị phát âm thanh. Kiểm tra loa, HDMI/USB và cấu hình âm thanh.")
    requested = output_preference() if requested is None else str(requested).strip()
    if requested:
        if requested.startswith("alsa-name:"):
            name = requested.removeprefix("alsa-name:").strip().casefold()
            if not name:
                raise ValueError("Cần tên loa sau alsa-name:.")
            matches = [(index, item) for index, item in outputs
                       if name in item["name"].casefold()
                       and _hardware_endpoint(item["name"]) is not None]
            selected = _unique_output(matches, requested, outputs)
        elif requested.startswith("alsa:"):
            card = requested.removeprefix("alsa:")
            if not card.isdecimal():
                raise ValueError("Chọn card ALSA theo dạng alsa:1.")
            matches = [(index, item) for index, item in outputs
                       if re.search(rf"\b(?:plug)?hw:{re.escape(card)},\d+\b", item["name"], re.I)]
            if not matches:
                raise RuntimeError(f"Không thấy loa trên card ALSA {card}; xem --check-audio.")
            selected = matches[0][0]
        elif requested.isdecimal():
            selected = _unique_output([(index, item) for index, item in outputs
                                       if index == int(requested)], requested, outputs)
        else:
            matches = [(index, item) for index, item in outputs
                       if requested.casefold() in item["name"].casefold()]
            exact = [(index, item) for index, item in matches
                     if item["name"].casefold() == requested.casefold()]
            selected = _unique_output(exact or matches, requested, outputs)
    else:
        default = sd.default.device[1]
        selected = default if any(index == default for index, _ in outputs) else outputs[0][0]
    choose_output_format(sd, selected, devices[selected]["max_output_channels"])
    return selected


def choose_output_format(sd, device, max_channels):
    """USB PCM thường nhận int16; thử thêm tần số/kênh tương thích nếu cần."""
    last_error = None
    for channels in (min(2, max_channels), 1):
        for sample_rate, dtype in ((48000, "int16"), (44100, "int16"),
                                   (48000, "float32"), (44100, "float32")):
            try:
                sd.check_output_settings(device=device, samplerate=sample_rate,
                                         channels=channels, dtype=dtype)
                return sample_rate, dtype, channels
            except sd.PortAudioError as error:
                last_error = error
    raise RuntimeError(f"Không mở được thiết bị phát #{device}: {last_error}")


def test_output_tone():
    """Phát một tiếng thử ngắn qua đúng ngõ ra ZeroTTS, không nạp model."""
    import numpy as np
    import sounddevice as sd

    device = choose_output_device(sd)
    sample_rate, dtype, channels = choose_output_format(
        sd, device, sd.query_devices(device)["max_output_channels"])
    times = np.arange(int(sample_rate * 0.8)) / sample_rate
    samples = 0.2 * np.sin(2 * np.pi * 440 * times)
    samples = (samples * 32767).astype(np.int16) if dtype == "int16" else samples.astype(np.float32)
    sd.play(samples, samplerate=sample_rate, device=device,
            mapping=list(range(1, channels + 1)), blocking=True)
    return device, sample_rate, dtype, channels
