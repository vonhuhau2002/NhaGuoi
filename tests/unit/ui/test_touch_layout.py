"""Touch navigation, scrolling and usable settings at the real kiosk size."""

import os
from types import SimpleNamespace
import tkinter as tk
import unittest

from tests.unit.ui.test_keyboard import Preview


class TouchLayoutTests(unittest.TestCase):
    def setUp(self):
        display = os.getenv("NHARONG_TEST_DISPLAY")
        if not display:
            self.skipTest("Cần NHARONG_TEST_DISPLAY cho kiểm tra bố cục cảm ứng")
        self.root = tk.Tk(screenName=display)
        self.addCleanup(self.root.destroy)
        self.app = Preview(self.root)
        self.root.geometry("800x480")
        self.root.update()

    def test_bottom_navigation_targets_fit_and_select_their_destination(self):
        for tab, button in self.app.nav_buttons.items():
            self.assertGreaterEqual(button.winfo_height(), 48)
            self.assertGreaterEqual(button.winfo_width(), 100)
            self.assertLessEqual(button.winfo_y() + button.winfo_height(),
                                 button.master.winfo_height())
            button.invoke()
            self.root.update()
            self.assertEqual(self.app.tabs.select(), tab)

    def test_dragging_question_list_scrolls_without_selecting_an_answer(self):
        self.app.tabs.select(self.app.qa_tab)
        rows = self.app.questions
        for index in range(30):
            rows.insert("end", f"Câu hỏi gợi ý số {index}?")
        self.root.update()
        before = rows.canvas.yview()[0]
        rows.touch_start(SimpleNamespace(y_root=250))
        rows.touch_move(SimpleNamespace(y_root=140))
        rows.choose(0)
        self.root.update()
        self.assertGreater(rows.canvas.yview()[0], before)
        self.app.choose_question.assert_not_called()
        rows.touch_start(SimpleNamespace(y_root=200))
        rows.choose(2)
        self.root.update()
        self.assertEqual(rows.curselection(), (2,))
        self.app.choose_question.assert_called_once()

    def test_scrolling_settings_reaches_the_last_controls(self):
        self.app.tabs.select(self.app.setup_tab)
        self.root.update()
        canvas = next(w for w in self.app.setup_tab.winfo_children() if isinstance(w, tk.Canvas))
        form = canvas.winfo_children()[0]
        close = next(w for row in form.winfo_children() for w in row.winfo_children()
                     if isinstance(w, tk.ttk.Button) and w.cget("text") == "Đóng ứng dụng")
        canvas.yview_moveto(1)
        self.root.update()
        self.assertGreaterEqual(close.winfo_rooty(), canvas.winfo_rooty())
        self.assertLessEqual(close.winfo_rooty() + close.winfo_height(),
                             canvas.winfo_rooty() + canvas.winfo_height())
