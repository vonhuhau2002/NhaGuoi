# Công cụ phát triển và quản trị

Chạy các lệnh dưới đây từ thư mục gốc. Công cụ không được import bởi giao diện.

| Công cụ | Lệnh |
| --- | --- |
| Toàn bộ kiểm thử | `./tools/test.sh -q` |
| Phát hành, cài, rollback | `./appctl --help` |
| Chuẩn bị ghi chú nghiên cứu | `python3 tools/chatbot/prepare_research.py` |
| Thu thập nguồn từ manifest | `python3 tools/chatbot/collect_sources.py --help` |
| Nhập JSONL đã kiểm tra vào corpus | `python3 tools/chatbot/import_corpus.py` |
| Nhập TXT hỏi đáp, giữ nguyên nguồn | `python3 tools/stories/import_questions.py --help` |
| Tải/materialize model ZeroTTS | `.venv-video/bin/python tools/tts/install_model.py` |
| Kiểm tra USB/HID Baseus | `python3 tools/diagnostics/baseus.py --help` |
| Chụp UI mẫu trên display thử | `DISPLAY=:93 .venv-video/bin/python tools/diagnostics/preview_ui.py` |
| So sánh cache TTS, không mở loa | `.venv-video/bin/python tools/diagnostics/tts_cache.py` |
| Cài bộ gõ tiếng Việt trên Pi | `./tools/setup/install_vietnamese_input.sh` |

Lệnh thu thập nguồn/tải model dùng mạng khi được người phát triển chủ động
chạy. Báo cáo Baseus nằm trong `reports/diagnostics/`. Thu thập raw không đổi
trạng thái duyệt corpus; đọc tài liệu dữ liệu trước khi dựng lại index.
