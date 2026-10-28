# Adapter RFID cục bộ

`mfrc522/` là bản adapter đã dùng trên Pi 5, được sao chép từ
`/home/admin/mfrc522_test/src/mfrc522` để dự án không phụ thuộc thư mục ngoài.
Bản này dùng `spidev` và GPIO Zero; không thay bằng adapter RPi.GPIO cũ khi
chưa thử trên phần cứng. Giấy phép gốc ở `MFRC522-LICENSE`.

Ứng dụng nạp adapter qua `features/rfid/reader.py`. Không mở SPI/GPIO trong
thao tác kiểm tra import. Các sửa đổi ở đây chỉ vào app đã cài sau phát hành.
