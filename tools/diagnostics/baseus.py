"""Kiểm tra Baseus BS-OH065 trên Linux, không cài driver hoặc ghi lệnh vào bút.

python3 tools/diagnostics/baseus.py            # chỉ xem USB/HID và ALSA
sudo python3 tools/diagnostics/baseus.py --capture  # phép thử có hướng dẫn tại Terminal
"""

import argparse
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import selectors
import sys
import time


VENDOR, PRODUCT = "fff1", "001a"
MAX_BYTES = 4 * 1024 * 1024


def read_text(path):
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def discover():
    usb = []
    for path in sorted(Path("/sys/bus/usb/devices").glob("*")):
        if (read_text(path / "idVendor"), read_text(path / "idProduct")) != (VENDOR, PRODUCT):
            continue
        interfaces = []
        for interface in sorted(path.glob(path.name + ":*")):
            interfaces.append({"name": interface.name,
                               "class": read_text(interface / "bInterfaceClass"),
                               "driver": (interface / "driver").resolve().name
                               if (interface / "driver").exists() else ""})
        usb.append({"port": path.name, "product": read_text(path / "product"),
                    "interfaces": interfaces})
    hid = []
    for path in sorted(Path("/sys/class/hidraw").glob("hidraw*")):
        fields = dict(line.split("=", 1) for line in read_text(path / "device/uevent").splitlines()
                      if "=" in line)
        identity = fields.get("HID_ID", "").split(":")
        if len(identity) != 3:
            continue
        if (int(identity[1], 16), int(identity[2], 16)) != (int(VENDOR, 16), int(PRODUCT, 16)):
            continue
        descriptor = path / "device/report_descriptor"
        hid.append({"node": str(Path("/dev") / path.name),
                    "name": fields.get("HID_NAME", ""), "physical": fields.get("HID_PHYS", ""),
                    "descriptor_hex": descriptor.read_bytes().hex()})
    return usb, hid


def inspect(usb, hid):
    print("Baseus BS-OH065 — đầu thu USB fff1:001a")
    if not usb:
        print("Chưa tìm thấy đầu thu fff1:001a. Kiểm tra kết nối USB.")
    for device in usb:
        print(f"USB {device['port']}: {device['product']}")
        for interface in device["interfaces"]:
            print(f"  {interface['name']}: class={interface['class']}, driver={interface['driver']}")
    for device in hid:
        node = Path(device["node"])
        permission = "đọc được" if os.access(node, os.R_OK) else "chưa có quyền đọc / chưa thấy trong môi trường này"
        print(f"  {node}: {device['physical']} — {permission}")
    pcm = read_text(Path("/proc/asound/pcm"))
    print("\nALSA:\n" + (pcm or "Không thấy PCM."))
    if "capture" not in pcm.lower():
        print("Chưa có đầu vào ALSA. HID có thể chứa dữ liệu riêng, chưa chứng minh có âm thanh.")
    return pcm


def collect_phase(selector, seconds, phase, packets, totals):
    # Loại bỏ gói chờ từ trước để không gán nhầm nút bấm sang giai đoạn kế tiếp.
    drain_until = time.monotonic() + 0.1
    while time.monotonic() < drain_until:
        ready = selector.select(timeout=0)
        if not ready:
            break
        for key, _ in ready:
            try:
                os.read(key.fd, 4096)
            except BlockingIOError:
                pass
    started = time.monotonic()
    deadline = started + seconds
    count = 0
    print(f"ĐANG ĐỌC {seconds} GIÂY — {phase}", flush=True)
    while time.monotonic() < deadline:
        for key, _ in selector.select(timeout=min(0.2, max(0, deadline - time.monotonic()))):
            try:
                data = os.read(key.fd, 4096)
            except BlockingIOError:
                continue
            if not data:
                raise OSError("Bút đã ngắt kết nối trong khi kiểm tra.")
            totals[0] += len(data)
            if totals[0] > MAX_BYTES:
                raise ValueError("Đã đạt giới hạn 4 MiB. Dừng thu dữ liệu.")
            packets.append({"phase": phase, "seconds": round(time.monotonic() - started, 4),
                            "node": key.data, "hex": data.hex()})
            count += 1
    print(f"Kết thúc {phase}: {count} gói.\n", flush=True)


