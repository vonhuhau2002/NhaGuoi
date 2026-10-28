# Sử dụng RFID và hỏi Già làng

Chạy trên Raspberry Pi:

```bash
cd /home/admin/NhaRongCoTu
./run_rfid.sh
```

## Giao diện màn hình 7 inch

- **Nghe truyện:** quét thẻ đã gán để mở truyện, đọc lại hoặc dừng. Hai nút mũi tên cuộn nội dung. Có ảnh minh họa người kể và khung nội dung.
- **Gán thẻ:** chọn một trong sáu nhân vật, bấm Gán thẻ đã chọn rồi đưa thẻ vào đầu đọc. UID lưu trong `config/rfid_cards.json` trong thư mục cấu hình. Chuyển sang mục khác sẽ hủy lần gán đang chờ.
- **Già làng kể:** chạm tên một nhân vật để Già làng kể truyện của người đó.
- **Hỏi đáp:** sau khi Già làng kể xong, chạm Hỏi thêm, rồi chọn một câu hỏi để xem và nghe giải thích. Có nút đọc lại câu trả lời, dừng và cuộn nội dung.

Nhân vật phụ chỉ kể chuyện. Khi đổi sang nhân vật hoặc truyện khác, phần hỏi đáp của truyện trước được xóa. Dừng giọng đọc giữa chừng không được tính là kể xong; có thể bấm Đọc lại để nghe hết truyện.

Nếu không có giọng đọc hoặc đã tắt Tự đọc khi quét, có thể đọc bằng mắt rồi bấm Đã đọc xong để mở hỏi đáp cho truyện do Già làng kể.

Giọng kể dùng ZeroTTS tiếng Việt, cố định qua các lần mở: Già làng dùng Hữu Đức
(nam lớn tuổi), người dệt vải dùng Kim Oanh (nữ trung niên), người kể chuyện
dùng Mai Chi (nữ trẻ); người giữ lửa/dẫn đường/làm nhạc cụ lần lượt dùng
Gia Huy/Quang Minh/Tiến Đạt. Model giữ trong một tiến trình, không nạp lại
khi đổi giọng. Truyện/đáp án đã tạo được lưu ở `var/cache/tts/` để phát lại. Cấu hình ở
`config/tts_voices.json`; ngõ ra loa ở `config/tts_output.json` (mặc định USB Audio Device).
Xem phần cài ZeroTTS và kiểm tra loa trong `docs/HUONG_DAN_VIDEO.md`.

## Nội dung và tài nguyên

- Hỏi đáp truyện mẫu gồm 15 câu có sẵn, 3 câu mỗi truyện, chạy ngoại tuyến.
  Câu hỏi tự do nhập tại tab Chatbot Gemini; nhận giọng nói chỉ có trong app video.
- Sửa câu hỏi và lời giải thích ở `src/cotu_app/features/stories/sample_questions.py`. Khi đổi nội dung truyện trong `src/cotu_app/features/stories/characters.py`, cần duyệt lại câu hỏi cho khớp.
- Bộ sáu hình AI nằm ở `resources/images/village_characters.png`, thông tin tạo ảnh trong `resources/images/README.md`.
- Các truyện và lời giải thích là nội dung mẫu cần người phụ trách duyệt trước khi giảng dạy.
- Giữ thư mục `src/`, `resources/`, `config/` và `data/` khi chuyển ứng dụng sang máy khác.

## Kiểm tra

```bash
./tools/test.sh -v
./run_rfid.sh --check-rfid
```

Các kiểm tra tự động không mở màn hình hoặc thiết bị RFID. Cần kiểm tra trực tiếp trên Pi: hình hiển thị đúng nhân vật, các nút vừa màn hình 800×480, âm thanh, quét thẻ, hỏi đáp sau khi đọc xong và đổi thẻ khi đang trả lời.
