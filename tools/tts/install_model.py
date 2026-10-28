"""Tải ZeroTTS rồi materialize các ONNX file để chạy trên Raspberry Pi."""

from pathlib import Path
import shutil

from zerotts.hub import load_config, resolve_model_dir


def main():
    base = Path(__file__).resolve().parents[2]
    models = base / ".venv-video" / "models"
    source = resolve_model_dir(cache_dir=str(models / "hub"))
    target = models / "zerotts"
    shutil.copytree(source, target, symlinks=False, dirs_exist_ok=True)
    load_config(target)
    print(f"ZeroTTS sẵn sàng: {target}")


if __name__ == "__main__":
    main()
