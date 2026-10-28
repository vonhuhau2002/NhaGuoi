"""Kiểm tra cache, dùng lại model và ưu tiên/dừng đọc không cần loa thật."""

from pathlib import Path
from fractions import Fraction
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch
import wave

import numpy as np

from cotu_app.features.tts.output import AudioDeviceSelectionError
from cotu_app.features.tts.service import SpeechJob, SpeechService
from cotu_app.features.tts.worker import AudioEngine, AudioWorker, Cancelled, play_cached
from cotu_app.features.tts.streaming import AudioResampler


def write_wav(path, frames=480):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(48000)
        audio.writeframes(b"\0\0" * frames)


class AudioCacheTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.base = Path(folder.name)
        self.model_dir = self.base / "model"
        self.model_dir.mkdir()
        (self.model_dir / "config.json").write_text("{}")
        self.version = patch("cotu_app.features.tts.worker.version", return_value="test")
        self.version.start()
        self.addCleanup(self.version.stop)
        self.engine = AudioEngine(self.model_dir, self.base / "cache")
        self.item = {"text": "Nhà Gươl là nhà chung.", "voice": "huuduc", "rate": 0.88}

    def test_cache_survives_restart_without_loading_model(self):
        path = self.engine.path_for(self.item)
        write_wav(path)
        restarted = AudioEngine(self.model_dir, self.base / "cache")
        with patch.object(restarted, "get_model", side_effect=AssertionError("must not load")):
            self.assertEqual(restarted.render(self.item), path)

    def test_text_voice_rate_and_model_changes_invalidate_cache(self):
        original = self.engine.path_for(self.item)
        for field, value in (("text", "Nội dung đã sửa."), ("voice", "kimoanh"), ("rate", 1.0)):
            self.assertNotEqual(self.engine.path_for({**self.item, field: value}), original)
        (self.model_dir / "config.json").write_text('{"changed":true}')
        changed = AudioEngine(self.model_dir, self.base / "cache")
        self.assertNotEqual(changed.path_for(self.item), original)

    def test_truncated_wav_is_not_treated_as_ready(self):
        path = self.engine.path_for(self.item)
        write_wav(path)
        path.write_bytes(path.read_bytes()[:-10])
        self.assertIsNone(self.engine.cached(self.item))

    def fake_package(self):
        tts = Mock(sample_rate=48000)
        tts.list_voices.return_value = ["huuduc", "kimoanh"]
        def stream(*args, **kwargs):
            yield np.ones((1, 480), dtype=np.float32) * .1
        tts.synthesize_stream.side_effect = stream
        model_class = Mock()
        model_class.from_pretrained.return_value = tts
        package = SimpleNamespace(ZeroTTS=model_class, normalize_vi_text=lambda text: text)
        chunking = SimpleNamespace(chunk_text=lambda text, **k: [text],
                                   clean_segment_punctuation=lambda text: text,
                                   normalize_punctuation=lambda text: text)
        return tts, model_class, {"zerotts": package, "zerotts.chunking": chunking}

    def test_two_voices_load_model_once_and_write_valid_wavs(self):
        tts, model_class, modules = self.fake_package()
        with patch.dict("sys.modules", modules):
            first = self.engine.render(self.item)
            second = self.engine.render({**self.item, "voice": "kimoanh"})
            self.engine.render(self.item)
        model_class.from_pretrained.assert_called_once()
        self.assertEqual(tts.synthesize_stream.call_count, 2)
        self.assertNotEqual(first, second)
        with wave.open(str(first), "rb") as audio:
            self.assertGreater(audio.getnframes(), 0)

    def test_cancelled_synthesis_never_commits_partial_audio(self):
        tts, _, modules = self.fake_package()
        cancelled = threading.Event()

        def stream(*args, **kwargs):
            cancelled.set()
            yield np.ones((1, 480), dtype=np.float32)

        tts.synthesize_stream.side_effect = stream
        with patch.dict("sys.modules", modules), self.assertRaises(Cancelled):
            self.engine.render(self.item, cancelled.is_set)
        self.assertIsNone(self.engine.cached(self.item))
        self.assertFalse(list((self.base / "cache").glob("*.tmp")))

    def test_stream_delivers_audio_before_synthesis_finishes_and_commits_same_pcm(self):
        tts, _, modules = self.fake_package()
        delivered = []

        def stream(*args, **kwargs):
            yield np.ones((1, 4800), dtype=np.float32) * .1
            self.assertTrue(delivered, "first audio must not wait for the tail")
            self.assertIsNone(self.engine.cached(self.item), "partial answer must not be cached")
            yield np.ones((1, 4800), dtype=np.float32) * .2

        tts.synthesize_stream.side_effect = stream
        with patch.dict("sys.modules", modules):
            path = self.engine.render(self.item, on_audio=delivered.append)
        with wave.open(str(path), "rb") as audio:
            cached = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
        np.testing.assert_array_equal(cached, np.concatenate(delivered))
        self.assertEqual(tts.synthesize_stream.call_args.kwargs["first_chunk_frames"], 2)

    def test_cancel_after_first_stream_chunk_does_not_publish_partial_wav(self):
        tts, _, modules = self.fake_package()
        cancelled = threading.Event()
        def stream(*args, **kwargs):
            yield np.ones((1, 4800), dtype=np.float32) * .1
            yield np.ones((1, 4800), dtype=np.float32) * .2
        tts.synthesize_stream.side_effect = stream
        with patch.dict("sys.modules", modules), self.assertRaises(Cancelled):
            self.engine.render(self.item, cancelled.is_set, on_audio=lambda audio: cancelled.set())
        self.assertIsNone(self.engine.cached(self.item))


