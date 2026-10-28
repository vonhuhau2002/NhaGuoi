"""Release activation, isolation and rollback, without UI, hardware or network."""

import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tools.deployment import manage_app as manager


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)
        self.root = self.base / "installed"

    def package(self, version, text="original", fail=False):
        package = self.base / f"{version}.tar.gz"
        files = {
            "release.json": json.dumps({"version": version, "format": 1,
                                         "compatibility": manager.compatibility()}),
            "defaults/video_stories.json": '{"stories": {}}',
            "defaults/rfid_cards.json": '{}',
            "defaults/launch.json": '{"args": []}',
            "nharong/feature.txt": text,
            "run_video.sh": "#!/bin/sh\nexit " + ("1" if fail else "0") + "\n",
        }
        with tarfile.open(package, "w:gz") as archive:
            for name, content in files.items():
                data = content.encode()
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        Path(str(package) + ".sha256").write_text(manager.digest(package) + "\n")
        return package

    def install(self, package):
        with patch.object(manager, "check_release"):
            manager.install(self.root, package, shortcuts=False)

    def test_update_and_rollback_preserve_user_data_and_previous_code(self):
        self.install(self.package("1.0.0"))
        old = manager.selected(self.root)
        cards = self.root / "shared/rfid_cards.json"
        cards.write_text('{"123": "elder"}')
        self.install(self.package("1.1.0", "new feature"))
        self.assertEqual(manager.selected(self.root).name, "1.1.0")
        self.assertEqual((old / "nharong/feature.txt").read_text(), "original")
        self.assertEqual(cards.read_text(), '{"123": "elder"}')
        with patch.object(manager, "check_release"):
            manager.rollback(self.root)
        self.assertEqual(manager.selected(self.root), old)
        self.assertEqual(cards.read_text(), '{"123": "elder"}')

    def test_failed_check_never_activates_new_release(self):
        self.install(self.package("1.0.0"))
        old = manager.selected(self.root)
        with patch.object(manager, "check_release", side_effect=RuntimeError("broken runtime")):
            with self.assertRaisesRegex(RuntimeError, "broken runtime"):
                manager.install(self.root, self.package("1.1.0"), shortcuts=False)
        self.assertEqual(manager.selected(self.root), old)
        self.assertFalse((self.root / "releases/1.1.0").exists())

    def test_corrupt_or_reused_package_does_not_replace_installed_code(self):
        package = self.package("1.0.0")
        self.install(package)
        with self.assertRaisesRegex(ValueError, "đã cài"):
            self.install(package)
        with package.open("ab") as stream:
            stream.write(b"corruption")
        with self.assertRaisesRegex(ValueError, "SHA256"):
            self.install(package)
        self.assertEqual(manager.selected(self.root).name, "1.0.0")

    def test_archive_cannot_write_outside_staging_directory(self):
        package = self.base / "evil.tar.gz"
        with tarfile.open(package, "w:gz") as archive:
            info = tarfile.TarInfo("../../outside.txt")
            info.size = 4
            archive.addfile(info, io.BytesIO(b"evil"))
        Path(str(package) + ".sha256").write_text(manager.digest(package))
        with self.assertRaises(tarfile.TarError):
            manager.install(self.root, package, shortcuts=False)
        self.assertFalse((self.root / "outside.txt").exists())

    def test_incompatible_runtime_is_rejected_before_activation(self):
        package = self.package("1.0.0")
        with patch.object(manager, "compatibility", return_value={"machine": "different"}):
            with self.assertRaisesRegex(ValueError, "cùng kiến trúc"):
                self.install(package)
        self.assertIsNone(manager.selected(self.root))
        self.assertFalse((self.root / "shared").exists())

    def test_second_launch_cannot_claim_hardware_while_first_is_running(self):
        self.install(self.package("1.0.0"))
        with manager.locked(self.root / "app.lock"):
            with self.assertRaisesRegex(RuntimeError, "đang chạy"):
                manager.launch(self.root, [])

    def test_launch_resolves_version_before_starting_child_and_clears_dev_paths(self):
        self.install(self.package("1.0.0"))
        old = manager.selected(self.root)
        with patch.dict(os.environ, {"PYTHONPATH": "/dev/source", "GEMINI_API_KEY": "dev-key"}), \
                patch.object(manager.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            manager.launch(self.root, ["--no-rfid"])
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["/bin/sh", str(old / "run_video.sh"), "--no-rfid"])
        self.assertEqual(kwargs["cwd"], old)
        self.assertNotIn("PYTHONPATH", kwargs["env"])
        self.assertNotIn("GEMINI_API_KEY", kwargs["env"])
        self.assertEqual(kwargs["env"]["NHARONG_DATA_DIR"], str(self.root / "shared"))

    def test_development_edits_do_not_change_snapshot(self):
        source = self.base / "source"
        for item in ("src/cotu_app", "resources", "tools/deployment", "deploy", "config/chatbot",
                     "data/chatbot/corpus", "data/chatbot/evaluation", "vendor/mfrc522",
                     "data/videos", "data/stories", ".venv-video/lib",
                     ".venv-video/native", ".venv-video/models", ".venv-video/bin"):
            (source / item).mkdir(parents=True, exist_ok=True)
        (source / ".venv-video/bin/python").symlink_to(sys.executable)
        (source / ".venv-video/pyvenv.cfg").write_text("include-system-site-packages = true\n")
        feature = source / "src/cotu_app/feature.py"
        feature.write_text("FEATURE = 'stable'\n")
        for name in ("run_video.sh", "run_rfid.sh", "run_chatbot.sh", "requirements-video.txt",
                     "pyproject.toml", "tools/deployment/manage_app.py", "deploy/nharong-cotu.svg",
                     "config/chatbot/.env.example", "config/chatbot/aliases.json",
                     *("config/" + name for name in manager.CONFIG_FILES)):
            (source / name).write_text("{}")
        (source / "config/video_stories.json").write_text(json.dumps({"stories": {"elder": {
            "video": "../data/videos/story.mp4"}}}))
        (source / "config/chatbot/.env").write_text("GEMINI_API_KEY=never-package-this")
        package = manager.build(source, self.base / "dist", "1.0.0")
        feature.write_text("FEATURE = 'development only'\n")
        self.install(package)
        self.assertEqual((manager.selected(self.root) / "src/cotu_app/feature.py").read_text(), "FEATURE = 'stable'\n")
        with tarfile.open(package) as archive:
            self.assertNotIn("config/chatbot/.env", archive.getnames())
        config = json.loads((self.root / "shared/video_stories.json").read_text())
        self.assertEqual(config["stories"]["elder"]["video"], "videos/story.mp4")
        self.assertEqual((manager.selected(self.root) / ".venv-video/bin/python").resolve(), Path(sys.executable).resolve())

    def test_data_paths_and_api_config_are_selected_outside_code(self):
        data = self.base / "my data"
        data.mkdir()
        key_file = data / "chatbot.env"
        key_file.write_text("GEMINI_API_KEY=installed-test-key\n")
        code = ("from cotu_app.core.paths import DATA; from cotu_app.features.chatbot.config import Settings; "
                "from cotu_app.features.tts.voices import VOICES_FILE; "
                "import json; print(json.dumps([str(DATA), str(VOICES_FILE), Settings.from_env().api_key]))")
        env = manager.runtime_env(manager.SOURCE, data)
        env["PYTHONPATH"] = str(manager.SOURCE / "src")
        result = json.loads(subprocess.check_output([sys.executable, "-c", code],
                                                   cwd=manager.SOURCE, env=env, text=True))
        self.assertEqual(result, [str(data), str(data / "tts_voices.json"), "installed-test-key"])


if __name__ == "__main__":
    unittest.main()