def capture(hid, packets):
    if not hid:
        raise ValueError("Không tìm thấy cổng HID của đầu thu Baseus.")
    with selectors.DefaultSelector() as selector:
        try:
            for device in hid:
                node = device["node"]
                try:
                    fd = os.open(node, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
                except PermissionError:
                    raise PermissionError(
                        f"Không đọc được {node}. Chạy tại Terminal trên Pi:\n"
                        "sudo python3 tools/diagnostics/baseus.py --capture") from None
                try:
                    selector.register(fd, selectors.EVENT_READ, node)
                except BaseException:
                    os.close(fd)
                    raise
            print("\nPhép thử chỉ đọc cổng của bút Baseus, không đọc bàn phím khác.")
            print("Dữ liệu thô được lưu tại máy; chưa giải mã âm thanh và không gửi lên mạng.")
            print("Bật bút, đặt gần đầu thu. Dừng video để nghe hướng dẫn dễ hơn.")
            totals = [0]
            phases = [
                ("idle", 6, "Đặt bút nằm yên, không bấm nút."),
                ("mic_hold", 10, "Sau khi bắt đầu, NHẤN GIỮ nút mic và nói một câu thử, rồi thả nút."),
                ("mic_click", 10, "Sau khi bắt đầu, BẤM một lần nút mic, nói câu thử, rồi bấm lại để dừng."),
                ("page_next", 6, "Sau khi bắt đầu, bấm nút chuyển trang vài lần để kiểm tra tín hiệu điều khiển."),
            ]
            for phase, seconds, instructions in phases:
                input(f"{instructions}\nNhấn Enter để bắt đầu {seconds} giây: ")
                collect_phase(selector, seconds, phase, packets, totals)
        finally:
            for key in list(selector.get_map().values()):
                os.close(key.fd)


def save_report(report):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    folder = Path(__file__).resolve().parents[2] / "reports/diagnostics"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"baseus_capture_{stamp}.json"
    # Tạo mới, không theo symlink hoặc ghi đè file đã có khi chạy sudo.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        if os.geteuid() == 0 and os.environ.get("SUDO_UID", "").isdecimal() and os.environ.get("SUDO_GID", "").isdecimal():
            os.fchown(stream.fileno(), int(os.environ["SUDO_UID"]), int(os.environ["SUDO_GID"]))
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(f"\nĐã lưu báo cáo: {path}")
    counts = Counter((item["phase"], item["node"]) for item in report["packets"])
    for (phase, node), count in sorted(counts.items()):
        print(f"  {phase:12} {node}: {count} gói")
    print("Có gói HID chưa đủ kết luận có âm thanh; cần phân tích định dạng dữ liệu.")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true", help="Đọc dữ liệu HID với hướng dẫn bấm nút")
    args = parser.parse_args(argv)
    try:
        usb, hid = discover()
        pcm = inspect(usb, hid)
        if not args.capture:
            return 0 if usb else 1
        if not sys.stdin.isatty():
            print("Chạy --capture tại Terminal tương tác trên Pi để làm theo hướng dẫn.", file=sys.stderr)
            return 1
        report = {"model": "BS-OH065", "usb": usb, "hid": hid, "alsa_pcm": pcm, "packets": []}
        try:
            capture(hid, report["packets"])
        except (OSError, ValueError, KeyboardInterrupt, EOFError) as error:
            if report["packets"]:
                report["interrupted"] = str(error) or type(error).__name__
                save_report(report)
            raise
        save_report(report)
        return 0
    except (OSError, ValueError, KeyboardInterrupt, EOFError) as error:
        print(f"Chưa hoàn tất: {str(error) or type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
