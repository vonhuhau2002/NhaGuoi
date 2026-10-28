# Nhà Gươi

Ứng dụng desktop Python/Tkinter cho Raspberry Pi 5: kể chuyện bằng video hoặc
văn bản, chọn nhân vật qua RFID/nút GPIO, hỏi đáp, nhận dạng giọng nói và đọc
tiếng Việt. Chatbot ưu tiên đáp án có sẵn, nhận diện các cách hỏi tương đương
và phát WAV đã lưu; câu chưa khớp mới tìm tư liệu bằng SQLite và gọi dịch vụ
AI khi có mạng và key.

Giao diện cảm ứng mới mang tên **Nhà Gươi**; khung hội thoại là **Trò chuyện Nhà Gươi**.
Xem [thiết kế, ảnh chụp và ghi nhận độ trễ TTS](docs/design/NHA_GUOI_UI.md).

## Chạy để phát triển

Chuẩn bị trên Raspberry Pi OS/Debian 64 bit:

```bash
sudo apt update
sudo apt install git vlc libvlc5 libportaudio2 python3-venv python3-tk
git clone https://github.com/vonhuhau2002/NhaGuoi.git
cd NhaGuoi
python3 -m venv --system-site-packages .venv-video
.venv-video/bin/python -m pip install -r requirements-video.txt
cp config/rfid_cards.example.json config/rfid_cards.json
cp config/chatbot/.env.example config/chatbot/.env
.venv-video/bin/python tools/tts/install_model.py
```

Điền API key trong `config/chatbot/.env` nếu cần dùng nhánh AI. File này và
UID thẻ thật được Git bỏ qua. Model, môi trường Python, cache và gói cài
không lưu trong kho mã nguồn. Video mẫu, bộ hỏi đáp và tài nguyên giao diện
được giữ trong dự án; gán thẻ RFID tại Thiết lập trên máy đang sử dụng.
Xem [hướng dẫn phần cứng và model](docs/HUONG_DAN_VIDEO.md) để cài SPI/GPIO
và cấu hình mic/loa trên Pi.

Từ thư mục gốc dự án, với môi trường `.venv-video` đã cài:

```bash
./run_video.sh                 # App chính: video, RFID, hỏi đáp, chatbot
./run_video.sh --no-rfid        # Thử giao diện không mở đầu đọc
./run_rfid.sh                  # Giao diện kể truyện chữ
./run_chatbot.sh doctor        # Kiểm tra chatbot, không gọi API
./run_chatbot.sh ask --mode research --offline "Gươl dùng để làm gì?"
./tools/test.sh -q             # Toàn bộ kiểm thử unit và integration
```

Các lệnh chạy tự đưa `src/` vào đường dẫn Python. Nếu chạy trực tiếp một module
bằng Python/IDE, đặt `PYTHONPATH=src`. Cài lại thư viện theo
[hướng dẫn video](docs/HUONG_DAN_VIDEO.md); dependencies được khai báo trong
`pyproject.toml`, `requirements-video.txt` dùng nhóm `desktop` của khai báo này.

## Cấu trúc dự án

```text
src/cotu_app/
  app/                    Điều phối cửa sổ chính, truyện chữ và worker nền
  core/                   Đường dẫn, cấu hình, JSON, chuẩn hóa văn bản
  features/
    chatbot/              Retrieval, Gemini, hội thoại và khung chat
    tts/                  Văn bản → giọng nói: voice, speaker, service, worker
    stt/                  Mic → WAV → văn bản: capture và Whisper
    stories/              Nhân vật, phiên kể, bộ câu hỏi và đáp án đã duyệt
    video/                Lời thoại, nạp nội dung MP4 và cache kết quả
    rfid/                 Đầu đọc MFRC522 và ánh xạ UID
    gpio/                 Bốn nút chọn truyện
  ui/                     Bố cục video, bàn phím cảm ứng
config/                   Cấu hình ứng dụng, giọng, loa, thẻ và Gemini .env
data/                     Video, tư liệu truyện và pipeline dữ liệu chatbot
resources/                Hình ảnh đóng gói cùng app
tools/                    Công cụ dữ liệu, cài đặt, chẩn đoán và phát hành
tests/                    unit/ theo tính năng; integration/ kiểm tra phối hợp
docs/                     Hướng dẫn và kiến trúc
reports/                  Báo cáo kiểm chứng và kết quả đo
examples/legacy/          Các giao diện thử nghiệm đời đầu, không dùng khi chạy app
vendor/                   Adapter RFID cho Pi và giấy phép đi kèm
var/                      Cache và file IPC phát sinh, không đóng gói
dist/                     Gói phát hành, không chỉnh sửa trực tiếp
.venv-video/              Môi trường Python và model của máy phát triển
```

`nharong/` trước đây chứa cả cửa sổ, TTS, STT và phần cứng. Toàn bộ mã đang dùng
đã chuyển sang các module trên. Tên sản phẩm **Nhà Gươi** và lệnh mở app
giữ nguyên; tên package dùng chung là `cotu_app`.

## Cấu hình và dữ liệu

- Cấu hình chính: `config/video_stories.json`; đường dẫn nội dung tính từ thư
  mục chứa file cấu hình, ví dụ `../data/videos/person_5.mp4`.
- API key phát triển: `config/chatbot/.env`, dựa trên `.env.example`; không
  đóng gói key vào bản phát hành.
- Truyện TXT và bộ hỏi đáp có nguồn: `data/stories/`; video/phụ đề/bộ hỏi đáp
  theo video: `data/videos/`. Kiểm tra SHA256 của nguồn vẫn được giữ nguyên.
- Dữ liệu chatbot: `data/chatbot/{raw,manifests,clean,corpus,index,evaluation}`.
  `research` vẫn là tư liệu thử nghiệm; chỉ dùng `approved` sau khi duyệt nguồn.

## App đã cài và bản phát hành

App đã cài nằm ở `~/.local/share/nharong-cotu/`, độc lập với mã nguồn này.
Phiên bản mã nguồn hiện tại là `1.1.7`. Sửa code hoặc cập nhật Git không tự
thay đổi app đã cài; tính năng mới chỉ có sau khi phát hành và cập nhật app.
Khi chuẩn bị một phiên bản mới, cập nhật số phiên bản trong `pyproject.toml`
rồi chạy (ví dụ `1.1.8`):

```bash
./tools/test.sh -q
./appctl build 1.1.8
./appctl update dist/nharong-cotu-1.1.8-aarch64.tar.gz
```

Lần đầu nâng từ cấu trúc `1.0.0` sang `1.1.0`, dùng **`./appctl` trong dự án**
để có bộ quản lý hiểu cả hai định dạng gói. Bộ quản lý mới vẫn hỗ trợ kiểm tra
và quay về bản `1.0.0`; không tự di chuyển dữ liệu người dùng đã cài.

Xem [kiến trúc](docs/ARCHITECTURE.md), [triển khai và cập nhật](docs/TRIEN_KHAI_APP_PI5.md),
[RFID](docs/HUONG_DAN_RFID.md) và [chatbot](docs/chatbot/README.md).
