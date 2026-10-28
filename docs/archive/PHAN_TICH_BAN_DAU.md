> Tài liệu phân tích lịch sử trước khi tích hợp video/chatbot và tái cấu trúc.
> Cấu trúc hiện tại: [README](../../README.md), [kiến trúc](../ARCHITECTURE.md).
> UID trong tài liệu đã đổi sang số minh họa; cấu hình thẻ thật không đưa lên GitHub.

# Phân tích dự án STEM Nhà Rông Cơ Tu

Ngày ghi nhận: 15/10/2026.

Tài liệu ghi lại kết quả đọc mã nguồn và kế hoạch phát triển. Chưa chạy kiểm thử giao diện hoặc phần cứng RFID trong phiên phân tích. Không thay đổi các file Python hiện có.

## 1. Mục tiêu

- Có 1 Già làng và 5 nhân vật phụ, nhận diện bằng 6 thẻ RFID.
- Mỗi nhân vật phụ có câu chuyện riêng; nhận diện đúng nhân vật phải hiển thị đúng truyện.
- Già làng có thể kể chuyện của các nhân vật.
- Có thể mở rộng âm thanh và video.

## 2. Cấu trúc dự án đã đọc

Mã nguồn hiện được tổ chức trong `nharong/`, kiểm thử trong `tests/`, công cụ
trong `scripts/` và tài liệu trong `docs/`.

| File | Vai trò xác nhận từ code |
| --- | --- |
| `main.py` | Chỉ in 3 dòng giới thiệu, không mở giao diện hoặc gọi các file khác. |
| `display_test.py` | Kiểm tra cửa sổ Tkinter 800×480, lời chào cố định. |
| `app.py` | Giao diện 5 nhân vật, chọn và hiển thị truyện, chưa phát âm thanh. |
| `app1.py` | Giao diện 5 nhân vật, có đọc tiếng Việt bằng `espeak-ng`. |
| `app2.py` | Giao diện có khung truyện cuộn, đọc/dừng tiếng nói, dùng `espeak-ng` hoặc phương án `pyttsx3`. |

Ba file `app.py`, `app1.py`, `app2.py` chạy độc lập, mỗi file có phần tạo cửa sổ và gọi `mainloop()`. Chưa có điểm khởi chạy chung. Không thể kết luận `main.py` là chương trình giao diện chỉ dựa vào tên file.

Đề xuất dùng `app2.py` làm cơ sở phát triển vì có nhiều chức năng nhất. Đây là đề xuất, chưa phải quyết định thay đổi chương trình khởi chạy. Cần xác nhận file thực tế được chạy trên Raspberry Pi qua terminal, IDE hoặc cơ chế tự khởi động.

Các file bên ngoài dự án đã đọc để đối chiếu RFID:

- `/home/admin/mfrc522/test_rfid.py`
- `/home/admin/mfrc522_test/src/mfrc522/SimpleMFRC522.py`

## 3. Kiến trúc hiện tại

Mỗi bản giao diện chứa dữ liệu và xử lý trong cùng một file:

- `CHARACTERS`: danh sách 5 nhân vật với tên, vai trò, màu và truyện riêng.
- `NhaRongApp`: tạo giao diện, giữ trạng thái `self.selected`, cập nhật truyện và điều khiển giọng đọc nếu có.
- Tkinter xử lý thao tác qua vòng lặp sự kiện.

Luồng chọn nhân vật trong `app2.py`:

```text
Bấm nút nhân vật
→ select_character(index)
→ dừng giọng đọc cũ
→ cập nhật self.selected
→ lấy CHARACTERS[index]
→ cập nhật tiêu đề và nội dung bằng set_story()
```

`read_story()` lấy truyện theo `self.selected` khi bấm nghe kể chuyện.

### Khoảng cách so với mục tiêu

- Già làng hiện chỉ xuất hiện ở lời chào, tương ứng `self.selected = None`; chưa có bản ghi nhân vật thứ sáu.
- Chưa có cơ chế riêng để Già làng lựa chọn kể chuyện của nhân vật khác.
- Các truyện hiện là nội dung mẫu; cần xác minh nội dung văn hóa trước khi sử dụng chính thức.
- Âm thanh tổng hợp đã có ở `app1.py` và `app2.py`, nhưng chưa xác nhận hoạt động trên Pi trong phiên này.
- Chưa có video, bảng ánh xạ UID hoặc kết nối RFID trong các file ứng dụng.

## 4. Phân tích hiện tượng chọn nhân vật nhưng truyện không đổi

### Đã xác nhận từ code

Chưa tìm thấy lỗi trực tiếp giải thích hiện tượng đã từng gặp:

- Các callback giữ chỉ số bằng tham số mặc định (`lambda i=index` hoặc `lambda n=i`), không thấy lỗi mọi nút cùng dùng chỉ số cuối.
- Các hàm chọn đều lấy truyện theo chỉ số và cập nhật widget nội dung.
- Năm truyện trong từng danh sách có nội dung khác nhau.
- `app2.py:set_story()` chuyển `Text` sang `normal`, xóa nội dung cũ, chèn nội dung mới, chuyển lại `disabled` và cuộn về đầu.

### Các giả thuyết cần kiểm tra