class StreamingResamplerTests(unittest.TestCase):
    def test_chunks_match_whole_wave_without_clicks_missing_or_repeated_samples(self):
        from scipy.signal import resample_poly
        samples = np.random.default_rng(7).normal(0, .1, 50003).astype(np.float32)
        for ratio in (Fraction(25, 22), Fraction(20, 19), Fraction(147, 160), Fraction(1)):
            with self.subTest(ratio=ratio):
                converter = AudioResampler(ratio)
                parts = []
                for start in range(0, len(samples), 317):
                    parts.append(converter.push(samples[start:start + 317]))
                    if converter.buffer is not None:
                        self.assertLess(len(converter.buffer), 1000)
                parts.append(converter.push([], final=True))
                expected = resample_poly(samples, ratio.numerator, ratio.denominator)
                np.testing.assert_allclose(np.concatenate(parts), expected, atol=1e-7)

    def test_very_short_chunks_and_tail_are_not_lost(self):
        from scipy.signal import resample_poly
        samples = np.arange(71, dtype=np.float32)
        converter = AudioResampler(Fraction(25, 22))
        parts = [converter.push([sample]) for sample in samples]
        parts.append(converter.push([], final=True))
        np.testing.assert_allclose(np.concatenate(parts), resample_poly(samples, 25, 22), atol=1e-5)


