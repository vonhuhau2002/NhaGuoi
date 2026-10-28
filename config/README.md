# Cấu hình phát triển

- `video_stories.json`: đường dẫn MP4/lời thoại/bộ hỏi đáp, mic, Whisper,
  ánh xạ nút GPIO và bật/mode chatbot.
- `rfid_cards.json`: UID đã gán cho sáu nhân vật, là cấu hình cục bộ không
  đưa lên GitHub. Sao chép `rfid_cards.example.json` khi cài máy mới, rồi
  gán thẻ trong Thiết lập.
- `tts_voices.json`: giọng và tốc độ đọc của từng nhân vật.
- `tts_output.json`: thiết bị loa được chọn.
- `chatbot/aliases.json`: thuật ngữ retrieval, đi theo phiên bản code.
- `chatbot/.env`: key và cấu hình Gemini riêng ở máy, không đưa vào gói.

Đường dẫn nội dung trong JSON tính từ **file cấu hình**, ví dụ
`../data/videos/person_5.mp4`. Các file JSON ở đây dùng khi chạy source.
App đã cài dùng bản riêng trong `~/.local/share/nharong-cotu/shared/`; cập nhật
không ghi đè cấu hình người dùng. Xem tài liệu triển khai trước khi thay đổi
định dạng các file này.
