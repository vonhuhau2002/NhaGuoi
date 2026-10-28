import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cotu_app.features.stories.catalog import CuratedCatalog


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config_path = self.root / "config.json"
        self.video = self.root / "video.mp4"
        self.video.write_bytes(b"source video")
        self.item = {"question": "Nhà Gươl là gì?", "answer": "Ngôi nhà chung.",
                     "aliases": ["Giới thiệu nhà Gươl"], "character_id": "elder"}
        self.write("video.json", {"video_sha256": hashlib.sha256(self.video.read_bytes()).hexdigest(),
                                  "questions": [self.item]})
        self.source = self.root / "source.txt"
        self.source.write_text("Câu 1: Ai dệt vải?\nNgười dệt.\n", encoding="utf-8")
        self.write("doc.json", {"source_file": "source.txt",
                                "source_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
                                "questions": [{"question": "Ai dệt vải?", "answer": "Người dệt.",
                                               "character_id": "person_3", "source_question": 1}]})
        self.config = {"stories": {cid: {"video": "video.mp4", "questions": "video.json"}
                                   for cid in ("elder", "person_3")},
                       "document_questions": ["doc.json"]}

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def load(self):
        return CuratedCatalog.load(self.config_path, self.config)

    def test_aliases_accents_salutations_and_owner_across_characters(self):
        catalog = self.load()
        item = catalog.find("Già làng ơi, cho con hỏi nha guoi la gi vậy?", "person_3")
        self.assertEqual(item["answer"], self.item["answer"])
        self.assertEqual(item["character_id"], "elder")
        self.assertEqual(catalog.find("gioi thieu nha guol", "elder")["answer"], self.item["answer"])
        self.assertEqual(catalog.find("Ai dệt vải?", "elder")["character_id"], "person_3")
        for question in ("Nhà Gươl không là gì?", "Nhà Gươl có phải nhà riêng không?", "Ai dệt?"):
            self.assertIsNone(catalog.find(question, "elder"))

    def test_video_hash_checked_once_for_shared_bank_and_never_per_question(self):
        from cotu_app.features.video.content import video_digest
        with patch("cotu_app.features.video.content.video_digest", wraps=video_digest) as digest:
            catalog = self.load()
            for _ in range(5):
                catalog.find("Nhà Gươl là gì?", "elder")
            self.assertEqual(digest.call_count, 1)

    def test_changed_video_rejects_bank_but_preserves_valid_document(self):
        self.video.write_bytes(b"replacement video")
        with self.assertLogs("cotu_app.features.stories.catalog", level="WARNING"):
            catalog = self.load()
        self.assertIsNone(catalog.find("Nhà Gươl là gì?", "elder"))
        self.assertIsNotNone(catalog.find("Ai dệt vải?", "elder"))

    def test_changed_document_rejects_answers_and_new_snapshot_keeps_video(self):
        original = self.load()
        self.source.write_text("Câu 1: Ai dệt vải?\nĐã sửa lời đáp.\n", encoding="utf-8")
        with self.assertLogs("cotu_app.features.stories.catalog", level="WARNING"):
            changed = self.load()
        self.assertIsNotNone(original.find("Ai dệt vải?", "elder"))
        self.assertIsNone(changed.find("Ai dệt vải?", "elder"))
        self.assertIsNotNone(changed.find("Nhà Gươl là gì?", "elder"))

    def test_normalized_ambiguous_wording_does_not_pick_arbitrary_answer(self):
        other = {"question": "Khác?", "aliases": ["Nha guoi la gi"],
                 "answer": "Lời khác.", "character_id": "person_3"}
        catalog = CuratedCatalog({"elder": [self.item, other, self.item]})
        self.assertIsNone(catalog.find("Nhà Gươl là gì?", "elder"))
        self.assertEqual(catalog.find("Khác?", "elder")["answer"], "Lời khác.")

    def test_equivalent_definition_collision_does_not_choose_an_answer(self):
        other = {"question": "Nhà Gươl là cái gì?", "answer": "Lời khác.",
                 "character_id": "person_3"}
        catalog = CuratedCatalog({"elder": [self.item, other]})
        self.assertIsNone(catalog.find("Nhà Gươl được hiểu là gì?", "elder"))

    def test_unassigned_video_voice_uses_selected_character(self):
        item = {k: v for k, v in self.item.items() if k != "character_id"}
        self.write("video.json", {"video_sha256": hashlib.sha256(self.video.read_bytes()).hexdigest(),
                                  "questions": [item]})
        catalog = self.load()
        self.assertEqual(catalog.find(item["question"], "person_3")["character_id"], "person_3")


class RealBankParaphraseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cotu_app.core.settings import CONFIG, load_config
        from cotu_app.features.video.content import learn_video
        cls.catalog = CuratedCatalog.load(CONFIG, load_config(CONFIG))
        def refuse_asr(*args):
            raise AssertionError("No ASR")
        cls.knowledge = learn_video(CONFIG, load_config(CONFIG), "elder", refuse_asr)

    def test_equivalent_questions_use_same_approved_text_and_voice_in_both_features(self):
        from cotu_app.features.stories.answers import answer_question
        for question, original in (
            ("nhà guol là cái gì", "Nhà Gươl là gì?"),
            ("Gươl là cái gì thế ạ?", "Nhà Gươl là gì?"),
            ("Bạn có thể giải thích giúp tôi nhà Gươl được hiểu là gì vậy ạ?", "Nhà Gươl là gì?"),
            ("Tôi muốn biết thế nào là ngôi nhà Gươl?", "Nhà Gươl là gì?"),
            ("Thưa già làng, nhà gươi có nghĩa là gì?", "Nhà Gươl là gì?"),
            ("Công dụng của Gươl là gì?", "Người dân dùng nhà Gươl để làm gì?"),
            ("Gươl được sử dụng để làm cái gì?", "Người dân dùng nhà Gươl để làm gì?"),
            ("Mái nhà Gươl làm bằng chất liệu nào?", "Mái nhà Gươl được lợp bằng gì?"),
            ("Tại sao nhà Gươl được xem là trái tim của làng?", "Vì sao nhà Gươl được xem là trái tim của làng?"),
            ("Ngôi nhà Gươl có mấy cột con thế?", "Nhà Gươl có bao nhiêu cột con?"),
            ("Chim Tring có ý nghĩa gì?", "Ý nghĩa của chim Tring"),
            ("Ý nghĩa của nói lý hát lý là cái gì?", "Ý nghĩa của nói lý hát lý"),
        ):
            with self.subTest(question=question):
                expected = self.catalog.find(original, "elder")
                for cid in ("elder", "person_3"):
                    matched = self.catalog.find(question, cid)
                    self.assertIsNotNone(matched)
                    self.assertEqual(matched["answer"], expected["answer"])
                    self.assertEqual(matched["character_id"], expected["character_id"])
                answer = answer_question(question, self.knowledge)
                self.assertTrue(answer.approved)
                self.assertEqual(answer.text, expected["answer"])
                self.assertEqual(answer.character_id, expected["character_id"])

    def test_unknown_details_negation_compound_questions_and_changed_intents_still_miss(self):
        from cotu_app.features.stories.answers import answer_question
        for question in (
            "Nhà Gươl không là cái gì?", "Nhà Gươl không dùng để làm cái gì?",
            "Mái nhà Gươl được lợp bằng lá cây gì?", "Sàn nhà Gươl làm bằng loại tre nào?",
            "Nhà Gươl có bao nhiêu cột bằng bê tông?", "Nhà Gươl là cái gì ở Huế?",
            "Nhà Gươl dùng để làm gì vào năm 2026?", "Nhà Gươl là gì và xây hết bao nhiêu tiền?",
            "Nhà Gươl có phải là nhà riêng không?", "Vì sao nhà Gươl là cái gì?",
            "Chim Tring không có ý nghĩa gì?", "Chim Tring có ý nghĩa gì ở Huế?",
        ):
            with self.subTest(question=question):
                self.assertIsNone(self.catalog.find(question, "elder"))
                self.assertFalse(answer_question(question, self.knowledge).approved)
