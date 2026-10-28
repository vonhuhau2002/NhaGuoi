#!/usr/bin/env python3
"""Local, offline release manager for the Raspberry Pi desktop application."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile


SOURCE = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = Path.home() / ".local/share/nharong-cotu"
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?")
CONFIG_FILES = ("video_stories.json", "rfid_cards.json", "tts_voices.json", "tts_output.json")


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path, data):
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def atomic_write(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".writing-")
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Ứng dụng hoặc thao tác này đang chạy.") from None
        yield stream


def compatibility():
    os_info = platform.freedesktop_os_release()
    return {"machine": platform.machine(), "python": list(sys.version_info[:2]),
            "os": os_info.get("ID"), "os_version": os_info.get("VERSION_ID")}


def clean_member(info):
    parts = Path(info.name).parts
    if any(part in {"__pycache__", ".git", ".locks", ".no_exist"} for part in parts):
        return None
    if info.name.endswith((".pyc", ".pyo")) or Path(info.name).name in {".env", ".agent_harnesses.json"}:
        return None
    # A venv is machine-specific. Recreate Python links on the target Pi; only
    # invoke bin/python, never scripts with a development-directory shebang.
    if info.name.startswith(".venv-video/bin/"):
        return None
    if not (info.isdir() or info.isfile() or info.issym()):
        raise ValueError(f"Không đóng gói file đặc biệt: {info.name}")
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def add_json(archive, name, data):
    content = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    info = tarfile.TarInfo(name)
    info.size, info.mode = len(content), 0o644
    archive.addfile(info, io.BytesIO(content))


def portable_config(source):
    config_file = source / "config/video_stories.json"
    config = json.loads(config_file.read_text(encoding="utf-8"))
    def relative(value):
        if not value:
            return value
        try:
            path = (config_file.parent / value).resolve()
            result = path.relative_to((source / "data").resolve())
        except ValueError:
            raise ValueError(f"Hãy chép tài nguyên vào videos/ trước khi phát hành: {value}") from None
        if result.parts[0] not in {"videos", "stories"}:
            raise ValueError(f"Tài nguyên phải thuộc data/videos/ hoặc data/stories/: {value}")
        return str(result)
    for story in config["stories"].values():
        for key in ("video", "transcript", "questions"):
            if key in story:
                story[key] = relative(story[key])
    config["document_questions"] = [relative(p) for p in config.get("document_questions", [])]
    if Path(config.get("whisper_model", "base")).is_absolute():
        raise ValueError("Bản phát hành cần whisper_model là tên model, ví dụ base.")
    return config


def build(source, output, version):
    if not VERSION.fullmatch(version):
        raise ValueError("Phiên bản cần dạng 1.0.0 hoặc 1.0.0-beta.1.")
    runtime = source / ".venv-video"
    if not (runtime / "bin/python").is_file():
        raise ValueError("Chưa có .venv-video; xem docs/HUONG_DAN_VIDEO.md.")
    runtime_version = json.loads(subprocess.check_output(
        [str(runtime / "bin/python"), "-c", "import sys,json; print(json.dumps(list(sys.version_info[:2])))"],
        text=True))
    if runtime_version != list(sys.version_info[:2]):
        raise ValueError("Python của appctl và .venv-video phải cùng phiên bản major/minor.")
    # Editable installs can make an apparently isolated release import live code.
    for pattern in ("lib/**/*.pth", "lib/**/*.egg-link"):
        for path in runtime.glob(pattern):
            raise ValueError(f"Cần runtime không có editable/path hook trước khi phát hành: {path}")
    config = portable_config(source)
    rfid = source / "vendor/mfrc522"
    if not rfid.is_dir():
        rfid = Path("/home/admin/mfrc522_test/src/mfrc522")
    if not rfid.is_dir():
        raise ValueError("Cần thư viện RFID đã dùng được ở vendor/mfrc522.")
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"nharong-cotu-{version}-{platform.machine()}.tar.gz"
    if target.exists():
        raise ValueError("Gói phiên bản này đã tồn tại. Hãy tăng số phiên bản.")
    metadata = {"version": version, "built_at": datetime.now(timezone.utc).isoformat(),
                "compatibility": compatibility(), "format": 2}
    fd, name = tempfile.mkstemp(dir=output, prefix=".building-", suffix=".tar.gz")
    os.close(fd)
    temporary = Path(name)
    try:
        print("Đang đóng gói code, runtime và model độc lập...", flush=True)
        with tarfile.open(temporary, "w:gz", compresslevel=1) as archive:
            for item in ("src", "resources", "run_video.sh", "run_rfid.sh", "run_chatbot.sh",
                         "requirements-video.txt", "pyproject.toml",
                         "tools/deployment/manage_app.py", "deploy/nharong-cotu.svg",
                         "config/chatbot/aliases.json", "config/chatbot/.env.example",
                         "data/chatbot/corpus", "data/chatbot/evaluation"):
                archive.add(source / item, arcname=item, filter=clean_member)
            for item in ("lib", "pyvenv.cfg", "native", "models"):
                archive.add(runtime / item, arcname=f".venv-video/{item}", filter=clean_member)
            archive.add(rfid, arcname="vendor/mfrc522", filter=clean_member)
            license_file = rfid.parent / "LICENSE"
            if not license_file.is_file():
                license_file = rfid.parent / "MFRC522-LICENSE"
            if license_file.is_file():
                archive.add(license_file, arcname="vendor/MFRC522-LICENSE")
            for item in ("videos", "stories"):
                archive.add(source / "data" / item, arcname=f"defaults/{item}", filter=clean_member)
            for item in CONFIG_FILES:
                if item != "video_stories.json":
                    archive.add(source / "config" / item, arcname=f"defaults/{item}", filter=clean_member)
            add_json(archive, "defaults/video_stories.json", config)
            add_json(archive, "defaults/launch.json", {"args": []})
            add_json(archive, "release.json", metadata)
        checksum = digest(temporary)
        temporary.replace(target)
        atomic_write(Path(str(target) + ".sha256"), checksum + "  " + target.name + "\n")
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Gói: {target}\nSHA256: {checksum}")
    return target


def runtime_env(release, data):
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "NHARONG_VIDEO_ENV",
                "GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL", "GEMINI_THINKING_LEVEL"):
        env.pop(key, None)
    for key in list(env):
        if key.startswith("CHATBOT_"):
            env.pop(key)
    env.update(NHARONG_DATA_DIR=str(data), NHARONG_CHATBOT_ENV=str(data / "chatbot.env"),
               PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
    if (release / "src/cotu_app").is_dir():
        env["PYTHONPATH"] = str(release / "src")
    return env


def check_release(release, data):
    env = runtime_env(release, data)
    subprocess.run(["/bin/sh", str(release / "run_video.sh"), "--check"],
                   cwd=release, env=env, check=True, timeout=90)
    if (release / "src/cotu_app").is_dir():
        code = ("import sys; sys.path.insert(0,'vendor'); "
                "from cotu_app.features.chatbot.retrieval import build_index; "
                "from cotu_app.features.chatbot.config import ROOT, Settings; "
                "[build_index(ROOT/'corpus/documents.jsonl',ROOT/('index/'+m+'.sqlite3'),m) "
                "for m in ('approved','research')]; Settings.from_env(); "
                "import mfrc522, tkinter, vlc; vlc.libvlc_get_version(); "
                "from cotu_app.core.settings import load_config; "
                "from cotu_app.core.files import resolve_path; "
                "from cotu_app.features.stories.questions import load_document_questions; ")
    else:
        # Keep old packages and rollback to v1.0.0 supported.
        code = ("import sys; sys.path[:0]=['chatbot/src','vendor']; "
            "from cotu_chatbot.retrieval import build_index; "
            "from cotu_chatbot.config import ROOT; "
            "[build_index(ROOT/'data/corpus/documents.jsonl',ROOT/('data/index/'+m+'.sqlite3'),m) "
            "for m in ('approved','research')]; "
            "import mfrc522, tkinter, vlc; vlc.libvlc_get_version(); "
            "from cotu_chatbot.config import Settings; Settings.from_env(); "
            "from nharong.app_rfid_video import load_config,load_document_questions,resolve_path; "
            )
    code += ("from pathlib import Path; "
             f"p=Path({str(data / 'video_stories.json')!r}); c=load_config(p); "
             "[load_document_questions(resolve_path(p,v)) for v in c.get('document_questions',[])]")
    subprocess.run([str(release / ".venv-video/bin/python"), "-c", code],
                   cwd=release, env=env, check=True, timeout=90)


def switch_link(root, name, target):
    temporary = root / ("." + name + "-next")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target.relative_to(root), target_is_directory=True)
    temporary.replace(root / name)


def selected(root, name="current"):
    path = root / name
    return path.resolve(strict=True) if path.is_symlink() else None


def install(root, package, shortcuts=True):
    package = package.resolve()
    checksum_file = Path(str(package) + ".sha256")
    expected = checksum_file.read_text(encoding="utf-8").split()[0]
    if not re.fullmatch(r"[a-f0-9]{64}", expected) or digest(package) != expected:
        raise ValueError("SHA256 không khớp; giữ nguyên bản đang dùng.")
    with locked(root / "update.lock"):
        releases = root / "releases"
        releases.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=releases, prefix=".installing-") as directory:
            stage = Path(directory)
            print("Đang giải nén và kiểm tra bản phát hành...", flush=True)
            with tarfile.open(package, "r:gz") as archive:
                archive.extractall(stage, filter="data")
            metadata = json.loads((stage / "release.json").read_text(encoding="utf-8"))
            version = metadata["version"]
            if metadata.get("format") not in {1, 2} or not VERSION.fullmatch(version):
                raise ValueError("Định dạng gói/phiên bản không hợp lệ.")
            if metadata["compatibility"] != compatibility():
                raise ValueError("Gói cần cùng kiến trúc, Python và phiên bản OS với Pi hiện tại.")
            target = releases / version
            if target.exists():
                raise ValueError("Phiên bản đã cài. Dùng rollback hoặc phát hành phiên bản mới.")
            binary = stage / ".venv-video/bin"
            binary.mkdir(parents=True, exist_ok=True)
            (binary / "python").symlink_to(sys.executable)
            # The temporary path becomes the final path; no links to the workspace.
            data = root / "shared"
            check_release(stage, data if data.exists() else stage / "defaults")
            if not data.exists():
                # Seed once. Updates and rollback never overwrite user configuration.
                with tempfile.TemporaryDirectory(dir=root, prefix=".seed-") as seed_dir:
                    seed = Path(seed_dir) / "shared"
                    shutil.copytree(stage / "defaults", seed)
                    atomic_write(seed / "chatbot.env", "# GEMINI_API_KEY=\n", 0o600)
                    seed.rename(data)
            stage.rename(target)
            # TemporaryDirectory must still find its original path on cleanup.
            stage.mkdir()
        old = selected(root)
        if old is not None:
            switch_link(root, "previous", old)
        if shortcuts:
            install_shortcuts(root, target)
        switch_link(root, "current", target)
    print(f"Đã cài v{version}. Mở app lần tiếp theo sẽ dùng bản này.")


def install_shortcuts(root, release):
    manager = root / "manager.py"
    source_manager = release / "tools/deployment/manage_app.py"
    if not source_manager.is_file():
        source_manager = release / "scripts/manage_app.py"
    atomic_write(manager, source_manager.read_text(encoding="utf-8"))
    wrapper = Path.home() / ".local/bin/nharong-cotu"
    atomic_write(wrapper, "#!/bin/sh\nexec " + shlex.join(
        [sys.executable, str(manager), "--root", str(root)]) + ' "$@"\n', 0o755)
    icon = root / "nharong-cotu.svg"
    atomic_write(icon, (release / "deploy/nharong-cotu.svg").read_text(encoding="utf-8"))
    # Desktop Exec is not a shell; escape its four reserved characters and %.
    executable = str(wrapper).replace("%", "%%")
    for char in ("\\", '"', "`", "$"):
        executable = executable.replace(char, "\\" + char)
    desktop = ("[Desktop Entry]\nType=Application\nName=Nhà Gươi\n"
               "Comment=Kể chuyện, RFID và chatbot Cơ Tu\n"
               f'Exec="{executable}" launch\nIcon={icon}\nTerminal=false\n'
               "Categories=Education;\nStartupNotify=false\n")
    apps = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "applications"
    atomic_write(apps / "nharong-cotu.desktop", desktop, 0o755)
    result = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True,
                            check=False) if shutil.which("xdg-user-dir") else None
    desktop_dir = Path(result.stdout.strip()) if result and result.returncode == 0 and result.stdout.strip() else Path.home() / "Desktop"
    if desktop_dir != Path.home():
        shortcut = desktop_dir / "nharong-cotu.desktop"
        atomic_write(shortcut, desktop, 0o755)
        if shutil.which("gio"):
            subprocess.run(["gio", "set", str(shortcut), "metadata::trusted", "true"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(apps)], check=False)


def rollback(root):
    with locked(root / "update.lock"):
        old, previous = selected(root), selected(root, "previous")
        if previous is None or old is None:
            raise ValueError("Chưa có bản trước để quay lại.")
        check_release(previous, root / "shared")
        switch_link(root, "current", previous)
        switch_link(root, "previous", old)
    print(f"Đã quay về v{previous.name}; mở lại app để dùng.")


def launch(root, args):
    with locked(root / "app.lock") as lock:
        release = selected(root)
        if release is None:
            raise ValueError("Chưa cài app. Dùng appctl update <gói.tar.gz>.")
        data = root / "shared"
        options = json.loads((data / "launch.json").read_text(encoding="utf-8")).get("args", [])
        if not isinstance(options, list) or any(not isinstance(item, str) for item in options):
            raise ValueError("launch.json cần args là danh sách chuỗi.")
        logs = root / "logs"
        logs.mkdir(exist_ok=True)
        log = logs / "app.log"
        if log.exists() and log.stat().st_size > 2 * 1024 * 1024:
            log.replace(logs / "app.previous.log")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"\n{datetime.now(timezone.utc).isoformat()} — v{release.name}\n")
            stream.flush()
            result = subprocess.run(["/bin/sh", str(release / "run_video.sh"), *options, *args],
                                    cwd=release, env=runtime_env(release, data),
                                    stdout=stream, stderr=stream, pass_fds=(lock.fileno(),))
        if result.returncode:
            raise RuntimeError(f"App thoát với mã {result.returncode}. Xem {log}")
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    builder = sub.add_parser("build", help="Đóng gói bản phát hành từ mã nguồn")
    builder.add_argument("version")
    builder.add_argument("--output", type=Path, default=SOURCE / "dist")
    updater = sub.add_parser("update", help="Cài/cập nhật từ gói và file .sha256 đi kèm")
    updater.add_argument("package", type=Path)
    updater.add_argument("--no-shortcuts", action="store_true")
    sub.add_parser("rollback", help="Quay lại bản trước")
    sub.add_parser("status", help="Xem phiên bản và đường dẫn dữ liệu")
    sub.add_parser("check", help="Kiểm tra bản đã cài, không mở thiết bị")
    launcher = sub.add_parser("launch", help="Mở app; thêm -- trước tham số app")
    launcher.add_argument("app_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    try:
        if args.command == "build":
            build(SOURCE, args.output.resolve(), args.version)
        elif args.command == "update":
            install(root, args.package, shortcuts=not args.no_shortcuts)
        elif args.command == "rollback":
            rollback(root)
        elif args.command == "status":
            print(json.dumps({"current": str(selected(root)), "previous": str(selected(root, "previous")),
                              "data": str(root / "shared"), "logs": str(root / "logs/app.log")}, indent=2))
        elif args.command == "check":
            release = selected(root)
            if release is None:
                raise ValueError("Chưa cài app.")
            check_release(release, root / "shared")
        elif args.command == "launch":
            extra = args.app_args[1:] if args.app_args[:1] == ["--"] else args.app_args
            return launch(root, extra)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, tarfile.TarError, KeyError) as error:
        message = f"Không thực hiện được: {error}"
        print(message, file=sys.stderr)
        if args.command == "launch" and (os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY")):
            try:
                import tkinter as tk
                from tkinter import messagebox
                window = tk.Tk()
                window.withdraw()
                messagebox.showerror("Nhà Gươi", message, parent=window)
                window.destroy()
            except Exception:
                pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
