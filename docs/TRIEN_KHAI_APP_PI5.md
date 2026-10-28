# Triển khai app trên Raspberry Pi 5

Người dùng mở **Nhà Gươi** từ Desktop hoặc menu. Lập trình viên sửa mã
trong dự án; chỉ thao tác `build → update` mới đưa code mới sang app đã cài.
Số phiên bản hiện trên tiêu đề. Không tự tải cập nhật qua mạng.

## Hai vùng độc lập

```text
/home/admin/NhaRongCoTu/                    # Source: src/config/data/resources/tools
  .venv-video/                            # Runtime/model của máy phát triển
  dist/                                   # Gói phát hành + file SHA256
~/.local/share/nharong-cotu/
  releases/1.0.0/                          # Bản cũ vẫn hoạt động độc lập
  releases/1.1.0/                          # Bản mới sau khi chủ động build/update
  current -> releases/<phiên bản>
  previous -> releases/<phiên bản trước>
  shared/                                 # Dữ liệu giữ qua cập nhật
    video_stories.json, rfid_cards.json
    tts_voices.json, tts_output.json
    videos/, docs/ hoặc stories/
    chatbot.env                            # Key riêng, quyền 600
    launch.json                            # Tham số mở app
    .tts_cache/ hoặc cache/tts/
    .video_cache/ hoặc cache/video/
  logs/app.log
~/.local/bin/nharong-cotu                   # Lệnh quản lý đã cài
```

App `1.0.0` hiện dùng mã cũ trong release riêng. Tái cấu trúc source không thay
app này. Bản mới dùng `src/cotu_app/`, vẫn đọc được cấu hình và đường dẫn
`shared/` cũ. Không di chuyển dữ liệu app đã cài theo cấu trúc source.

## Phát hành cấu trúc mới

Chạy bằng tài khoản desktop, không dùng sudo. Cần runtime/model đã chuẩn bị
trong [hướng dẫn video](HUONG_DAN_VIDEO.md).

```bash
cd /home/admin/NhaRongCoTu
./tools/test.sh -q
./appctl build 1.1.0
./appctl update dist/nharong-cotu-1.1.0-aarch64.tar.gz
./appctl status
```

Dùng tên gói thực tế được build in ra; kiến trúc lấy từ `platform.machine()`.
Không ghi đè phiên bản đã phát hành: các lần tiếp theo tăng số phiên bản.
Code, tài nguyên, corpus, adapter RFID và runtime/model được sao chép vào gói,
không symlink tới source/môi trường phát triển.

**Lần đầu nâng từ `1.0.0` sang cấu trúc mới dùng `./appctl` trong source.** Bộ
quản lý `1.0.0` đã cài chỉ hiểu gói cũ; bộ quản lý source hiểu cả hai. Sau cập
nhật, lệnh quản lý đã cài cũng nhận phiên bản mới. Vẫn hỗ trợ rollback `1.0.0`.

Giữ gói `.tar.gz` và `.tar.gz.sha256`. Bộ cài xác minh checksum, kiến trúc,
Python, OS; giải nén vào vùng tạm, kiểm tra cấu hình/thư viện/model/nguồn hỏi
đáp, dựng hai index trước khi chuyển `current`. Thất bại giữ bản đang dùng.
App đang mở tiếp tục chạy release đã chọn; code mới có hiệu lực sau mở lại.

## Cấu hình và nội dung người dùng

Cài đầu sao chép `config/` cùng `data/videos/`, `data/stories/` vào `shared/`,
đổi đường dẫn tương đối cho phù hợp. Cập nhật/rollback không ghi đè dữ liệu
này. Corpus/index và alias chatbot thuộc release; đóng gói không đổi cờ duyệt.

API key không nằm trong gói. Nếu cài đầu và muốn dùng key hiện có:

```bash
install -m 600 config/chatbot/.env "$HOME/.local/share/nharong-cotu/shared/chatbot.env"
```

App `1.0.0` đã cài có key riêng, không cần lệnh này khi chỉ cập nhật code.
Sửa `.env` phát triển không ảnh hưởng key của app đang dùng.

Muốn mở luôn với bốn nút GPIO, sửa `shared/launch.json`:

```json
{"args": ["--buttons"]}
```

Mặc định `args: []`; `--chatbot` mở thẳng tab chat. Thiết lập thẻ/loa/MP4 trong
app lưu vào `shared`; `./run_video.sh` dùng cấu hình source ở `config/`.

## Mở, kiểm tra và quay lại

```bash
"$HOME/.local/bin/nharong-cotu" launch
"$HOME/.local/bin/nharong-cotu" launch -- --no-rfid
./appctl check
./appctl rollback
tail -n 80 "$HOME/.local/share/nharong-cotu/logs/app.log"
```

Nếu Desktop yêu cầu, chuột phải biểu tượng chọn **Allow Launching**. App đã cài
chỉ mở một bản đồng thời. Bản phát triển và bản đã cài dùng chung phần cứng:
đóng bản đang dùng RFID/GPIO/mic/loa trước khi thử bản còn lại.

Rollback đổi code, không phục hồi `shared`. Thay đổi định dạng dữ liệu tương
lai cần sao lưu/migration tương thích. Lần tái cấu trúc này không đổi định dạng
cấu hình của app đã cài.

