"""Bám nguyên văn nguồn TXT; tài liệu bổ sung không thành lời thoại video."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from cotu_app.core.paths import BASE
from cotu_app.core.settings import CONFIG, load_config
from cotu_app.features.stories.models import Knowledge
from cotu_app.app.desktop import VideoApp
from cotu_app.features.stories.answers import answer_question
from cotu_app.features.video.content import learn_video
from cotu_app.features.stories.questions import load_document_questions, load_story_questions, parse_numbered_questions
from cotu_app.core.text import question_key
from cotu_app.core.files import write_json


class DocumentQuestionsTests(unittest.TestCase):
    def setUp(self):
        self.bank = BASE / "data/stories/co_tu_story.questions.json"
        self.source = BASE / "data/stories/Text cau chuyen co tu.txt"
        self.questions = load_document_questions(self.bank)

    def test_all_five_questions_and_29_aliases_keep_original_answers_and_elder_voice(self):
        original = parse_numbered_questions(self.source.read_text(encoding="utf-8-sig"))
        self.assertEqual(len(self.questions), 5)
        self.assertEqual(sum(len(item["aliases"]) for item in self.questions), 29)
        knowledge = Knowledge("video", [], self.questions, "tài liệu")
        for item in self.questions:
            number = item["source_question"]
            self.assertEqual((item["question"], item["answer"]), original[number])
            self.assertNotIn("source_start", item)
            for wording in [item["question"], *item["aliases"]]:
                answer = answer_question(wording, knowledge)
                self.assertTrue(answer.approved, wording)
                self.assertEqual(answer.character_id, "elder")
                self.assertEqual(answer.text, original[number][1])
                self.assertEqual(answer.source, f"{self.source.name} — Câu {number}")

    def test_new_and_old_question_variants_never_collide_after_normalization(self):
        knowledge = learn_video(CONFIG, load_config(CONFIG), "elder", Mock(side_effect=AssertionError("ASR")))
        self.assertEqual(len(knowledge.questions), 37)
        seen = {}
        for index, item in enumerate(knowledge.questions):
            for wording in [item["question"], *item.get("aliases", [])]:
                key = question_key(wording)
                self.assertEqual(seen.get(key, index), index, wording)
                seen[key] = index
        for wording in ("Nói lý hát lý là gì?", "Nguồn gốc người Cơ Tu theo thần thoại là gì?",
                        "Vì sao người Cơ Tu nói mất Gươl là mất làng?"):
            answer = answer_question(wording, knowledge)
            self.assertTrue(answer.approved)
            self.assertIn(self.source.name, answer.source)

    def test_unknown_specifics_are_not_invented_from_document(self):
        knowledge = Knowledge("video", [], self.questions, "tài liệu")
        for wording in ("Giàng sinh ra năm nào?", "Người Cơ Tu không sinh ra từ quả bầu phải không?",
                        "Cột xnur chính xác cao bao nhiêu mét?"):
            self.assertFalse(answer_question(wording, knowledge).approved)

    def test_hash_mismatch_and_modified_answer_are_rejected(self):
        data = json.loads(self.bank.read_text())
        with tempfile.TemporaryDirectory() as folder:
            bank = Path(folder) / "bank.json"
            data["source_file"] = str(self.source)
            data["source_sha256"] = "0" * 64
            write_json(bank, data)
            with self.assertRaisesRegex(ValueError, "SHA256"):
                load_document_questions(bank)
            data["source_sha256"] = hashlib.sha256(self.source.read_bytes()).hexdigest()
            data["questions"][0]["answer"] = "Nội dung tự thêm, không có trong tài liệu."
            write_json(bank, data)
            with self.assertRaisesRegex(ValueError, "nguyên văn"):
                load_document_questions(bank)

    def test_missing_question_is_reported_instead_of_silently_dropping_content(self):
        data = json.loads(self.bank.read_text())
        data["source_file"] = str(self.source)
        data["questions"].pop()
        with tempfile.TemporaryDirectory() as folder:
            bank = Path(folder) / "bank.json"
            write_json(bank, data)
            with self.assertRaisesRegex(ValueError, "đủ các câu"):
                load_document_questions(bank)

    def test_parser_accepts_adjacent_headers_and_rejects_empty_or_duplicate_answers(self):
        parsed = parse_numbered_questions("Câu 1: Một?\n\nĐáp một.\nCâu 2: Hai?\nĐáp hai.")
        self.assertEqual(parsed, {1: ("Một?", "Đáp một."), 2: ("Hai?", "Đáp hai.")})
        for text in ("Không có câu hỏi", "Câu 1: Một?", "Câu 1: Một?\nĐáp.\nCâu 1: Hai?\nĐáp."):
            with self.assertRaises(ValueError):
                parse_numbered_questions(text)

    def test_config_rejects_invalid_document_paths(self):
        config = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            for invalid in (None, "docs/file.json", [None], [""]):
                config["document_questions"] = invalid
                write_json(path, config)
                with self.assertRaisesRegex(ValueError, "document_questions"):
                    load_config(path)

    def test_legacy_video_bank_without_character_keeps_selected_speaker(self):
        config = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            bank = Path(folder) / "video.json"
            write_json(bank, {"video_sha256": "digest", "questions": [
                {"question": "Câu cũ?", "answer": "Đáp cũ."},
            ]})
            config["stories"]["person_2"]["questions"] = str(bank)
            config["document_questions"] = [str(self.bank)]
            loaded = load_story_questions(path, config, "person_2", "digest")
        knowledge = Knowledge("digest", [], loaded, "test")
        self.assertEqual(answer_question("Câu cũ?", knowledge).character_id, "person_2")
        self.assertEqual(answer_question("Nói lý hát lý là gì?", knowledge).character_id, "elder")

    def test_ui_shows_document_source_but_only_speaks_original_answer(self):
        item = self.questions[0]
        app = VideoApp.__new__(VideoApp)
        app.busy, app.cid = False, "person_3"
        app.knowledge = Knowledge("video", [], self.questions, "tài liệu")
        app.question = Mock()
        app.question.get.return_value = item["aliases"][0]
        app.pause, app.stop_speech, app.show, app.status = Mock(), Mock(), Mock(), Mock()
        with patch("cotu_app.app.desktop.start_speech") as speak:
            VideoApp.ask(app)
        speak.assert_called_once_with(item["answer"], "elder")
        self.assertIn(f"Nguồn: {self.source.name} — Câu 1", app.show.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
