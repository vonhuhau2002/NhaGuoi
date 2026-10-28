# Kiến trúc và quy ước tổ chức mã

## Trách nhiệm của các tầng

`app/` kết nối các tính năng và quản lý vòng đời cửa sổ/tiến trình. `ui/` dựng
widget và nhận thao tác. `features/` thực hiện từng chức năng cụ thể; `core/`
chứa tiện ích dùng chung. Module truyện, cấu hình và adapter thiết bị không
import cửa sổ chính. Không tải Whisper/ZeroTTS hoặc mở GPIO chỉ vì import module.

```text
                  app.desktop / app.story_reader
                     │        │          │
                     ▼        ▼          ▼
                    ui     features    app.media_worker
                              │          │
                              ▼          ▼
                            core       stt + video
```

| Tính năng | Vị trí mã | Trách nhiệm |
| --- | --- | --- |
| TTS | `features/tts/voices.py`, `output.py`, `service.py`, `worker.py` | Chọn giọng, loa, quản lý job và sinh/phát WAV |
| STT | `features/stt/microphone.py`, `transcriber.py` | Thu WAV và giữ Whisper để nhận dạng nhiều lượt |
| Chatbot | `features/chatbot/` | SQLite retrieval, gọi Gemini, trạng thái hội thoại và tích hợp panel |
| Truyện | `features/stories/` | Nhân vật, phiên kể, xác minh nguồn, khớp đáp án mẫu |
| Video | `features/video/content.py` | Đọc lời thoại, tải nội dung, cache kết quả nhận dạng |
| RFID | `features/rfid/reader.py`, `cards.py` | Lấy UID và lưu ánh xạ; không điều khiển UI |
| GPIO | `features/gpio/buttons.py` | Ánh xạ, chống dội, đưa sự kiện nút vào queue |

RFID/GPIO chỉ đẩy sự kiện; luồng giao diện chọn nhân vật. `app.media_worker`
phối hợp STT với nạp nội dung video qua queue và revision để bỏ kết quả cũ.
TTS giữ model trong worker riêng, tái sử dụng WAV. Luồng và chính sách dữ liệu
không đổi trong lần tái cấu trúc này.

## Đường dẫn và dữ liệu

Mọi đường dẫn chung được định nghĩa tại `src/cotu_app/core/paths.py`. Không
tính project root bằng số cấp `__file__` riêng trong từng tính năng. Tool chạy
độc lập được phép xác định root từ vị trí `tools/<nhóm>/<script>.py`.

Khi phát triển, cấu hình ở `config/`, nội dung ở `data/`, tài nguyên ở
`resources/`, cache ở `var/cache/`, file IPC của GPIO ở `var/run/`. File trong cấu hình được giải quyết tương
đối với file cấu hình, không phụ thuộc thư mục làm việc của Terminal.

Khi chạy bản đã cài, `NHARONG_DATA_DIR` chọn `shared/` và
`NHARONG_CHATBOT_ENV` chọn key riêng. Bố cục dữ liệu `shared/` của bản `1.0.0`
vẫn được hỗ trợ để nâng cấp/rollback mà không thay cấu hình hoặc nguồn tư liệu.
Corpus/index và alias chatbot thuộc từng release; video, thẻ, giọng, loa và key
là dữ liệu người dùng được giữ lại.

## Thêm tính năng và kiểm thử

Thêm mã nghiệp vụ trong `features/<tên>/`, đưa các thao tác UI vào `ui/` hoặc
panel riêng của tính năng và nối chúng tại `app/`. Không thêm một file
`app3.py`/`app4.py` mới làm bản sao ứng dụng chính. Thử nghiệm độc lập nằm trong
`examples/`; công cụ quản trị nằm trong `tools/`.

`tests/unit/` kiểm tra tính năng, `tests/integration/` kiểm tra phối hợp UI,
worker và phát hành. Chạy `./tools/test.sh -q`. Các test cần Tk dùng
`NHARONG_TEST_DISPLAY` và được bỏ qua khi chưa có màn hình thử. Kiểm thử logic
không gọi API, tải model hoặc mở thiết bị.

`pyproject.toml` là khai báo package/dependencies chung. Gói code Python chưa
thay thế gói app chứa cấu hình/tài nguyên/runtime; triển khai desktop dùng
`appctl`, theo [hướng dẫn phát hành](TRIEN_KHAI_APP_PI5.md).