## Phạm vi bộ cài

Gói chứa runtime/model nên lớn, mỗi release dùng dung lượng riêng. Không tự
xóa bản cũ. Chỉ dọn bản không là `current`/`previous` và không đang chạy. Gói
cần cùng kiến trúc, Python major/minor và OS với máy build; vẫn dùng Python
hệ thống, Tk, VLC và các thư viện GPIO/SPI của OS.

Checksum phát hiện hỏng file, không phải chữ ký nhà phát hành. `check` không
quét thẻ, mở GPIO/mic/loa hay gọi Gemini. Sau phát hành cần thử thiết bị thật.
Wheel từ `pyproject.toml` chỉ chứa mã Python; triển khai đầy đủ dùng `appctl`.

## Giọng đọc liền mạch trong Trò chuyện

Từ `1.1.3`, app nạp trước ZeroTTS ở tiến trình nền ngay khi mở cửa sổ.
Khi gửi câu hỏi, app dùng lại lượt chuẩn bị đó trong lúc chờ dịch vụ trả lời.
Từ `1.1.5`, sau khi nhận câu trả lời hoàn chỉnh và kiểm tra nguồn, app tạo
xong WAV rồi nạp và chuẩn hóa toàn bộ âm thanh trong RAM trước khi mở loa.
Loa đọc liên tục từ bộ đệm đã sẵn sàng, với bộ đệm PortAudio `latency=high`.
Lúc đang tạo giọng, chân trang hiển thị tiến độ thay vì báo đang đọc.
Nghe lại dùng WAV có sẵn; hủy câu không lưu WAV dở dang. Các yêu cầu cũ có
`stream=true` cũng đi qua bước chờ WAV đầy đủ để không tái phát lỗi.

Phép đo cũ ở `1.1.2–1.1.4` ghi nhận âm thanh đầu sau 0,749 giây nhưng cần
hơn 17 giây để tạo khoảng 7,8 giây lời nói. Phát ngay từng mẩu làm loa hết
dữ liệu giữa chừng. Số đo âm thanh đầu đó không chứng minh giọng đọc lưu
loát, nên không còn dùng làm tiêu chí tối ưu. Bản `1.1.5` ưu tiên đọc trọn
lời đáp không đứt quãng; câu mới cần chờ tạo giọng, câu đã lưu phát lại ngay.
Việc nạp model lần đầu từ SD vẫn chạy nền và cũng có thể làm câu đầu chậm.
Đo mới kiểm tra cả thời gian chuẩn bị, thời lượng phát và số lần loa thiếu
dữ liệu trong [báo cáo độ liền mạch](../reports/tts/chat-fluency.json).

Có thể đo lại mà không gọi API chatbot. Đóng app trước để chỉ chạy một model:

```bash
PYTHONPATH=src .venv-video/bin/python tools/diagnostics/chat_latency.py \
  --play --output reports/tts/chat-fluency.json
```

Phép đo dùng model đã nạp, nội dung/giọng/nhịp cố định, cùng hạt giống ngẫu
nhiên và cache riêng rỗng. `--play` chạy một câu chưa có cache qua worker và
loa thật, xác nhận WAV đã hoàn tất trước khi mở loa, ghi số underflow và
khoảng cách giữa các lần ghi âm thanh. Bỏ tùy chọn đó nếu chỉ đo tạo WAV.

## Trả lời bằng dữ liệu có sẵn từ 1.1.6

Tab Trò chuyện ưu tiên bộ hỏi đáp đã kiểm tra nguồn. Khi khớp câu/alias,
app trả một đáp án và phát nguyên văn bằng giọng chủ câu hỏi, dùng lại WAV
trong `shared/.tts_cache`. Câu chưa khớp tiếp tục qua AI. Không cần nạp nội
dung video hoặc nhận dạng lời thoại trước để dùng nhánh tra câu hỏi này.
Nguồn sai SHA256 bị bỏ qua và ghi log; thay nguồn trong Thiết lập sẽ nạp
lại bộ tra. Cache WAV giữ nguyên qua cập nhật.

[Báo cáo kiểm tra bản cài](../reports/tts/curated-chat.json): 37/37 WAV,
233 cách hỏi trên sáu nhân vật, không gọi API hoặc nạp model trong nhánh
có sẵn. Câu “Nhà Gươl là gì?” gửi âm thanh đầu ra USB sau 0,251 giây và
phát hoàn tất không underflow. Phép đo không tính mở app, IPC hoặc trễ loa;
không áp dụng số này cho câu AI chưa có WAV. Chi tiết trong
[luồng hỏi đáp và giọng đọc](chatbot/LUONG_HOI_DAP_VA_GIONG_DOC.md).

Từ `1.1.7`, bộ tra nhận thêm các mẫu diễn đạt tương đương như “nhà guol
là cái gì”, “Gươl được hiểu là gì”, “công dụng của Gươl là gì” và “Chim
Tring có ý nghĩa gì”. Quy tắc chạy trên Pi, không cần tải model khác hoặc
đổi bộ hỏi đáp/WAV trong shared. Câu đổi ý, thiếu chi tiết phù hợp hoặc
không nằm trong các mẫu nhận diện vẫn dùng luồng chatbot thông thường.
