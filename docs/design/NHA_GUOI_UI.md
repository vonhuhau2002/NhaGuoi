# Giao diện Nhà Gươi trên Pi 5

## Mục tiêu và nguồn thiết kế

Tên hiển thị: **Nhà Gươi**; tính năng hội thoại: **Trò chuyện Nhà Gươi**. Đích
chính là màn hình cảm ứng ngang 800×480; cũng kiểm tra cửa sổ 1100×720. App
tiếp tục dùng Tkinter/libVLC và ảnh nhân vật hiện có để giữ chi phí chạy thấp.

Đã tìm hướng dẫn trên GitHub, đọc [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
và tham khảo [frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design).
Chọn/cài UI/UX Pro Max vì có hướng dẫn desktop, touch, contrast và hiệu năng.
Skill ở `~/.codex/skills/ui-ux-pro-max/`; không phải dependency của app.

Tìm kiếm `museum education touchscreen kiosk` phù hợp ở hướng flat/ít hiệu
ứng và tránh nút nhỏ, nhưng palette tối không hợp bối cảnh. Lần tìm hẹp hơn
`children storytelling nature` gợi xanh thiên nhiên; các đề xuất landing page
và Google Fonts không được áp dụng vào app Tk. Màu riêng, font DejaVu Sans
cài sẵn và layout kiosk được định nghĩa tại `src/cotu_app/ui/theme.py`.

## Bố cục và hành vi

- Header gọn: biểu tượng nhà, tên Nhà Gươi, mô tả văn hóa Cơ Tu và toàn màn hình.
- Bốn mục phía dưới: Nghe chuyện, Hỏi đáp, Trò chuyện, Thiết lập. Native button
  có nhãn, focus, trạng thái nhấn/chọn; chiều cao đo được 52 px ở màn hình thử.
- Nghe chuyện: sáu nhân vật ở bên trái, video bên phải, các điều khiển phát
  cố định phía dưới video. Chọn bằng cảm ứng, RFID và nút GPIO vẫn dùng chung.
- Hỏi đáp: ô hỏi, mic, danh sách gợi ý và vùng đáp án tách rõ. Danh sách dùng
  cách hỏi ngắn nhất **đã có trong aliases**, không tự tóm tắt hoặc đổi nguồn.
  Chọn vẫn phát nguyên văn đáp án của đúng nhân vật. Kéo danh sách không chọn
  nhầm một câu; scrollbar là phương án thay thế thao tác kéo.
- Hội thoại: dùng tên dự án thay tên nhà cung cấp. Gợi ý mở theo yêu cầu để
  dành diện tích cho hội thoại. Giữ cảnh báo tư liệu chưa duyệt và việc gửi
  câu hỏi tới Google; không hiển thị enum trạng thái hay thời gian API trong UI.
- Thiết lập: file, thẻ, mic và nạp nội dung ở góc thầy cô có thanh cuộn. Không
  để các thao tác quản trị chiếm hàng nút của màn hình hỏi đáp.
- Bàn phím Việt nằm trong cửa sổ, giữ ô nhập trên phím, tạm ẩn nội dung phụ;
  các nút hàng dưới và phím chữ được kiểm tra không tràn màn hình.

Màu, khoảng cách và native widget giữ thống nhất. Không thêm animation, tải
font mạng, trình duyệt hoặc model mới cho việc thay giao diện. Danh tính lưu
trữ `nharong-cotu`/package `cotu_app` giữ nguyên để tránh tách dữ liệu người dùng.

## Kiểm chứng và xem trước

Đã chạy bộ kiểm thử trên display ảo riêng 800×480, không mở RFID/GPIO/mic/loa
hoặc gọi API thật. Các ca gồm bàn phím tiếng Việt, hủy/đổi phiên chat, điều
hướng, kéo danh sách không chọn nhầm và cuộn đến cuối thiết lập. Kiểm tra
bàn phím ở cửa sổ 1100×720 nằm trong bộ test.

Ảnh chụp từ UI thật (dữ liệu mẫu, không gọi mô hình):

- [Nghe chuyện](../../reports/ui/nha-guoi-nghe-chuyen-800x480.png)
- [Hỏi đáp](../../reports/ui/nha-guoi-hoi-dap-800x480.png)
- [Trò chuyện](../../reports/ui/nha-guoi-tro-chuyen-800x480.png)
- [Bàn phím](../../reports/ui/nha-guoi-ban-phim-800x480.png)
- [Thiết lập](../../reports/ui/nha-guoi-thiet-lap-800x480.png)

Chạy source: `./run_video.sh --no-rfid`. Source mới chưa thay code release
`1.0.0` đang mở; biểu tượng và UI app đã cài đổi khi cài bản cập nhật.

## Vì sao bản app có thể đọc chậm lúc đầu?

Bản `1.0.0` có cache riêng ở `shared/.tts_cache`, còn source ở `var/cache/tts`.
Bộ cài ban đầu chưa mang WAV từ source sang app. `AudioEngine` còn đưa mtime
các file model vào fingerprint: đóng gói/giải nén tạo fingerprint khác dù
config model không đổi. Vì vậy app lần đầu phải tạo lại những câu source đã
có cache. Đây là nguyên nhân xác minh được về việc không dùng chung WAV;
không đủ để suy ra mọi trường hợp chậm đều có cùng nguyên nhân.

Đã kiểm tra cả hai vùng có 37/37 đáp án lưu WAV, fingerprint khác nhau. Worker
app đã ngừng sử dụng CPU ở lần lấy mẫu sau khi chuẩn bị xong. Một câu mới chưa
có WAV vẫn chờ tổng hợp toàn bộ câu trước khi phát; thiết kế này cũng có trong
bản Terminal. Giao diện không làm model nhanh hơn.

Chạy `.venv-video/bin/python tools/diagnostics/tts_cache.py` để lưu so sánh tại
`reports/tts/cache-check.json`. Số đo là lookup cache, không phải thời gian tới
tiếng đầu tiên hay độ trễ loa. Chưa thay thuật toán TTS trong lần thiết kế UI;
cần đo cùng một câu, giọng, trạng thái cache/model và loa trước khi so tốc độ.
