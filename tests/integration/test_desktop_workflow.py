"""Kiểm tra video/hỏi đáp độc lập màn hình, RFID, mạng và mô hình ASR."""

import multiprocessing as mp
from pathlib import Path
import queue
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch
import wave

from cotu_app.core.errors import Cancelled
from cotu_app.core.settings import CONFIG, load_config
from cotu_app.features.stories.models import Knowledge
from cotu_app.features.stories.answers import UNKNOWN, answer_question
from cotu_app.app.desktop import VideoApp, main
from cotu_app.features.video.content import learn_video, read_transcript, video_digest
from cotu_app.features.stories.questions import load_questions
from cotu_app.core.text import normalize
from cotu_app.features.stt.microphone import record_microphone
from cotu_app.core.files import resolve_path, write_json
from cotu_app.app.media_worker import speech_worker


class VideoKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)
        self.path = self.base / "config.json"
        self.config = load_config(CONFIG)
        self.config.pop("document_questions", None)
        # Không giải mã file này; các kiểm tra dùng ASR giả, không tải mô hình.
        self.video = self.base / "story.mp4"
        self.video.write_bytes(b"test video content one")
        self.config["stories"]["person_1"] = {"video": "story.mp4", "questions": "", "transcript": ""}
        self.asr = Mock(return_value=[{"start": 1.5, "text": "Lan mang nước về cho bà."}])

    def learn(self):
        return learn_video(self.path, self.config, "person_1", self.asr)

    def test_learn_reuses_cache_and_invalidates_when_video_changes(self):
        first = self.learn()
        self.assertEqual(first.segments[0]["start"], 1.5)
        self.assertEqual(self.learn(), first)
        self.asr.assert_called_once_with(self.video)
        self.video.write_bytes(b"different content same filename")
        second = self.learn()
        self.assertNotEqual(first.video_sha256, second.video_sha256)
        self.assertEqual(self.asr.call_count, 2)

    def test_model_change_invalidates_cache(self):
        self.learn()
        self.config["whisper_model"] = "small"
        self.learn()
        self.assertEqual(self.asr.call_count, 2)

    def test_bad_cache_is_rebuilt(self):
        self.learn()
        cache = next((self.base / ".video_cache").glob("*.json"))
        cache.write_text('{"segments": null}', encoding="utf-8")
        self.learn()
        self.assertEqual(self.asr.call_count, 2)

    def test_empty_speech_does_not_create_cache(self):
        self.asr.return_value = []
        with self.assertRaisesRegex(ValueError, "Không nhận được lời thoại"):
            self.learn()
        self.assertFalse((self.base / ".video_cache").exists())

    def test_explicit_transcript_avoids_asr(self):
        (self.base / "story.txt").write_text("Lan mang nước về cho bà.\nBà cảm ơn Lan.", encoding="utf-8")
        self.config["stories"]["person_1"]["transcript"] = "story.txt"
        knowledge = self.learn()
        self.assertEqual(len(knowledge.segments), 2)
        self.assertIsNone(knowledge.segments[0]["start"])
        self.asr.assert_not_called()

    def test_curated_bank_works_without_asr(self):
        write_json(self.base / "bank.json", {
            "video_sha256": video_digest(self.video),
            "questions": [{"question": "Ai mang nước?", "answer": "Lan mang nước.", "aliases": []}],
        })
        self.config["stories"]["person_1"]["questions"] = "bank.json"
        knowledge = self.learn()
        self.assertTrue(answer_question("Ai mang nước?", knowledge).approved)
        self.asr.assert_not_called()

    def test_spawn_worker_loads_curated_video_without_model_or_hardware(self):
        write_json(self.base / "bank.json", {
            "video_sha256": video_digest(self.video),
            "questions": [{"question": "Ai mang nước?", "answer": "Lan mang nước."}],
        })
        self.config["stories"]["person_1"]["questions"] = "bank.json"
        context = mp.get_context("spawn")
        jobs, results, revision = context.Queue(), context.Queue(), context.Value("i", 1)
        worker = context.Process(target=speech_worker, args=(jobs, results, revision))
        try:
            worker.start()
            jobs.put((1, "learn", str(self.path), self.config, "person_1"))
            jobs.put(None)
            self.assertEqual(results.get(timeout=10)[0], "progress")
            kind, epoch, (task, knowledge, error) = results.get(timeout=10)
            self.assertEqual((kind, epoch, task, error), ("done", 1, "learn", None))
            self.assertTrue(answer_question("Ai mang nước?", knowledge).approved)
            worker.join(timeout=5)
            self.assertEqual(worker.exitcode, 0)
        finally:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=2)
            jobs.close()
            results.close()

    def test_wrong_bank_rejected_instead_of_using_other_answers(self):
        write_json(self.base / "bank.json", {"video_sha256": "wrong-video", "questions": []})
        self.config["stories"]["person_1"]["questions"] = "bank.json"
        with self.assertRaisesRegex(ValueError, "SHA256"):
            self.learn()
        self.asr.assert_not_called()

    def test_missing_video_is_actionable(self):
        self.video.unlink()
        with self.assertRaisesRegex(ValueError, "Chọn video"):
            self.learn()

    def test_cancelled_learning_does_not_write_cache(self):
        def transcribe_then_cancel(path):
            raise Cancelled()
        with self.assertRaises(Cancelled):
            learn_video(self.path, self.config, "person_1", transcribe_then_cancel)
        self.assertFalse((self.base / ".video_cache").exists())

    def test_srt_and_utf8_bom(self):
        path = self.base / "story.srt"
        path.write_text("\ufeff1\n00:01:02,500 --> 00:01:04,000\nLan mang nước.\nCho bà.\n\n"
                        "2\n00:02:03,000 --> 00:02:05,000\nBà cảm ơn.\n", encoding="utf-8")
        segments = read_transcript(path)
        self.assertEqual(segments[0], {"start": 62.5, "text": "Lan mang nước. Cho bà."})
        self.assertEqual(segments[1]["start"], 123)
        path.write_text("not an SRT", encoding="utf-8")
        with self.assertRaises(ValueError):
            read_transcript(path)

    def test_duplicate_normalized_aliases_are_rejected(self):
        path = self.base / "bank.json"
        write_json(path, {"video_sha256": "digest", "questions": [
            {"question": "Ai mang nước?", "aliases": ["ai mang nuoc"], "answer": "Lan."}
        ]})
        with self.assertRaisesRegex(ValueError, "trùng"):
            load_questions(path, "digest")

    def test_question_owners_must_be_valid_and_complete(self):
        path = self.base / "bank.json"
        questions = [
            {"question": "Câu một?", "answer": "Đáp một.", "character_id": "elder"},
            {"question": "Câu hai?", "answer": "Đáp hai."},
        ]
        write_json(path, {"video_sha256": "digest", "questions": questions})
        with self.assertRaisesRegex(ValueError, "mọi câu cần character_id"):
            load_questions(path, "digest")
        questions[1]["character_id"] = "unknown"
        write_json(path, {"video_sha256": "digest", "questions": questions})
        with self.assertRaisesRegex(ValueError, "character_id"):
            load_questions(path, "digest")
        questions[1]["character_id"] = ["elder"]
        write_json(path, {"video_sha256": "digest", "questions": questions})
        with self.assertRaisesRegex(ValueError, "character_id"):
            load_questions(path, "digest")

    def test_config_validation_and_relative_paths(self):
        self.assertEqual(resolve_path(self.path, "story.mp4"), self.video)
        for seconds in (True, 0, 100, "8"):
            with self.subTest(seconds=seconds):
                self.config["record_seconds"] = seconds
                write_json(self.path, self.config)
                with self.assertRaises(ValueError):
                    load_config(self.path)


