"""Keep recognition lazy, reusable and cancellable without loading a model."""

import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from cotu_app.core.errors import Cancelled
from cotu_app.features.stt.transcriber import WhisperTranscriber


class TranscriberTests(unittest.TestCase):
    def setUp(self):
        self.factory = Mock()
        self.factory.return_value.transcribe.side_effect = lambda *a, **k: (
            iter([SimpleNamespace(start=1.5, text=" Xin chào. ")]), None)
        self.module = patch.dict(sys.modules, {"faster_whisper": SimpleNamespace(WhisperModel=self.factory)})
        self.module.start()
        self.addCleanup(self.module.stop)

    def test_reuses_same_model_across_video_and_microphone_requests(self):
        recognizer = WhisperTranscriber()
        self.factory.assert_not_called()
        for filename in ("video.mp4", "microphone.wav"):
            self.assertEqual(recognizer.transcribe(filename), [{"start": 1.5, "text": "Xin chào."}])
        self.factory.assert_called_once_with("base", device="cpu", compute_type="int8", cpu_threads=4)
        self.assertEqual(self.factory.return_value.transcribe.call_count, 2)

    def test_switching_configured_model_reloads_it(self):
        recognizer = WhisperTranscriber()
        recognizer.transcribe("one.wav", "base")
        recognizer.transcribe("two.wav", "small")
        self.assertEqual([call.args[0] for call in self.factory.call_args_list], ["base", "small"])

    def test_cancelled_job_does_not_load_model(self):
        with self.assertRaises(Cancelled):
            WhisperTranscriber().transcribe("one.wav", check=Mock(side_effect=Cancelled))
        self.factory.assert_not_called()

    def test_cancellation_during_segment_iteration_discards_old_result(self):
        checks = Mock(side_effect=[None, None, Cancelled()])
        with self.assertRaises(Cancelled):
            WhisperTranscriber().transcribe("one.wav", check=checks)
