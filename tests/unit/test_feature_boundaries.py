"""Importing domain/device adapters must not start the UI or load ML libraries."""

import json
import os
import subprocess
import sys
import unittest


class FeatureBoundaryTests(unittest.TestCase):
    def test_domain_and_device_modules_do_not_import_ui_or_models(self):
        code = (
            "import sys,json; import cotu_app.features.stories.questions; "
            "import cotu_app.features.rfid.cards; import cotu_app.features.stt.transcriber; "
            "import cotu_app.features.tts.voices; "
            "print(json.dumps([n for n in ['tkinter','vlc','faster_whisper','zerotts','gpiozero'] "
            "if n in sys.modules]))")
        loaded = json.loads(subprocess.check_output([sys.executable, "-c", code], env=os.environ, text=True))
        self.assertEqual(loaded, [])
