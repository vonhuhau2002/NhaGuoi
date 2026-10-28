"""Capture mono WAV using the microphone native sample rate."""
import wave

def record_microphone(device, seconds, path, check=lambda: None, ready=lambda: None):
    import sounddevice as sd

    info = sd.query_devices(device, "input")
    rate = int(info["default_samplerate"])
    count = int(seconds * rate)
    with sd.RawInputStream(device=device, samplerate=rate, channels=1, dtype="int16") as stream:
        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(rate)
            ready()
            while count > 0:
                check()
                frames = min(count, max(1, rate // 10))
                chunk, overflow = stream.read(frames)
                if overflow:
                    raise RuntimeError("Mic bị mất mẫu âm thanh. Hãy thử lại khi Pi ít tải hơn.")
                audio.writeframesraw(bytes(chunk))
                count -= frames
