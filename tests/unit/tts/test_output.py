"""Kiểm tra gán giọng cho sáu nhân vật mà không nạp model lớn."""

import unittest
import sys
from unittest.mock import Mock, patch

from cotu_app.features.tts.output import AudioDeviceSelectionError, choose_output_device, choose_output_format, test_output_tone as play_test_tone
from cotu_app.features.tts.voices import load_voice_styles


class CharacterVoiceTests(unittest.TestCase):
    def test_characters_have_fixed_voices_matching_their_roles(self):
        styles = load_voice_styles()
        self.assertEqual(set(styles), {"elder", *(f"person_{i}" for i in range(1, 6))})
        self.assertEqual(len(set(styles.values())), 6)
        self.assertEqual(styles, {
            "elder": ("huuduc", 0.88), "person_1": ("giahuy", 1.0),
            "person_2": ("quangminh", 1.0), "person_3": ("kimoanh", 0.95),
            "person_4": ("tiendat", 1.0), "person_5": ("maichi", 1.0),
        })
        load_voice_styles.cache_clear()
        self.assertEqual(load_voice_styles(), styles)

    def test_audio_reports_missing_speaker_before_loading_model(self):
        sd = Mock()
        sd.query_devices.return_value = []
        with self.assertRaisesRegex(RuntimeError, "không thấy thiết bị phát âm thanh"):
            choose_output_device(sd)

    def test_audio_chooses_available_output_when_default_is_missing(self):
        sd = Mock()
        sd.query_devices.return_value = [
            {"name": "Mic", "max_output_channels": 0},
            {"name": "HDMI", "max_output_channels": 2},
        ]
        sd.default.device = [-1, -1]
        with patch("cotu_app.features.tts.output.output_preference", return_value=""):
            self.assertEqual(choose_output_device(sd), 1)
        sd.check_output_settings.assert_called_once_with(
            device=1, samplerate=48000, channels=2, dtype="int16")

    def test_audio_selects_alsa_card_one_instead_of_default_usb_zero(self):
        sd = Mock()
        sd.query_devices.return_value = [
            {"name": "USB speaker (hw:0,0)", "max_output_channels": 2},
            {"name": "USB speaker (hw:1,0)", "max_output_channels": 2},
        ]
        sd.default.device = [-1, 0]
        with patch("cotu_app.features.tts.output.output_preference", return_value="alsa:1"):
            self.assertEqual(choose_output_device(sd), 1)
        sd.check_output_settings.assert_called_once_with(
            device=1, samplerate=48000, channels=2, dtype="int16")

    def test_real_pi_listing_selects_usb_number_one_not_hdmi_zero(self):
        sd = Mock()
        sd.query_devices.return_value = [
            {"name": "vc4-hdmi-1: MAI PCM i2s-hifi-0 (hw:1,0)", "max_output_channels": 2},
            {"name": "USB Audio Device: - (hw:2,0)", "max_output_channels": 2},
        ]
        sd.default.device = [-1, 0]
        with patch("cotu_app.features.tts.output.output_preference", return_value="USB Audio Device"):
            self.assertEqual(choose_output_device(sd), 1)

    def test_audio_falls_back_to_44100_int16(self):
        class PortAudioError(Exception):
            pass

        sd = Mock()
        sd.PortAudioError = PortAudioError
        sd.check_output_settings.side_effect = [PortAudioError("48 kHz unsupported"), None]
        self.assertEqual(choose_output_format(sd, 1, 2), (44100, "int16", 2))

    def test_usb_hardware_is_selected_when_names_match_multiple_aliases(self):
        sd = Mock()
        sd.query_devices.return_value = [
            {"name": "HDMI", "max_output_channels": 2},
            {"name": "USB Audio Device: - (hw:2,0)", "max_output_channels": 2},
            {"name": "USB Audio Device via PipeWire", "max_output_channels": 2},
        ]
        self.assertEqual(choose_output_device(sd, "USB Audio Device"), 1)
        self.assertEqual(choose_output_device(sd, "alsa-name:USB Audio Device"), 1)

    def test_alsa_name_follows_usb_when_card_and_portaudio_numbers_change(self):
        sd = Mock()
        for card in (2, 3):
            sd.query_devices.return_value = [
                {"name": "USB Audio Device virtual", "max_output_channels": 2},
                {"name": "HDMI", "max_output_channels": 2},
                {"name": f"USB Audio Device: - (hw:{card},0)", "max_output_channels": 2},
            ]
            self.assertEqual(choose_output_device(sd, "alsa-name:USB Audio Device"), 2)

    def test_two_real_usb_speakers_report_candidates_instead_of_guessing(self):
        sd = Mock()
        sd.query_devices.return_value = [
            {"name": "USB Audio Device (hw:2,0)", "max_output_channels": 2},
            {"name": "USB Audio Device (hw:3,0)", "max_output_channels": 2},
        ]
        with self.assertRaisesRegex(AudioDeviceSelectionError, "Có nhiều ngõ ra.*#0.*#1"):
            choose_output_device(sd, "alsa-name:USB Audio Device")

    def test_missing_usb_is_distinct_from_duplicate_names_and_never_uses_hdmi(self):
        sd = Mock()
        sd.query_devices.return_value = [{"name": "HDMI", "max_output_channels": 2}]
        with self.assertRaisesRegex(AudioDeviceSelectionError, "Không tìm thấy loa.*HDMI"):
            choose_output_device(sd, "alsa-name:USB Audio Device")
        sd.check_output_settings.assert_not_called()

    def test_numeric_device_selection_does_not_match_digits_in_other_names(self):
        sd = Mock()
        sd.query_devices.return_value = [
            {"name": "HDMI (hw:1,0)", "max_output_channels": 2},
            {"name": "USB Audio Device (hw:2,0)", "max_output_channels": 2},
        ]
        self.assertEqual(choose_output_device(sd, "1"), 1)

    def test_full_name_takes_precedence_over_partial_name(self):
        sd = Mock()
        sd.query_devices.return_value = [
            {"name": "USB Audio Device A (hw:2,0)", "max_output_channels": 2},
            {"name": "USB Audio Device", "max_output_channels": 2},
        ]
        self.assertEqual(choose_output_device(sd, "USB Audio Device"), 1)

    def test_tone_opens_configured_output_not_default_hdmi(self):
        sd = Mock()
        devices = [
            {"name": "HDMI", "max_output_channels": 2},
            {"name": "USB Audio Device", "max_output_channels": 2},
        ]
        sd.query_devices.side_effect = lambda index=None: devices if index is None else devices[index]
        with patch.dict(sys.modules, {"sounddevice": sd}), \
                patch("cotu_app.features.tts.output.output_preference", return_value="USB Audio Device"):
            self.assertEqual(play_test_tone(), (1, 48000, "int16", 2))
        kwargs = sd.play.call_args.kwargs
        self.assertEqual(kwargs["device"], 1)
        self.assertEqual(kwargs["mapping"], [1, 2])
        self.assertEqual(kwargs["samplerate"], 48000)
        self.assertEqual(kwargs["blocking"], True)


if __name__ == "__main__":
    unittest.main()