class AnswersTests(unittest.TestCase):
    def setUp(self):
        self.knowledge = Knowledge("digest", [{"start": 62, "text": "Lan mang nước về cho bà."}], [
            {"question": "Ai mang nước về cho bà?", "aliases": ["Người mang nước cho bà là ai?"],
             "answer": "Lan mang nước về cho bà."},
            {"question": "Bà cảm ơn ai?", "answer": "Bà cảm ơn Lan."},
        ], "nhận dạng tự động, cần kiểm tra")

    def test_exact_question_and_explicit_alias_ignore_accents(self):
        self.assertEqual(normalize("ĐƯỜNG?"), "duong")
        for question in ("AI MANG NUOC VE CHO BA!!!", "Người mang nước cho bà là ai?"):
            with self.subTest(question=question):
                result = answer_question(question, self.knowledge)
                self.assertTrue(result.approved)
                self.assertEqual(result.text, "Lan mang nước về cho bà.")

    def test_similar_negated_question_never_gets_automatic_answer(self):
        result = answer_question("Ai không mang nước về cho bà?", self.knowledge)
        self.assertFalse(result.approved)
        self.assertIn("Ai mang nước về cho bà?", result.suggestions)
        self.assertIn(UNKNOWN, result.text)

    def test_unrelated_question_abstains(self):
        result = answer_question("Hà Nội rộng bao nhiêu?", self.knowledge)
        self.assertFalse(result.approved)
        self.assertEqual(result.text, UNKNOWN)

    def test_transcript_is_only_evidence_with_timestamp(self):
        result = answer_question("Lan mang nước gì?", self.knowledge)
        self.assertFalse(result.approved)
        self.assertIn("01:02", result.text)
        self.assertIn("Lời thoại liên quan", result.text)
        self.assertIn("nhận dạng tự động", result.text)

    def test_no_cross_video_knowledge(self):
        other = Knowledge("other", [], [{"question": "Lan đi đâu?", "answer": "Lan về nhà."}], "bộ hỏi đáp")
        self.assertFalse(answer_question("Ai mang nước về cho bà?", other).approved)
        self.assertFalse(answer_question("Ai mang nước về cho bà?", None).approved)
        self.assertFalse(answer_question("...", self.knowledge).approved)

    def test_transcript_only_explains_missing_question_bank(self):
        knowledge = Knowledge("digest", [], [], "nhận dạng tự động")
        result = answer_question("Video nói về gì?", knowledge)
        self.assertFalse(result.approved)
        self.assertIn("chưa có bộ hỏi đáp", result.text)
        self.assertIn("Thiết lập → Bộ hỏi đáp", result.text)