class WorkerSchedulingTests(unittest.TestCase):
    def make_worker(self, engine, player):
        self.events = []
        worker = AudioWorker(engine, self.events.append, player)
        worker.start()
        self.addCleanup(worker.close)
        return worker

    def wait_for(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate():
            if time.monotonic() > deadline:
                self.fail("worker timeout")
            threading.Event().wait(.01)

    def test_cached_answer_plays_while_model_thread_is_busy(self):
        engine = Mock()
        engine.path_for.side_effect = lambda item: item["text"]
        engine.cached.side_effect = lambda item: Path("ready.wav") if item["text"] == "cached" else None
        busy, release, played = threading.Event(), threading.Event(), threading.Event()

        def render(item, cancelled, progress):
            busy.set()
            release.wait(3)
            return Path("background.wav")

        engine.render.side_effect = render
        worker = self.make_worker(engine, lambda path, cancelled: played.set())
        self.addCleanup(release.set)
        worker.submit({"kind": "prepare", "id": 1, "items": [{"text": "background"}]})
        self.assertTrue(busy.wait(1))
        worker.submit({"kind": "speak", "id": 2, "text": "cached"})
        self.assertTrue(played.wait(1))
        self.assertFalse(release.is_set())

    def test_new_question_preempts_background_and_old_speech_is_cancelled(self):
        engine = Mock()
        engine.cached.return_value = None
        engine.path_for.side_effect = lambda item: item["text"]
        background_started = threading.Event()
        order, players = [], []
        player_started = threading.Event()

        def render(item, cancelled, progress):
            if item["text"] == "background" and not order:
                background_started.set()
                self.wait_for(cancelled)
                raise Cancelled()
            if cancelled():
                raise Cancelled()
            order.append(item["text"])
            return Path(item["text"])

        def player(path, cancelled):
            players.append(str(path))
            player_started.set()
            if str(path) == "first":
                self.wait_for(cancelled)
                raise Cancelled()

        engine.render.side_effect = render
        worker = self.make_worker(engine, player)
        worker.submit({"kind": "prepare", "id": 1, "items": [{"text": "background"}]})
        self.assertTrue(background_started.wait(1))
        worker.submit({"kind": "speak", "id": 2, "text": "first"})
        self.assertTrue(player_started.wait(1))
        worker.submit({"kind": "speak", "id": 3, "text": "second"})
        self.wait_for(lambda: any(e.get("id") == 3 and e.get("code") == 0 for e in self.events))
        self.assertEqual(order[0], "first")
        self.assertEqual(players, ["first", "second"])
        self.assertTrue(any(e.get("id") == 2 and e.get("code") == -15 for e in self.events))

    def test_playback_error_is_reported_to_ui(self):
        engine = Mock()
        engine.cached.return_value = Path("ready.wav")
        worker = self.make_worker(engine, Mock(side_effect=RuntimeError("USB missing")))
        worker.submit({"kind": "speak", "id": 5, "text": "cached"})
        self.wait_for(lambda: any(e.get("code") == 1 for e in self.events))
        self.assertIn("USB missing", self.events[-1]["message"])

    def test_speech_waits_for_complete_wav_even_for_legacy_stream_request(self):
        engine = Mock()
        engine.cached.return_value = None
        released, started, played = threading.Event(), threading.Event(), threading.Event()
        order = []
        def render(item, cancelled, progress):
            started.set()
            released.wait(3)
            order.append("complete")
            return Path("complete.wav")
        def player(source, cancelled):
            self.assertEqual(source, Path("complete.wav"))
            order.append("play")
            played.set()
        engine.render.side_effect = render
        self.addCleanup(released.set)
        worker = self.make_worker(engine, player)
        worker.submit({"kind": "speak", "id": 1, "text": "new answer", "stream": True})
        self.assertTrue(started.wait(1))
        self.assertFalse(played.wait(.05), "must not play a few words and then wait for synthesis")
        self.assertFalse(any("code" in event for event in self.events))
        released.set()
        self.wait_for(lambda: any(event.get("code") == 0 for event in self.events))
        self.assertEqual(order, ["complete", "play"])

    def test_new_question_cancels_old_synthesis_before_speaker_is_opened(self):
        engine = Mock()
        engine.cached.return_value = None
        started = threading.Event()
        def render(item, cancelled, progress):
            if item["text"] == "old":
                started.set()
                self.wait_for(cancelled)
                raise Cancelled()
            return Path("new.wav")
        engine.render.side_effect = render
        player = Mock()
        worker = self.make_worker(engine, player)
        worker.submit({"kind": "speak", "id": 1, "text": "old", "stream": True})
        self.assertTrue(started.wait(1))
        worker.submit({"kind": "speak", "id": 2, "text": "new", "stream": True})
        self.wait_for(lambda: any(event.get("id") == 2 and event.get("code") == 0 for event in self.events))
        player.assert_called_once()
        self.assertEqual(player.call_args.args[0], Path("new.wav"))
        self.assertTrue(any(event.get("id") == 1 and event.get("code") == -15 for event in self.events))

    def test_synthesis_error_is_reported_without_playing_a_partial_answer(self):
        engine = Mock()
        engine.cached.return_value = None
        engine.render.side_effect = ValueError("synthesis failed")
        player = Mock()
        worker = self.make_worker(engine, player)
        worker.submit({"kind": "speak", "id": 1, "text": "new", "stream": True})
        self.wait_for(lambda: any(event.get("code") == 1 for event in self.events))
        self.assertIn("synthesis failed", self.events[-1]["message"])
        player.assert_not_called()


class SpeechHandleTests(unittest.TestCase):
    def test_entire_wav_is_loaded_before_speaker_starts(self):
        from contextlib import contextmanager
        sd = MagicMock()
        sd.query_devices.return_value = {"max_output_channels": 2}
        loaded = threading.Event()
        original_open = wave.open
        @contextmanager
        def open_audio(*args, **kwargs):
            with original_open(*args, **kwargs) as audio:
                yield audio
            loaded.set()
        def output_stream(**kwargs):
            self.assertTrue(loaded.is_set(), "speaker must not wait for WAV reads")
            self.assertEqual(kwargs["latency"], "high")
            return MagicMock()
        sd.OutputStream.side_effect = output_stream
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "complete.wav"
            write_wav(path, 9600)
            with patch.dict("sys.modules", {"sounddevice": sd}), \
                    patch("cotu_app.features.tts.worker.wave.open", side_effect=open_audio), \
                    patch("cotu_app.features.tts.worker.choose_output_device", return_value=1), \
                    patch("cotu_app.features.tts.worker.choose_output_format", return_value=(48000, "int16", 2)):
                play_cached(path)
        sd.OutputStream.assert_called_once()

    def test_warmup_is_deduplicated_while_loading_and_after_model_is_ready(self):
        service = SpeechService.__new__(SpeechService)
        service.sequence, service.jobs, service.preparation = 0, {}, None
        service.send = Mock()
        first = service.request("warmup")
        self.assertIs(service.request("warmup"), first)
        first.finish(0, "ready")
        self.assertIs(service.request("warmup"), first)
        service.send.assert_called_once()

    def test_cancel_stops_request_without_terminating_model_process(self):
        service = Mock()
        job = SpeechJob(service, 12)
        job.terminate()
        self.assertEqual(job.wait(.1), -15)
        service.send.assert_called_once_with({"kind": "cancel", "id": 12})
        service.process.terminate.assert_not_called()

    def test_same_preparation_is_not_queued_again(self):
        service = SpeechService.__new__(SpeechService)
        service.sequence, service.jobs, service.preparation = 0, {}, None
        service.send = Mock()
        data = {"items": [{"text": "answer", "voice": "huuduc", "rate": .88}]}
        first = service.request("prepare", **data)
        first.finish(0, "done")
        self.assertIs(service.request("prepare", **data), first)
        service.send.assert_called_once()

    def test_playback_stops_on_cancel_and_uses_selected_usb(self):
        sd = MagicMock()
        sd.query_devices.return_value = {"max_output_channels": 2}
        stream = sd.OutputStream.return_value.__enter__.return_value
        cancelled = threading.Event()
        stream.write.side_effect = lambda samples: cancelled.set()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sound.wav"
            write_wav(path, 48000)
            with patch.dict("sys.modules", {"sounddevice": sd}), \
                    patch("cotu_app.features.tts.worker.choose_output_device", return_value=1), \
                    patch("cotu_app.features.tts.worker.choose_output_format", return_value=(48000, "int16", 2)), \
                    self.assertRaises(Cancelled):
                play_cached(path, cancelled.is_set)
        self.assertEqual(sd.OutputStream.call_args.kwargs["device"], 1)
        stream.abort.assert_called_once()
        stream.write.assert_called_once()

    def test_usb_hotplug_refreshes_portaudio_without_loading_model(self):
        sd = MagicMock()
        sd.query_devices.return_value = {"max_output_channels": 2}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sound.wav"
            write_wav(path)
            with patch.dict("sys.modules", {"sounddevice": sd}), \
                    patch("cotu_app.features.tts.worker.choose_output_device",
                          side_effect=[AudioDeviceSelectionError("USB absent"), 1]) as choose, \
                    patch("cotu_app.features.tts.worker.choose_output_format", return_value=(48000, "int16", 2)), \
                    patch.object(AudioEngine, "get_model", side_effect=AssertionError("no model load")):
                play_cached(path)
        self.assertEqual(choose.call_count, 2)
        sd._terminate.assert_called_once()
        sd._initialize.assert_called_once()
        self.assertEqual(sd.OutputStream.call_args.kwargs["device"], 1)


if __name__ == "__main__":
    unittest.main()
