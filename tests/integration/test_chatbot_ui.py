"""Shared chatbot in the existing UI; fake transport, no API/audio/RFID calls."""

import os
import gc
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from cotu_app.features.chatbot import integration as chatbot
from cotu_app.features.stories.models import Knowledge
from cotu_app.app.desktop import VideoApp

from cotu_app.features.chatbot.config import Settings
from cotu_app.features.chatbot.service import ChatResult


class ChatIntegrationTests(unittest.TestCase):
    def test_defaults_remain_approved_and_invalid_modes_rejected(self):
        self.assertEqual(chatbot.chatbot_options({}), {"enabled": True, "mode": "approved"})
        for value in (None, [], {"mode": "all"}, {"enabled": "yes"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                chatbot.chatbot_options({"chatbot": value})

    def test_first_launch_builds_local_index_and_needs_no_key(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch("cotu_app.features.chatbot.retrieval.index_path", return_value=Path(tmp) / "research.sqlite3"), \
                patch("cotu_app.features.chatbot.config.Settings.from_env", return_value=Settings()):
            service = chatbot.create_service("research")
            result = service.ask("Gươl dùng để làm gì?", offline=True)
        self.assertEqual(result.status, "extractive_fallback")
        self.assertFalse(result.metrics["api_called"])
        self.assertIn("S03:guol", [d["document_id"] for d in result.citations])

    def test_unknown_typed_or_mic_question_routes_to_same_app_chat(self):
        app = VideoApp.__new__(VideoApp)
        app.busy, app.cid = False, "person_3"
        app.knowledge = Knowledge("video", [], [], "test")
        app.question = Mock()
        app.question.get.return_value = "Người Cơ Tu nói lý như thế nào?"
        app.pause, app.stop_speech, app.show = Mock(), Mock(), Mock()
        app.chat_panel, app.chat_tab, app.tabs = Mock(), "chat", Mock()
        with patch("cotu_app.app.desktop.start_speech") as speech:
            app.ask()
        app.tabs.select.assert_called_once_with("chat")
        app.chat_panel.submit_question.assert_called_once_with(app.question.get())
        app.show.assert_not_called()
        speech.assert_not_called()

    def test_approved_question_keeps_existing_answer_and_voice(self):
        app = VideoApp.__new__(VideoApp)
        app.busy, app.cid = False, "elder"
        app.knowledge = Knowledge("video", [], [{"question": "Ai dệt?", "answer": "Người dệt vải.",
                                                  "character_id": "person_3"}], "test")
        app.question = Mock()
        app.question.get.return_value = "Ai dệt?"
        app.pause, app.stop_speech, app.show, app.status = Mock(), Mock(), Mock(), Mock()
        app.chat_panel, app.chat_tab, app.tabs = Mock(), "chat", Mock()
        with patch("cotu_app.app.desktop.start_speech") as speech:
            app.ask()
        speech.assert_called_once_with("Người dệt vải.", "person_3")
        app.chat_panel.submit_question.assert_not_called()

    def test_busy_mic_blocks_api_and_idle_chat_pauses_video_and_audio(self):
        app = SimpleNamespace(busy=True, pause=Mock(), stop_speech=Mock())
        self.assertTrue(chatbot.prepare_chat(app))
        app.pause.assert_not_called()
        app.busy = False
        with patch("cotu_app.features.tts.service.warmup_speech") as warmup:
            self.assertIsNone(chatbot.prepare_chat(app))
        warmup.assert_called_once()
        app.pause.assert_called_once()
        app.stop_speech.assert_called_once()

    def test_character_sync_and_tab_leave_invalidate_context(self):
        app = SimpleNamespace(cid="person_3", chat_panel=Mock(), tabs=Mock(),
                              chat_tab="chat", stop_speech=Mock(), pause=Mock())
        chatbot.sync_character(app, reset=True)
        app.chat_panel.set_character.assert_called_once_with("person_3", "Người dệt vải", reset=True)
        app.tabs.select.return_value = "video"
        chatbot.chatbot_tab_changed(app)
        app.chat_panel.hide_keyboard.assert_called_once()
        app.chat_panel.stop.assert_called_once()
        chatbot.close_chatbot(app)
        app.chat_panel.dispose.assert_called_once()

    def test_explicit_read_uses_existing_tts_and_character(self):
        app = SimpleNamespace(stop_speech=Mock(), speech_kind=None, status=Mock())
        with patch("cotu_app.features.tts.service.start_speech", return_value="handle") as speech:
            chatbot.read_chat_answer(app, "Câu trả lời có nguồn.", "person_3")
        speech.assert_called_once_with("Câu trả lời có nguồn.", "person_3")
        self.assertEqual(app.speech_kind, "chat")


class PanelService:
    def __init__(self):
        self.retriever = SimpleNamespace(mode="research")
        self.calls = []
        self.release = threading.Event()
        self.release.set()
        self.status = "answered"
        self.answer_text = "Câu trả lời đã kiểm tra."
        self.citations = []
        self.notice = ""

    def ask(self, question, history, **kwargs):
        self.calls.append((question, history, kwargs["character_id"]))
        self.release.wait(3)
        kwargs["on_delta"]("Bản nháp")
        return ChatResult(self.answer_text, self.status, self.citations, character_id=kwargs["character_id"], notice=self.notice,
                          metrics={"total_ms": 12})


class EmbeddedChatGuiTests(unittest.TestCase):
    def setUp(self):
        if not os.getenv("NHARONG_TEST_DISPLAY"):
            self.skipTest("Cần NHARONG_TEST_DISPLAY cho kiểm tra Tk")
        import tkinter as tk
        from tkinter import ttk
        from cotu_app.features.chatbot.desktop import ChatPanel
        from cotu_app.ui.keyboard import TouchKeyboard

        self.root = tk.Tk(screenName=os.environ["NHARONG_TEST_DISPLAY"])
        self.addCleanup(self.close_tk)
        self.root.geometry("800x480")
        self.root.title("Ứng dụng chính")
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True)
        self.tab = ttk.Frame(self.tabs)
        self.tabs.add(self.tab, text="Chatbot Gemini")
        self.service, self.read = PanelService(), Mock()
        self.addCleanup(self.service.release.set)
        self.panel = ChatPanel(self.tab, self.service, read_answer=self.read,
                               keyboard_factory=TouchKeyboard)
        self.panel.pack(fill="both", expand=True)
        self.root.update()

    def close_tk(self):
        self.panel.dispose()
        self.root.destroy()
        # Collect Tcl objects on their owner thread before another worker
        # can trigger Python's cyclic GC during the next test.
        del self.panel, self.tabs, self.tab, self.root
        gc.collect()

    def finish(self):
        deadline = time.monotonic() + 4
        while self.panel.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.02)
        self.assertFalse(self.panel.busy)

    def test_embedded_send_keeps_main_window_and_reads_final_answer(self):
        self.panel.set_character("person_3", "Người dệt vải")
        self.assertTrue(self.panel.submit_question("Nói lý là gì?"))
        self.finish()
        self.assertEqual(self.root.title(), "Ứng dụng chính")
        self.assertEqual(self.service.calls[0][2], "person_3")
        self.assertIn("Câu trả lời đã kiểm tra.", self.panel.transcript.get("1.0", "end"))
        self.assertNotIn("Bản nháp", self.panel.transcript.get("1.0", "end"))
        self.read.assert_called_once_with("Câu trả lời đã kiểm tra.", "person_3")
        self.panel.read_last()
        self.assertEqual(self.read.call_count, 2)
        self.assertTrue(self.panel.history)

    def test_curated_chat_reads_exact_cached_text_with_answer_owner_voice(self):
        from cotu_app.features.stories.catalog import CuratedCatalog
        from cotu_app.features.chatbot.service import ChatService
        from cotu_app.features.chatbot.presentation import compact_answer
        retriever = SimpleNamespace(mode="research", search=Mock(side_effect=AssertionError("No retrieval")))
        client = Mock()
        text = "Đáp án đã duyệt.\nGiữ nguyên nội dung đọc."
        self.panel.service = ChatService(retriever, Settings(), client, curated=CuratedCatalog({
            "elder": [{"question": "Ai dệt vải?", "answer": text, "character_id": "person_3"}]}))
        self.panel.submit_question("Ai dệt vải?")
        self.finish()
        self.assertIn(compact_answer(text), self.panel.transcript.get("1.0", "end"))
        self.assertEqual(self.panel.history[-1]["content"], compact_answer(text))
        self.read.assert_called_once_with(text, "person_3")
        self.assertIn("có sẵn", self.panel.status.get())
        self.panel.read_last()
        self.assertEqual(self.read.call_count, 2)
        client.generate.assert_not_called()
        retriever.search.assert_not_called()

    def test_user_paraphrase_reads_existing_real_answer_without_ai(self):
        from cotu_app.core.settings import CONFIG, load_config
        from cotu_app.features.stories.catalog import CuratedCatalog
        from cotu_app.features.chatbot.service import ChatService
        catalog = CuratedCatalog.load(CONFIG, load_config(CONFIG))
        original = catalog.find("Nhà Gươl là gì?", "elder")
        retriever = SimpleNamespace(mode="research", search=Mock(side_effect=AssertionError("No retrieval")))
        client = Mock()
        self.panel.service = ChatService(retriever, Settings(), client, curated=catalog)
        self.panel.submit_question("nhà guol là cái gì")
        self.finish()
        self.assertIn(original["answer"], self.panel.transcript.get("1.0", "end"))
        self.read.assert_called_once_with(original["answer"], original["character_id"])
        self.assertEqual(self.panel.last_answer.metrics["route"], "curated")
        client.generate.assert_not_called()
        retriever.search.assert_not_called()

    def test_streamed_draft_is_not_read_before_final_answer(self):
        self.service.release.clear()
        self.panel.submit_question("Gươl là gì?")
        self.panel.events.put((self.panel.generation, "delta", "Bản nháp chưa kiểm tra"))
        self.panel.after_cancel(self.panel.poll_id)
        self.panel.poll()
        self.assertNotIn("Bản nháp chưa kiểm tra", self.panel.transcript.get("1.0", "end"))
        self.read.assert_not_called()
        self.service.release.set()
        self.finish()
        self.read.assert_called_once_with("Câu trả lời đã kiểm tra.", "elder")

    def test_cancelled_answer_is_not_read(self):
        self.service.release.clear()
        self.panel.submit_question("Gươl là gì?")
        self.panel.stop()
        self.service.release.set()
        self.finish()
        self.read.assert_not_called()
        self.assertIsNone(self.panel.last_answer)

    def test_fallback_excerpts_are_not_read_as_an_answer(self):
        self.service.status = "extractive_fallback"
        self.service.answer_text = "Đoạn tư liệu liên quan: [S03:guol] Nội dung nguồn rất dài."
        self.panel.submit_question("Gươl là gì?")
        self.finish()
        self.read.assert_not_called()
        self.assertIsNone(self.panel.last_answer)
        text = self.panel.transcript.get("1.0", "end")
        self.assertNotIn("Nội dung nguồn", text)
        self.assertNotIn("S03:guol", text)
        self.assertIn("chưa tổng hợp được", text)

    def test_one_summary_is_displayed_and_read_without_source_details(self):
        self.service.answer_text = "**Gươl là nhà chung.** [S03:guol]\n\nĐây là nơi sinh hoạt."
        self.service.citations = [{"document_id": "S03:guol", "title": "Tư liệu gươl",
                                  "source_url": "https://example.com/source"}]
        self.service.notice = "THỬ NGHIỆM — ghi chú chưa được duyệt."
        self.panel.submit_question("Gươl là gì?")
        self.finish()
        text = self.panel.transcript.get("1.0", "end")
        summary = "Gươl là nhà chung. Đây là nơi sinh hoạt."
        self.assertEqual(text.count(summary), 1)
        for metadata in ("S03:guol", "Tư liệu gươl", "https://", "Bản nháp"):
            self.assertNotIn(metadata, text)
        self.assertEqual(self.panel.status.get(), "Đã trả lời.")
        self.read.assert_called_once_with(summary, "elder")
        self.assertEqual(self.panel.history[-1]["content"], summary)

    def test_reset_during_request_drops_old_answer_and_voice(self):
        self.service.release.clear()
        self.panel.submit_question("Gươl là gì?")
        self.panel.set_character("person_3", "Người dệt vải")
        self.service.release.set()
        self.finish()
        self.assertFalse(self.panel.history)
        self.assertIsNone(self.panel.last_answer)
        self.assertNotIn("Câu trả lời", self.panel.transcript.get("1.0", "end"))
        self.assertEqual(self.panel.character_id, "person_3")
        self.read.assert_not_called()

    def test_keyboard_fits_touchscreen_and_restores_chat_layout(self):
        self.panel.keyboard.show()
        self.root.update()
        self.assertTrue(self.panel.entry.winfo_ismapped())
        self.assertTrue(self.panel.keyboard.winfo_ismapped())
        self.assertLess(self.panel.entry.winfo_rooty(), self.panel.keyboard.winfo_rooty())
        self.assertLessEqual(self.panel.keyboard.winfo_rooty() + self.panel.keyboard.winfo_height(),
                             self.root.winfo_rooty() + self.root.winfo_height())
        self.panel.hide_keyboard()
        self.root.update()
        self.assertTrue(self.panel.body.winfo_ismapped())

    def test_dispose_cancels_worker_and_poll_callback(self):
        self.panel.dispose()
        self.assertTrue(self.panel.cancel.is_set())
        self.assertTrue(self.panel.closed)
        self.assertFalse(self.panel.submit_question("Gươl?"))

    def test_mount_uses_existing_notebook_without_second_root(self):
        from tkinter import ttk
        setup = ttk.Frame(self.tabs)
        self.tabs.add(setup, text="Thiết lập")
        app = SimpleNamespace(tabs=self.tabs, setup_tab=setup, cid="elder", stop_speech=Mock(), pause=Mock())
        with patch("cotu_app.features.chatbot.integration.create_service", return_value=self.service), \
                patch("cotu_app.features.tts.service.warmup_speech") as warmup:
            chatbot.mount_chatbot(app, {"chatbot": {"mode": "research"}})
        warmup.assert_called_once()
        self.assertIs(app.tts_warmup, warmup.return_value)
        self.assertIs(app.chat_panel.winfo_toplevel(), self.root)
        self.assertEqual(self.tabs.index(app.chat_tab) + 1, self.tabs.index(setup))
        chatbot.open_chatbot(app)
        self.root.update()
        self.assertEqual(self.tabs.select(), str(app.chat_tab))


if __name__ == "__main__":
    unittest.main()
