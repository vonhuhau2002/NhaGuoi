"""Kiểm tra hỏi đáp và hoàn tất giọng đọc mà không cần màn hình/đầu đọc."""

import io
import queue
import unittest
from unittest.mock import Mock, patch

from cotu_app.features.stories.characters import CHARACTERS
from cotu_app.features.stories.session import StorySession
from cotu_app.app.story_reader import LiveApp
from cotu_app.features.stories.sample_questions import STORY_QUESTIONS, questions_for


class ElderQuestionsTests(unittest.TestCase):
    def make_app(self, narrator="elder", story="person_1", result=0, kind="story"):
        app = LiveApp.__new__(LiveApp)
        app.session = StorySession()
        app.session.select_character(narrator)
        if narrator == "elder":
            app.session.elder_tells(story)
        app.completed_story = None
        app.manual_finish = False
        app.speech_kind = kind
        app.speech = Mock(returncode=result)
        app.speech.poll.return_value = result
        app.speech.tts_errors = io.BytesIO(b"RuntimeError: simulated TTS error\n")
        app.tick_process = None
        app.events = queue.Queue()
        app.root = Mock()
        app.status = Mock()
        app.refresh_questions = Mock()
        return app

    def test_questions_cover_five_stories(self):
        self.assertEqual(set(STORY_QUESTIONS), set(CHARACTERS) - {"elder"})
        for story, questions in STORY_QUESTIONS.items():
            self.assertEqual(len(questions), 3)
            self.assertEqual(len({q for q, _ in questions}), 3)
            self.assertTrue(all(q and a for q, a in questions))
            self.assertEqual(questions_for("elder", story, story), questions)

    def test_no_questions_before_completion_or_for_villagers(self):
        for story in STORY_QUESTIONS:
            self.assertFalse(questions_for("elder", story, None))
            self.assertFalse(questions_for(story, story, story))
            other = next(cid for cid in STORY_QUESTIONS if cid != story)
            self.assertFalse(questions_for("elder", story, other))
        self.assertFalse(questions_for("elder", "elder", "elder"))

    def test_successful_elder_story_opens_questions(self):
        app = self.make_app()
        app.poll()
        self.assertEqual(app.completed_story, "person_1")
        self.assertIsNone(app.speech)
        app.refresh_questions.assert_called_once()

    def test_failed_speech_needs_explicit_read_confirmation(self):
        app = self.make_app(result=1)
        app.poll()
        self.assertIsNone(app.completed_story)
        self.assertTrue(app.manual_finish)

    def test_answer_completion_does_not_complete_story(self):
        app = self.make_app(kind="answer")
        app.poll()
        self.assertIsNone(app.completed_story)
        app.refresh_questions.assert_not_called()

    def test_villager_cannot_open_questions_after_speech(self):
        app = self.make_app(narrator="person_1")
        app.poll()
        self.assertIsNone(app.completed_story)

    def test_stop_does_not_mark_story_complete(self):
        app = self.make_app(result=None)
        app.stop_speech()
        self.assertIsNone(app.speech)
        self.assertIsNone(app.speech_kind)
        self.assertIsNone(app.completed_story)

    def test_no_speech_engine_allows_reading_confirmation(self):
        app = self.make_app()
        with patch("cotu_app.app.story_reader.start_speech", side_effect=RuntimeError("model chưa cài")):
            app.speak()
        self.assertTrue(app.manual_finish)
        self.assertIsNone(app.completed_story)
        app.tabs = Mock()
        app.questions_tab = Mock()
        app.open_questions()
        self.assertEqual(app.completed_story, "person_1")
        app.tabs.select.assert_called_once_with(app.questions_tab)

    def test_stale_question_is_rejected_after_character_change(self):
        app = self.make_app(narrator="person_2")
        app.completed_story = "person_1"
        app.speak = Mock()
        app.set_answer = Mock()
        app.answer_question(*STORY_QUESTIONS["person_1"][0])
        app.speak.assert_not_called()
        app.set_answer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
