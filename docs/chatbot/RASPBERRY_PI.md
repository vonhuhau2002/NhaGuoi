# Vận hành trên Raspberry Pi 5

Chạy `./run_chatbot.sh doctor` trước: kiểm tra Python, ARM64, SQLite FTS5, Tkinter, màn hình, key có cấu hình hay chưa; không in key và không gọi mạng. Toàn bộ bản văn bản dùng thư viện chuẩn. Trên Raspberry Pi OS, nếu thiếu Tkinter, cài gói hệ điều hành `python3-tk`; CLI không cần gói này. Không cài Torch/transformers vào `.venv-video` để chạy chatbot này.

Chạy từ terminal desktop để mở `./run_chatbot.sh desktop --mode research`. SSH không có DISPLAY dùng `ask` hoặc `chat`; thông báo không mở được Tk không phải lỗi Gemini. Nếu UI thử nghiệm được dùng cùng video, theo dõi cả hai tiến trình: bộ nhớ UI/video/STT/TTS hiện có vẫn chiếm RAM dù chatbot không có LLM local.

Ưu tiên kiểm tra theo thứ tự:

1. Offline: dựng index, hỏi nguồn, chạy evaluate. Không cần mạng hoặc key.
2. API: đặt key Free Tier trong `config/chatbot/.env`, chạy một câu CLI, kiểm tra notice/status/citations và quota AI Studio.
3. Desktop: chạy `./run_video.sh --chatbot` hoặc `./run_rfid.sh --chatbot` từ dự án chính; thử câu dài, Dừng khi chờ mạng, Phiên mới, đổi nhân vật, mạng mất, key lỗi. Tab chatbot đã tích hợp, dùng bàn phím cảm ứng và giọng đọc hiện có.
4. Chạy cùng video 30 phút; theo dõi MemAvailable, swap-in/out, CPU/nhiệt/throttling và cảm giác chạm/gõ để đánh giá độ mượt toàn chuỗi.

```bash
free -h
vmstat 1
vcgencmd measure_temp
vcgencmd get_throttled
```

Không dựng index, OCR, tải dữ liệu hoặc tạo sẵn toàn bộ TTS khi khách đang hỏi. Bản hiện tại không làm những việc đó tự động. Cache chỉ ở RAM, hết khi đóng app. Một tiến trình cho kiosk giúp tránh nhiều cửa sổ đồng thời ăn chung quota; giới hạn cục bộ không phối hợp giữa các tiến trình.

`config/chatbot/.env.example` có timeout socket 15 s, deadline 35 s và khoảng cách API 6 s. Có thể tăng khoảng cách theo quota thực tế; không giảm rồi coi là đã tăng quota. Khi model thay đổi, kiểm tra Free Tier, vòng đời và khả năng JSON/thinking; đặt thinking `auto` để không gửi cấu hình thinking nếu model mới cần chế độ khác. Không tự chuyển model khi 404/429.

Đã thử API `gemini-3.1-flash-lite` qua CLI và qua khung chat nhúng trong VideoApp: mỗi lượt hoàn tất khoảng 8,5 giây; chưa đủ mẫu để kết luận p95 mạng/API. Đã kiểm tra widget/bàn phím ở 800×480 trong cửa sổ đầy đủ trên desktop Pi. Độ mượt chỉ mục offline không chứng minh video+UI+API+âm thanh cùng chạy đạt mục tiêu. Nút Đọc trả lời dùng chung tiến trình ZeroTTS hiện có; mic dùng luồng nhận dạng của video. Chưa đo toàn chuỗi bằng mic/loa thật trong đợt tích hợp này.
