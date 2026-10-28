"""Kiểm tra nút GPIO không mở phần cứng, video, màn hình hoặc mô hình."""

import copy
import importlib.util
import queue
import unittest
from unittest.mock import Mock, patch

from cotu_app.core.settings import CONFIG, load_config
from cotu_app.app.desktop import VideoApp, main
from cotu_app.features.stories.characters import CHARACTERS
from cotu_app.features.gpio.buttons import DEFAULT_BUTTONS, StoryButtons, button_mapping


class ButtonConfigTests(unittest.TestCase):
    def test_old_config_has_four_defaults_and_avoids_actual_rfid_reset(self):
        mapping = button_mapping({}, CHARACTERS)
        self.assertEqual(mapping, DEFAULT_BUTTONS)
        self.assertEqual(len(mapping), 4)
        self.assertNotIn(22, mapping.values())
        mapping["person_1"] = 5
        self.assertEqual(DEFAULT_BUTTONS["person_1"], 17)

    def test_can_assign_elder_and_fifth_person(self):
        mapping = {"elder": 17, "person_5": 27, "person_2": 23, "person_3": 24}
        self.assertEqual(button_mapping({"gpio_buttons": mapping}, CHARACTERS), mapping)

    def test_invalid_mappings_are_rejected(self):
        invalid = [None, [], {}, {"person_1": 17},
                   {**DEFAULT_BUTTONS, "ghost": 5},
                   {"ghost": 17, "person_2": 27, "person_3": 23, "person_4": 24}]
        for pin in (True, "17", 1, 28, 8, 9, 10, 11, 22, 25, 27):
            invalid.append({**DEFAULT_BUTTONS, "person_1": pin})
        for mapping in invalid:
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                button_mapping({"gpio_buttons": mapping}, CHARACTERS)

    def test_check_buttons_does_not_open_hardware(self):
        with patch("cotu_app.app.desktop.StoryButtons") as buttons, \
                patch("cotu_app.app.desktop.test_buttons") as test, \
                patch("builtins.print"):
            self.assertEqual(main(["--check", "--buttons"]), 0)
        buttons.assert_not_called()
        test.assert_not_called()

    def test_terminal_test_uses_config_without_gui_or_card_reader(self):
        with patch("cotu_app.app.desktop.test_buttons", return_value=0) as test, \
                patch("cotu_app.app.desktop.initialize_x11") as display, \
                patch("cotu_app.app.desktop.load_cards") as cards:
            self.assertEqual(main(["--test-buttons"]), 0)
        test.assert_called_once_with(button_mapping(load_config(CONFIG), CHARACTERS), CHARACTERS)
        display.assert_not_called()
        cards.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec("gpiozero"), "Cần gpiozero để chạy GPIO giả")
class ButtonInputTests(unittest.TestCase):
    def setUp(self):
        from gpiozero.pins.mock import MockFactory

        self.factory = MockFactory()
        self.events = queue.Queue(maxsize=16)
        self.buttons = StoryButtons(DEFAULT_BUTTONS, self.events, pin_factory=self.factory)
        self.addCleanup(self.factory.close)
        self.addCleanup(self.buttons.close)

    def test_each_press_selects_its_story_and_hold_does_not_repeat(self):
        self.assertTrue(self.events.empty())
        for cid, pin in DEFAULT_BUTTONS.items():
            gpio = self.factory.pin(pin)
            self.assertTrue(gpio.state)  # pull-up, chưa bấm
            gpio.drive_low()
            self.assertEqual(self.events.get_nowait(), cid)
            gpio.drive_low()  # giữ nút
            self.assertTrue(self.events.empty())
            gpio.drive_high()  # nhả nút không kể lại
            self.assertTrue(self.events.empty())
            gpio.drive_low()  # bấm lại kể lại cùng câu chuyện
            self.assertEqual(self.events.get_nowait(), cid)
            gpio.drive_high()

    def test_close_releases_pins_and_ignores_late_callbacks(self):
        self.buttons.close()
        self.buttons.close()
        self.buttons.enqueue("person_1")
        self.assertTrue(self.events.empty())
        self.assertTrue(all(button.closed for button in self.buttons.buttons))
        # Có thể mở lại cùng chân ngay sau khi đóng.
        reopened = StoryButtons(DEFAULT_BUTTONS, self.events, pin_factory=self.factory)
        reopened.close()

    def test_full_queue_does_not_block_gpio_callback(self):
        for _ in range(16):
            self.buttons.enqueue("person_1")
        self.buttons.enqueue("person_2")
        self.assertEqual(self.events.qsize(), 16)

    def test_partial_setup_failure_releases_previously_opened_pins(self):
        from gpiozero import Button

        self.buttons.close()
        opened = []

        def create(pin, **kwargs):
            if pin == 27:
                raise OSError("GPIO đang bận")
            button = Button(pin, **kwargs)
            opened.append(button)
            return button

        with patch("gpiozero.Button", side_effect=create), self.assertRaises(OSError):
            StoryButtons(DEFAULT_BUTTONS, self.events, pin_factory=self.factory)
        self.assertTrue(opened[0].closed)


class ButtonSessionTests(unittest.TestCase):
    def test_button_uses_existing_story_switch_and_cancels_old_work(self):
        app = VideoApp.__new__(VideoApp)
        app.config = copy.deepcopy(load_config(CONFIG))
        app.closed = False
        app.revision = Mock(value=7)
        app.revision.get_lock.return_value.__enter__ = Mock()
        app.revision.get_lock.return_value.__exit__ = Mock()
        app.busy = True
        app.pending = "elder"
        app.knowledge = "old knowledge"
        app.ids = list(CHARACTERS)
        for name in ("stop_playback", "stop_speech", "mic_button", "questions", "question",
                     "show", "choice", "refresh_details", "tabs", "play", "learn"):
            setattr(app, name, Mock())
        app.video_tab = "video tab"

        app.handle_button("person_3")

        self.assertEqual(app.cid, "person_3")
        self.assertEqual(app.revision.value, 8)
        self.assertFalse(app.busy)
        self.assertIsNone(app.pending)
        self.assertIsNone(app.knowledge)
        app.stop_playback.assert_called_once()
        app.stop_speech.assert_called_once()
        app.tabs.select.assert_called_once_with(app.video_tab)
        app.play.assert_called_once()
        app.learn.assert_called_once()

    def test_closed_app_and_unconfigured_character_are_ignored(self):
        app = VideoApp.__new__(VideoApp)
        app.config = load_config(CONFIG)
        app.select = Mock()
        app.closed = False
        app.handle_button("person_5")
        app.handle_button("invalid")
        app.closed = True
        app.handle_button("person_1")
        app.select.assert_not_called()


if __name__ == "__main__":
    unittest.main()
