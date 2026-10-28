# Các bản thử nghiệm ban đầu

Các file trong thư mục này được giữ để tham khảo lịch sử giao diện. App chính
không import chúng và bộ phát hành không đóng gói chúng.

| File cũ | File lưu lại |
| --- | --- |
| `nharong/app.py` | `basic_story_app.py` |
| `nharong/app1.py` | `story_app_v1.py` |
| `nharong/app2.py` | `illustrated_story_app.py` |
| `nharong/app_rfid.py` | `rfid_simulator.py` |
| `scripts/display_test.py` | `display_smoke.py` |
| `scripts/main.py` | `console_demo.py` |

Chạy app hiện hành bằng `./run_video.sh` hoặc `./run_rfid.sh` ở gốc dự án.
Nếu cần mở ví dụ, chạy từ gốc với `PYTHONPATH=src python3 examples/legacy/<file>.py`.