class WorkerAndSessionTests(unittest.TestCase):
    def make_app(self):
        app = VideoApp.__new__(VideoApp)
        app.revision = SimpleNamespace(value=7)
        app.busy = True
        app.knowledge = None
        app.mic_button = Mock()
        app.status = Mock()
        app.audio_status = Mock()
        app.tts_preparation = None
        app.questions = Mock()
        app.question = Mock()
        app.show = Mock()
        app.ask = Mock()
        return app

    def test_stale_mic_result_does_not_answer_after_card_change(self):
        app = self.make_app()
        app.handle_result(("done", 6, ("listen", "old question", None)))
        app.ask.assert_not_called()
        app.question.set.assert_not_called()
        self.assertTrue(app.busy)

    def test_approved_answer_uses_question_owners_tts_voice(self):
        app = self.make_app()
        app.busy = False
        app.cid = "elder"
        app.knowledge = Knowledge("digest", [], [
            {"question": "Vì sao cần bảo tồn?", "answer": "Để gìn giữ.",
             "character_id": "person_3"},
        ], "test")
        app.question.get.return_value = "Vì sao cần bảo tồn?"
        app.pause = Mock()
        app.stop_speech = Mock()
        with patch("cotu_app.app.desktop.start_speech", return_value=Mock()) as speak:
            VideoApp.ask(app)
        speak.assert_called_once_with("Để gìn giữ.", "person_3")
        self.assertIn("Người dệt vải trả lời", app.show.call_args.args[0])

    def test_legacy_answer_uses_selected_character(self):
        app = self.make_app()
        app.busy = False
        app.cid = "elder"
        app.knowledge = Knowledge("digest", [], [{"question": "Nhà Gươl là gì?", "answer": "Nhà chung."}], "test")
        app.question.get.return_value = "Nhà Gươl là gì?"
        app.pause = Mock()
        app.stop_speech = Mock()
        with patch("cotu_app.app.desktop.start_speech", return_value=Mock()) as speak:
            VideoApp.ask(app)
        speak.assert_called_once_with("Nhà chung.", "elder")

    def test_learn_lists_questions_grouped_by_answering_character(self):
        app = self.make_app()
        app.cid = "elder"
        knowledge = Knowledge("digest", [], [
            {"question": "Câu của người dệt?", "answer": "B.", "character_id": "person_3"},
            {"question": "Câu của Già làng?", "answer": "A.", "character_id": "elder"},
        ], "test")
        with patch("cotu_app.app.desktop.prepare_answers") as prepare:
            VideoApp.handle_result(app, ("done", 7, ("learn", knowledge, None)))
        prepare.assert_called_once_with(knowledge.questions, "elder")
        self.assertEqual(app.visible_questions[0]["character_id"], "elder")
        self.assertEqual(app.questions.insert.call_args_list[0].args,
                         ("end", "Già làng • Câu của Già làng?"))
        self.assertEqual(app.questions.insert.call_args_list[1].args,
                         ("end", "Người dệt vải • Câu của người dệt?"))

    def test_stale_knowledge_does_not_replace_new_story(self):
        app = self.make_app()
        app.handle_result(("done", 6, ("learn", Knowledge("old", [], [], "old"), None)))
        self.assertIsNone(app.knowledge)
        app.show.assert_not_called()

    def test_current_recognition_answers_and_reenables_mic(self):
        app = self.make_app()
        app.handle_result(("done", 7, ("listen", "Ai mang nước?", None)))
        app.ask.assert_called_once()
        app.question.set.assert_called_once_with("Ai mang nước?")
        self.assertFalse(app.busy)

    def test_worker_reports_error_without_crashing(self):
        jobs, results = queue.Queue(), queue.Queue()
        revision = SimpleNamespace(value=3)
        jobs.put((3, "learn", "config.json", {}, "person_1"))
        jobs.put(None)
        with patch("cotu_app.app.media_worker.learn_video", side_effect=ValueError("bad video")):
            speech_worker(jobs, results, revision)
        events = [results.get_nowait(), results.get_nowait()]
        self.assertEqual(events[-1], ("done", 3, ("learn", None, "ValueError: bad video")))

    def test_worker_skips_cancelled_queued_job_before_using_devices(self):
        jobs, results = queue.Queue(), queue.Queue()
        jobs.put((2, "listen", "config.json", {}, "person_1"))
        jobs.put(None)
        with patch("cotu_app.app.media_worker.record_microphone") as record:
            speech_worker(jobs, results, SimpleNamespace(value=3))
        record.assert_not_called()
        self.assertTrue(results.empty())

    def test_microphone_uses_device_sample_rate_and_writes_wav(self):
        sd = MagicMock()
        sd.query_devices.return_value = {"default_samplerate": 48000}
        stream = sd.RawInputStream.return_value.__enter__.return_value
        stream.read.side_effect = lambda frames: (b"\x00\x00" * frames, False)
        ready = Mock()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "audio.wav"
            with patch.dict("sys.modules", {"sounddevice": sd}):
                record_microphone(4, 0.2, path, ready=ready)
            with wave.open(str(path)) as sound:
                self.assertEqual(sound.getframerate(), 48000)
                self.assertEqual(sound.getnframes(), 9600)
                self.assertEqual(sound.getnchannels(), 1)
        ready.assert_called_once()
        sd.query_devices.assert_called_once_with(4, "input")

    def test_microphone_overflow_is_reported(self):
        sd = MagicMock()
        sd.query_devices.return_value = {"default_samplerate": 16000}
        sd.RawInputStream.return_value.__enter__.return_value.read.return_value = (b"", True)
        with tempfile.TemporaryDirectory() as folder, patch.dict("sys.modules", {"sounddevice": sd}):
            with self.assertRaisesRegex(RuntimeError, "mất mẫu"):
                record_microphone(None, 0.1, Path(folder) / "audio.wav")

    def test_audio_diagnostics_do_not_start_gui(self):
        process = Mock()
        process.wait.return_value = 0
        with patch("cotu_app.app.desktop.test_output_tone", return_value=(1, 48000, "int16", 2)) as tone, \
                patch("cotu_app.app.desktop.start_speech", return_value=process) as speak, \
                patch("cotu_app.app.desktop.speech_error", return_value="") as errors, \
                patch("cotu_app.app.desktop.initialize_x11") as display, \
                patch("builtins.print"):
            self.assertEqual(main(["--test-audio"]), 0)
            self.assertEqual(main(["--test-tts"]), 0)
        tone.assert_called_once()
        speak.assert_called_once_with("Xin chào, đây là câu trả lời thử của Già làng.", "elder")
        errors.assert_called_once_with(process)
        display.assert_not_called()


if __name__ == "__main__":
    unittest.main()