| Giả thuyết | Cách kiểm tra |
| --- | --- |
| Chạy nhầm file hoặc bản sao cũ | Ghi lại lệnh khởi chạy và đường dẫn tuyệt đối của file đang chạy. |
| Chạy `display_test.py` | File này chỉ có lời chào cố định, không có chức năng chọn truyện. |
| Callback gặp ngoại lệ trước khi cập nhật truyện | Quan sát traceback ở terminal lúc bấm, đặc biệt bước dừng âm thanh. |
| Màn hình đã đổi nhưng âm thanh vẫn cũ | Kiểm tra riêng văn bản và giọng đọc; xem xét luồng nền `pyttsx3` nếu nhánh này được sử dụng. |
| Lỗi thuộc bản mã trước | Tái hiện trên đúng bản đang vận hành trước khi sửa. |

Không coi các giả thuyết trên là nguyên nhân đã được chứng minh. Ưu tiên tái hiện bằng nút bấm trước khi tích hợp RFID.

## 5. Tình trạng RFID và điểm tích hợp

### Thông tin do người phát triển cung cấp

- Raspberry Pi 5 đã đọc được UID `1001`.
- Thư viện `mfrc522` đã cài và import thành công trên Pi.

Các thông tin này chưa được kiểm tra lại bằng phần cứng trong phiên phân tích. Chưa biết UID trên thuộc nhân vật nào; chưa có đủ 6 UID.

### Đã xác nhận từ file đã đọc

- `test_rfid.py` tạo `SimpleMFRC522`, gọi `reader.read()` để lấy UID và dữ liệu thẻ.
- Script chỉ in khi UID khác `last_uid`. Rút và quét lại cùng thẻ sẽ không in thông báo mới nếu chưa đọc thẻ khác.
- Trong bản nguồn `SimpleMFRC522.py` đã đọc, `read()` có vòng lặp chờ đọc được thẻ. Gọi trực tiếp trên luồng giao diện có thể làm đứng giao diện.
- Chưa xác nhận Python trên Pi thực sự import thư viện từ thư mục nguồn này; cần đối chiếu đường dẫn module đang được nạp.

### Phương án tích hợp đề xuất

Dùng `app2.py:select_character(index)` làm điểm cập nhật chung cho nút bấm và RFID. Hàm này đã có chú thích dành cho tích hợp RFID.

```text
Đầu đọc RFID ở luồng nền
→ UID
→ hàng đợi sự kiện
→ luồng Tkinter kiểm tra bằng root.after()
→ tra bảng UID → nhân vật
→ select_character(index) hoặc xử lý Già làng
```

- Chỉ cập nhật widget trên luồng Tkinter chính.
- Dùng UID để tra truyện trong ứng dụng; không cần lưu truyện trên thẻ.
- Thống nhất kiểu dữ liệu UID giữa đầu đọc và bảng ánh xạ.
- Bổ sung phản hồi cho thẻ chưa đăng ký và quy tắc chống đọc lặp, quét lại cùng thẻ.
- Thiết kế dừng bộ đọc khi đóng cửa sổ; tránh để việc chờ thẻ ngăn ứng dụng thoát.
- Thẻ Già làng có thể tạm gọi `show_welcome()`, nhưng như vậy chỉ đáp ứng lời chào, chưa đủ chức năng kể thay nhân vật khác.

## 6. Kế hoạch thực hiện từng bước nhỏ

1. **Xác nhận chương trình đang chạy trên Pi.** Ghi lệnh, đường dẫn file và môi trường Python. Chọn bản nền để tiếp tục phát triển.
2. **Tái hiện lỗi bằng nút bấm.** Chọn lần lượt 5 nhân vật, chọn ngược lại và chuyển nhanh; đối chiếu tiêu đề, truyện, trạng thái chọn và traceback.
3. **Sửa đúng lỗi đã xác định.** Nếu cần, thêm log tạm cho chỉ số nhân vật và nội dung truyện. Chưa tích hợp RFID ở bước này.
4. **Bổ sung định danh cho 6 nhân vật.** Quy định rõ hành vi của thẻ Già làng và cách lựa chọn truyện để Già làng kể. Tách người kể với truyện được chọn nếu cần.
5. **Thu đủ 6 UID và lập bảng ánh xạ.** Gắn từng thẻ với đúng nhân vật, không tự gán UID đã biết khi chưa có thông tin.
6. **Tích hợp RFID qua luồng chọn hiện có.** Thêm luồng đọc nền, hàng đợi, xử lý thẻ lạ, chống lặp và dừng khi đóng ứng dụng.
7. **Kiểm tra trên Raspberry Pi 5.** Thử đổi thẻ, giữ thẻ, rút và quét lại cùng thẻ, thẻ lạ, mất kết nối đầu đọc và đóng cửa sổ khi chờ thẻ. Giao diện phải còn phản hồi.
8. **Hoàn thiện âm thanh rồi mở rộng video.** Xác nhận thiết bị phát âm thanh, đọc đúng truyện và dừng nội dung cũ khi chuyển nhân vật; sau đó mới thêm phát video.

Mỗi bước chỉ triển khai sau khi kết quả bước trước đã rõ. Giữ nguyên các file hiện có khi tạo bản phát triển mới; không cần viết lại toàn bộ ứng dụng hoặc thay đổi cấu trúc dự án để bắt đầu.

## 7. Phạm vi hiện được chọn

Người phát triển chọn phương án C: chỉ tạo tài liệu phân tích và kế hoạch này. Chưa được yêu cầu triển khai ứng dụng mới hoặc sửa code.
