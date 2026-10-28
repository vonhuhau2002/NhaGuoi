"""NHARONG_TEST_DISPLAY=:93 để kiểm tra Tk trên màn hình ảo riêng."""

import os
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import Mock, patch

from cotu_app.app.desktop import VideoApp
from cotu_app.ui.keyboard import TONES, toned_vowel
from cotu_app.ui.video import VideoInterface


class VietnameseKeyboardTests(unittest.TestCase):
    def test_tones_preserve_vowel_shape_and_case(self):
        for original, label, expected in (
            ("ơ", "Hỏi", "ở"), ("ễ", "Sắc", "ế"), ("Ư", "Huyền", "Ừ"),
            ("ặ", "Ngã", "ẵ"), ("ố", "Bỏ dấu", "ô"), ("y", "Nặng", "ỵ"),
            ("đ", "Sắc", "đ"), ("?", "Hỏi", "?"), (" ", "Huyền", " "),
        ):
            with self.subTest(original=original, label=label):
                self.assertEqual(toned_vowel(original, TONES[label]), expected)


class Preview(VideoInterface):
    def __init__(self, root):
        self.root, self.tk, self.ttk = root, tk, ttk
        self.config = {"microphone": None}
        self.cid, self.pending = "elder", None
        for name in ("select", "resume", "pause", "play", "stop_playback", "listen", "learn",
                     "stop_speech", "ask", "choose_question", "select_file", "enroll",
                     "cancel_enrollment", "save_microphone", "refresh_details", "show"):
            setattr(self, name, Mock())
        self.close = root.destroy
        self.build_interface()

    tab_changed = VideoApp.tab_changed


class TouchKeyboardGuiTests(unittest.TestCase):
    def setUp(self):
        display = os.environ.get("NHARONG_TEST_DISPLAY")
        if not display:
            self.skipTest("Cần NHARONG_TEST_DISPLAY trỏ tới màn hình thử riêng")
        self.root = tk.Tk(screenName=display)
        self.addCleanup(self.root.destroy)
        self.app = Preview(self.root)
        self.app.tabs.select(self.app.qa_tab)
        self.root.update()
        self.keyboard = self.app.question_keyboard
        self.entry = self.app.question_entry

    def test_fullscreen_click_shows_inline_keyboard_and_keeps_entry_visible(self):
        self.assertFalse(self.keyboard.winfo_ismapped())
        with patch.object(self.root, "attributes", return_value=True):
            self.entry.event_generate("<ButtonRelease-1>")
            self.root.update()
            self.assertTrue(self.keyboard.winfo_ismapped())
            self.assertTrue(self.entry.winfo_ismapped())
            self.assertLess(self.entry.winfo_rooty() + self.entry.winfo_height(),
                            self.keyboard.winfo_rooty())
            self.assertLessEqual(self.keyboard.winfo_rooty() + self.keyboard.winfo_height(),
                                 self.root.winfo_rooty() + self.root.winfo_height())
            self.assertFalse(self.app.question_body.winfo_ismapped())
            for row in self.keyboard.rows:
                for key in row.winfo_children():
                    self.assertGreaterEqual(key.winfo_height(), 50)
                    self.assertGreaterEqual(key.winfo_width(), 55)
            self.keyboard.hide()
            self.root.update()
            self.assertTrue(self.app.question_body.winfo_ismapped())

    def test_vietnamese_keys_are_large_and_restore_layout_after_repeated_open(self):
        packed_before = self.app.qa_tab.pack_slaves()
        for _ in range(2):
            self.keyboard.show()
            self.keyboard.show()
            self.keyboard.toggle_vietnamese()
            self.root.update()
            self.assertTrue(self.keyboard.vietnamese)
            for row in self.keyboard.rows:
                for key in row.winfo_children():
                    self.assertGreaterEqual(key.winfo_width(), 80)
                    self.assertGreaterEqual(key.winfo_height(), 50)
            self.keyboard.toggle_numbers()
            self.assertFalse(self.keyboard.vietnamese)
            self.assertTrue(self.keyboard.numbers)
            self.keyboard.hide()
            self.keyboard.hide()
            self.root.update()
            self.assertEqual(self.app.qa_tab.pack_slaves(), packed_before)

    def test_large_window_keyboard_keeps_question_above_keys(self):
        self.root.geometry("1100x720")
        self.keyboard.show()
        self.root.update()
        self.assertLess(self.entry.winfo_rooty() + self.entry.winfo_height(),
                        self.keyboard.winfo_rooty())
        self.assertGreater(self.keyboard.rows[0].winfo_height(), 56)

    def test_windowed_click_and_explicit_toggle(self):
        with patch.object(self.root, "attributes", return_value=False):
            self.app.open_question_keyboard()
        self.assertFalse(self.keyboard.winfo_manager())
        self.app.toggle_question_keyboard()
        self.assertEqual(self.keyboard.winfo_manager(), "pack")
        self.app.toggle_question_keyboard()
        self.assertFalse(self.keyboard.winfo_manager())

    def test_keys_type_vietnamese_and_edit_at_cursor(self):
        self.keyboard.insert("Ngu")
        self.keyboard.backspace()
        self.keyboard.type_letter("ư")
        self.keyboard.type_letter("ơ")
        self.keyboard.add_tone(TONES["Huyền"])
        self.keyboard.insert("i kể chuyện?")
        self.assertEqual(self.entry.get(), "Người kể chuyện?")
        self.entry.icursor(0)
        self.keyboard.backspace()
        self.assertEqual(self.entry.get(), "Người kể chuyện?")
        self.keyboard.insert("Xin chào ")
        self.entry.selection_range(0, 9)
        self.keyboard.insert("Chào ")
        self.assertEqual(self.entry.get(), "Chào Người kể chuyện?")
        self.entry.icursor("end")
        self.keyboard.move(-1)
        self.keyboard.backspace()
        self.assertEqual(self.entry.get(), "Chào Người kể chuyệ?")

    def test_shift_numbers_selection_delete_and_clear(self):
        self.keyboard.toggle_shift()
        self.keyboard.type_letter("đ")
        self.assertEqual(self.entry.get(), "Đ")
        self.keyboard.toggle_numbers()
        self.keyboard.insert("123")
        self.assertEqual(self.entry.get(), "Đ123")
        self.entry.selection_range(1, 4)
        self.keyboard.backspace()
        self.assertEqual(self.entry.get(), "Đ")
        self.keyboard.clear()
        self.assertEqual(self.entry.get(), "")

    def test_both_submit_paths_hide_keyboard_and_ask_once(self):
        for send in (self.keyboard.send, self.app.submit_typed_question):
            self.app.ask.reset_mock()
            self.keyboard.show()
            send()
            self.assertFalse(self.keyboard.winfo_manager())
            self.app.ask.assert_called_once()

    def test_leaving_questions_hides_keyboard(self):
        self.keyboard.show()
        self.root.update()
        self.app.tabs.select(self.app.video_tab)
        self.root.update()
        self.assertFalse(self.keyboard.winfo_manager())


if __name__ == "__main__":
    unittest.main()
