# Đánh giá đúng phạm vi

```bash
./tools/test.sh -v
./run_chatbot.sh evaluate --mode research --rounds 100
```

Tests dùng fake client/HTTP/SSE, không gọi Gemini hoặc tiêu quota. Có ca Unicode chia giữa các gói, JSON sai/cắt/safety, 429 và RetryInfo, key lỗi, nguồn bịa/nguồn ngoài context, cache context/TTL/giới hạn, hủy trước/trong stream, một lượt đang chạy, lọc dữ liệu và cập nhật index. Tests không xác minh khả năng tuân thủ prompt của model thực.

Evaluate chỉ gọi retrieval, warm tối thiểu 100 lượt. Báo cáo ở `reports/chatbot/retrieval.research.local.json` gồm máy/Python/fingerprint, p50/p95, peak RSS của tiến trình CLI, ID liên quan và ID tìm được từng ca. Không ghi key hoặc hội thoại API. Peak RSS này chưa gồm desktop/video/STT/TTS và không phải số đo chênh RAM toàn hệ thống.

Trong 32 seed, có 21 câu answerable. `hit_rate_at_3` là tỷ lệ câu có ít nhất một ID liên quan nằm trong top 3. `mean_recall_at_3` là trung bình tỷ lệ số ID liên quan tìm được trên tổng ID liên quan của từng câu answerable; không gộp câu thiếu dữ liệu vào mẫu số. Đây là bộ nháp có thể thiên lệch theo thuật ngữ, chưa phải benchmark độc lập. Đừng chỉnh alias chỉ để làm đẹp bộ seed; thêm tập dev/test do người hiểu nội dung duyệt.

`unanswerable_with_retrieval_matches` nhắc rằng có đoạn trùng từ **không có nghĩa đủ câu trả lời**. Cần chấm Gemini riêng với các ca thiếu dữ liệu, tên khoa học Tring, niên đại nhà cụ thể, nhầm giới múa, dị bản, so sánh dân tộc và chỉ dẫn bỏ nguồn.

Khi có key: thu từng kết quả JSON bằng `ask --json` hoặc gọi service trong script đo của người vận hành; kiểm tra quota trước. Ghi `first_token_ms`, `total_ms`, usage, cache/API flag và groundedness thủ công. Không tự chạy vòng 100 lời gọi API miễn phí. Chỉ kết luận p95 mạng sau khi đủ lượt độc lập, nêu tách cache với API, cold với warm và điều kiện Wi-Fi/Ethernet. Khi chia sẻ log, loại câu hỏi có thông tin riêng tư.

Chưa đạt cổng khách dùng nếu chưa duyệt corpus, chưa chấm nguồn hỗ trợ từng mệnh đề hoặc còn lỗi gán nhầm tộc người/dị bản. Bộ test qua không thay thế các bước này.
