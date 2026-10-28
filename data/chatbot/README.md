# Dữ liệu nghiên cứu chatbot Cơ Tu

Đọc [kế hoạch](../../docs/KE_HOACH_CHATBOT_CO_TU.md) và [hồ sơ nguồn](../../docs/research/NGUON_CO_TU.md) trước khi dùng dữ liệu này.

- `raw/`: bản tải nguyên gốc, tên có source ID và 12 ký tự đầu SHA-256; không sửa trực tiếp.
- `manifests/sources.json`: danh mục ứng viên, không phải danh sách được phép đưa vào trả lời.
- `manifests/downloads.jsonl`: lịch sử tải dạng append, gồm thành công và thất bại; raw theo hash giữ các phiên bản cũ.
- `manifests/source_reviews.json`: ghi chú biên tập, hash đã đối chiếu, tác giả/ngày và phạm vi sử dụng.
- `clean/S*.md`: bản mẫu người dùng hoặc ghi chú tóm lược ngắn. Nguồn web/PDF chưa được chuyển thành toàn văn sạch.
- `clean/documents.jsonl`: dữ liệu máy cho ghi chú, có locator và hash raw; không phải các chunk đã cắt bằng tokenizer.
- `evaluation/questions.seed.jsonl`: câu hỏi thử ban đầu, chưa được duyệt thành gold.

`production_approved=false` trên toàn bộ ghi chú. `research_notes` dùng để nghiên cứu và chuẩn bị duyệt; `context_only` và `corroboration_only` không tự động đi vào kho trả lời mặc định. File mẫu S01 cách ly vì nguồn từng chi tiết chưa được xác minh. S08/S12 là hai điểm truy cập cùng một công trình, không phải chứng cứ độc lập.

Chạy offline từ thư mục dự án:

```bash
python3 tools/chatbot/prepare_research.py
```

Lệnh xác minh hash và dựng lại MD/JSONL từ ghi chú đã đối chiếu. Nếu raw mới khác hash của ghi chú, cần đọc lại nguồn và cập nhật review. Đây là kho nghiên cứu nguồn; tính năng SQLite + Gemini API được mô tả trong [tài liệu chatbot](../../docs/chatbot/README.md). Sau khi cập nhật JSONL ở đây, chạy `python3 tools/chatbot/import_corpus.py` rồi dựng lại chỉ mục; trạng thái duyệt không được tự thay đổi.
