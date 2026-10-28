"""Kiểm tra bộ hỏi đáp của MP4 thực tế, không mở video/mic/GPIO hoặc tải ASR."""

import unittest
from unittest.mock import Mock

from cotu_app.core.paths import BASE
from cotu_app.core.settings import CONFIG, load_config
from cotu_app.features.stories.models import Knowledge
from cotu_app.features.stories.answers import answer_question
from cotu_app.features.video.content import learn_video, read_transcript, video_digest
from cotu_app.features.stories.questions import load_questions
from cotu_app.core.text import question_key
from cotu_app.core.files import resolve_path


class VideoQuestionBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.video = BASE / "data/videos/person_5.mp4"
        cls.bank = BASE / "data/videos/person_5.questions.json"
        cls.digest = video_digest(cls.video)
        cls.questions = load_questions(cls.bank, cls.digest)
        cls.knowledge = Knowledge(cls.digest, [], cls.questions, "bộ hỏi đáp biên soạn theo video")

    def test_all_questions_and_aliases_resolve_to_their_own_answer(self):
        self.assertEqual(len(self.questions), 32)
        self.assertTrue(all(item["character_id"] in load_config(CONFIG)["stories"] for item in self.questions))
        for item in self.questions:
            self.assertLess(item["source_start"], item["source_end"])
            self.assertLessEqual(item["source_end"], 223)
            for wording in [item["question"], *item.get("aliases", [])]:
                with self.subTest(question=wording):
                    answer = answer_question(wording, self.knowledge)
                    self.assertTrue(answer.approved)
                    self.assertEqual(answer.text, item["answer"])

    def test_natural_courtesy_and_name_variants(self):
        for wording, expected in (
            ("Già làng ơi, cho con hỏi nhà gươi là gì ạ?", "ngôi nhà chung"),
            ("Cho em hỏi là nhà gơi để làm gì vậy ạ?", "hội họp"),
            ("Con muốn hỏi mái nhà gươl làm bằng gì?", "lá tự nhiên"),
            ("Xin hỏi, sàn nhà gươl làm bằng gì trong video này?", "tre"),
            ("NHÀ GƯƠL CÓ BAO NHIÊU CỘT!!!", "chín cột"),
            ("nha guol co y nghia gi", "gắn kết"),
        ):
            with self.subTest(question=wording):
                answer = answer_question(wording, self.knowledge)
                self.assertTrue(answer.approved)
                self.assertIn(expected, answer.text)

    def test_not_in_video_specificity_and_negation_do_not_get_invented_answers(self):
        for wording in (
            "Nhà Gươl được xây vào năm nào?",
            "Xây nhà Gươl hết bao nhiêu tiền?",
            "Mái nhà Gươl được lợp bằng lá cây gì?",
            "Nhà Gươl không có cột phải không?",
            "Nhà Gươl được xây bằng bê tông phải không?",
            "Quảng Nam hiện nay có bao nhiêu xã?",
            "Người dệt vải trong video tên gì?",
            "Một cộng một bằng mấy?",
        ):
            with self.subTest(question=wording):
                self.assertFalse(answer_question(wording, self.knowledge).approved)

    def test_all_current_stories_using_this_video_load_without_asr(self):
        config = load_config(CONFIG)
        transcribe = Mock(side_effect=AssertionError("Không được gọi ASR khi đã có bộ hỏi đáp"))
        configured = 0
        for cid, story in config["stories"].items():
            if resolve_path(CONFIG, story.get("video")) != self.video:
                continue
            configured += 1
            knowledge = learn_video(CONFIG, config, cid, transcribe)
            self.assertEqual(knowledge.questions[:32], self.questions)
            self.assertEqual(len(knowledge.questions), 37)
            self.assertTrue(all(item["source_type"] == "document" for item in knowledge.questions[32:]))
            self.assertEqual(knowledge.video_sha256, self.digest)
            for item in self.questions:
                result = answer_question(item["question"], knowledge)
                self.assertTrue(result.approved)
                self.assertEqual(result.character_id, item["character_id"])
        self.assertEqual(configured, 6)
        transcribe.assert_not_called()

    def test_notes_have_timestamps_and_correct_proper_names(self):
        segments = read_transcript(BASE / "data/videos/person_5.notes.srt")
        self.assertEqual(len(segments), 14)
        self.assertTrue(all(segment["start"] is not None for segment in segments))
        text = " ".join(segment["text"] for segment in segments)
        self.assertIn("Cơ Tu", text)
        self.assertIn("Tây Giang", text)
        self.assertIn("nhà Gươl", text)

    def test_normalization_preserves_negation(self):
        self.assertIn("khong", question_key("Cho con hỏi nhà gươi không có cột phải không ạ?"))
        self.assertEqual(question_key("Bà cảm ơn ai?"), "ba cam on ai")

    def test_normalization_collision_does_not_pick_first_answer(self):
        knowledge = Knowledge("test", [], [
            {"question": "Nhà Gươl là gì?", "answer": "Một đáp án."},
            {"question": "Cho con hỏi nhà gươi là gì?", "answer": "Đáp án khác."},
        ], "test")
        self.assertFalse(answer_question("Nhà Gươl là gì?", knowledge).approved)


if __name__ == "__main__":
    unittest.main()
