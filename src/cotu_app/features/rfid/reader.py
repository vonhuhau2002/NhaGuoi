"""MFRC522 adapter and hardware event loop; no UI imports."""
import sys
import time
from cotu_app.core.paths import BASE

RFID_SOURCE = BASE / "vendor"

def import_rfid_reader():
    """Ưu tiên bản thư viện cục bộ đã dùng để thử đầu đọc trên Pi."""
    if (RFID_SOURCE / "mfrc522" / "__init__.py").is_file():
        source = str(RFID_SOURCE)
        if source not in sys.path:
            sys.path.insert(0, source)
    try:
        from mfrc522 import SimpleMFRC522
    except ModuleNotFoundError as error:
        raise RuntimeError(
            f"Python {sys.executable} thiếu module {error.name}. "
            f"Thư mục nguồn RFID được kiểm tra: {RFID_SOURCE}. "
            "Hãy chạy bằng môi trường Python đã chạy thành công test_rfid.py."
        ) from error
    return SimpleMFRC522


def reader_process(events, stop):
    """Tiến trình riêng để việc chờ thẻ không chặn giao diện hoặc lúc thoát."""
    try:
        SimpleMFRC522 = import_rfid_reader()
        reader = SimpleMFRC522()
        events.put(("ready", "Đầu đọc đã sẵn sàng."))
        last_uid, last_seen = None, 0.0
        while not stop.is_set():
            # Bản thư viện của dự án có hàm này: chỉ lấy UID, không cần đọc bộ nhớ thẻ.
            if hasattr(reader, "_read_id_no_block"):
                uid = reader._read_id_no_block()
            else:
                uid, _ = reader.read()
            now = time.monotonic()
            if uid is not None:
                uid = str(uid)
                if uid != last_uid or now - last_seen > 1.2:
                    events.put(("uid", uid))
                last_uid, last_seen = uid, now
            stop.wait(0.15)
    except Exception as error:
        events.put(("error", f"{type(error).__name__}: {error}"))
