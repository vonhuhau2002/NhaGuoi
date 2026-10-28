# Kiểm chứng bản thử Gemini API — 18/10/2026

Đã triển khai lõi chatbot trong `chatbot/`, theo kế hoạch chuyển LLM sang API, và tích hợp vào cả giao diện video lẫn truyện RFID. Bảng bên dưới ghi kết quả đợt bản độc lập; xem phần bổ sung tích hợp ở cuối để biết trạng thái mới nhất.

## Đã kiểm tra

| Hạng mục | Kết quả |
|---|---|
| Máy thực thi | Raspberry Pi, aarch64, Python 3.13.5, SQLite 3.46.1; snapshot nguồn nhận diện Pi 5 RAM 4 GB |
| Corpus/seed | Bản sao byte giống nguồn; 10 ghi chú, 32 seed; không đổi trạng thái duyệt |
| Index research | 8 ghi chú; loại context khác tộc người và bài đăng lại |
| Index approved | 0 đoạn; thông báo kho trống, không âm thầm lấy research |
| Tests | **38/38 qua**, dùng fake transport, không gọi mạng/API |
| CLI thực | doctor/build-index/ask JSON và văn bản, offline, thiếu key, ngoài miền |
| Tính độc lập | Chép thư mục sang `/tmp`, bỏ index rồi dựng lại; hỏi CLI và terminal reset/quit chạy được ngoài dự án cha |
| Mã nguồn | Python parse và shell syntax qua; import xác minh JSONL trước khi thay bản sao |
| Cửa sổ | Module có, xử lý thiếu DISPLAY có thông báo; chưa tương tác với cửa sổ thật |
| Gemini thật | **Đã thử thành công một lượt** với `gemini-3.1-flash-lite`, status answered, nguồn S03:guol |

Test giao thức có JSON/Unicode/SSE chia gói, bỏ thought, cắt output/safety/schema sai, key/model lỗi, 429/RetryInfo/cooldown, timeout, hủy, cache/TTL/context, một request đang chạy và ID nguồn không hợp lệ. Test giả không chứng minh model thực tuân thủ prompt, có Free Tier cho project này hoặc đạt latency mục tiêu.

## Đo retrieval offline

Kết quả chi tiết và ID từng ca: [retrieval.research.json](retrieval.research.json). Chỉ gọi SQLite, không có API và desktop/video/audio.

| Chỉ số | Kết quả |
|---|---|
| Câu seed | 32; 21 answerable |
| Hit@3 / Recall@3 trung bình trên câu answerable | **19/21 = 90,48%** |
| Lượt warm đo latency | 100 |
| Retrieval p50 / p95 | **0,607 / 0,794 ms** |
| Peak RSS tiến trình CLI | **24,45 MiB** |
| Câu insufficient_evidence vẫn có match từ khóa | **7** — retrieval không tự kiểm tra đủ bằng chứng |

Hai câu chưa lấy đúng nguồn: `G04` (tiền đề gươl chỉ để biểu diễn cho khách) và `D02` (so sánh con gái/con trai múa). Bộ lọc yêu cầu hai từ trùng ở câu dài giảm match nhầm ngoài miền nhưng làm mất hai ca này. Đây là lỗi thật cần đánh giá thêm bằng tập độc lập; chưa thêm alias chỉ để làm đẹp điểm seed.

Trước khi có bộ lọc, seed đạt 21/21 nhưng câu “Tỷ giá USD hôm nay?” match nhầm vì bỏ dấu làm giá/giả, tỷ/ty giống nhau. Chỉ số chính thức bên trên là **cấu hình cuối có bộ lọc**, không dùng điểm của bản cũ. Cả bộ seed và các cách gọi miền đều chưa được chuyên gia duyệt; không công bố 90,48% như độ chính xác chatbot tổng thể.

## Việc cần điều kiện thật

- Đã lưu key riêng trong `.env` (quyền 0600, bỏ qua trong Git), chọn `gemini-3.1-flash-lite` theo ảnh AI Studio và gọi đúng một câu thử thành công. Tiếp tục kiểm tra quota trong AI Studio khi sử dụng.
- Mở desktop tại Pi, thử stream/Dừng/Phiên mới và màn hình cảm ứng; kiểm tra khi mạng chập chờn.
- Duyệt nội dung/nguồn và chấm groundedness, thiếu dữ liệu, dị bản, câu ngoài miền trên API thật. ID nguồn hợp lệ chưa bảo đảm facts đúng.
- Thu TTFT/p95 API và đo chung với video trong 30 phút trước khi kết luận độ mượt hoặc nối mic/TTS. Các số RSS/latency ở trên không bao gồm các phần đó.

Lệnh chạy và cấu hình: [README](../../docs/chatbot/README.md). Không cần cài hoặc nạp LLM local để làm các bước này.

## Tích hợp vào dự án chính — 18/10/2026

`ChatPanel` đã nhúng vào Notebook của VideoApp/LiveApp, không thêm root/mainloop riêng. Bản video chuyển câu gõ/mic chưa khớp đáp án mẫu sang tab Gemini; đáp án khớp vẫn giữ giọng/người trả lời cũ. Có bàn phím cảm ứng, Đọc trả lời dùng chung ZeroTTS, Dừng trả lời/Phiên mới và đồng bộ nhân vật. File cấu hình thử bật mode research và giữ nhãn chưa duyệt.

- **113/113 kiểm thử dự án qua** trong `.venv-video` với `NHARONG_TEST_DISPLAY=:0`, không bỏ qua ca GUI; **38/38 kiểm thử lõi chatbot qua** với Python hệ thống. Python hệ thống thiếu scipy và một số gói video nên không phù hợp cho bộ TTS/video; không cài thêm gói để xử lý việc này.
- 12 kiểm thử adapter/panel đã qua trên desktop Pi, bao gồm gửi/nhận câu trả lời giả, thay bản nháp, đổi nhân vật khi đang chờ, bỏ kết quả/giọng cũ, tái dùng TTS và giữ nguyên cửa sổ chính.
- Đã khởi tạo VideoApp thật với worker nhận dạng hoạt động, tắt RFID riêng cho smoke test; kiểm tra panel và bàn phím vừa cửa sổ 800×480. Đã khởi tạo LiveApp với reader giả để xác minh panel trong cửa sổ truyện RFID.
- **Một lời gọi API thật qua chính khung chat của VideoApp** trả answered, nguồn S03:guol, tổng 8.430,978 ms. Sau đó chọn nhân vật khác xóa lịch sử và câu trả lời có thể đọc. Không bắn vòng benchmark API.
- Không tự phát giọng trong smoke test; chưa chấm mic/loa thực, RFID thực hoặc phiên video/chat 30 phút. Các phần đó cần kiểm tra vận hành tiếp.

Chạy bản chung: `./run_video.sh --chatbot` hoặc `./run_rfid.sh --chatbot`.

## Bổ sung kiểm tra API thật — 18/10/2026

Người dùng cung cấp key và chọn Gemini 3.1 Flash-Lite trong AI Studio. Đã đổi cấu hình runtime, mặc định mã nguồn và `.env.example` sang `gemini-3.1-flash-lite`, thinking minimal. Không lưu key trong báo cáo hoặc mã nguồn; `.env` có quyền 0600 và thuộc `.gitignore`.

Một lượt hỏi công khai về công dụng nhà gươl qua chính `ChatService` trả status `answered`, dẫn nguồn `S03:guol` hợp lệ. Retrieval 0,687 ms; chữ đầu 8.271,654 ms; hoàn tất 8.497,616 ms. Usage: 478 prompt tokens, 95 output tokens, 573 tổng. Lượt này thực sự gọi API, không dùng cache hoặc fallback. Đây là **một mẫu**, không phải p50/p95; chưa đạt bằng chứng cho mục tiêu chữ đầu ≤ 3 giây. Không suy trạng thái billing/Free Tier từ việc API thành công.

38/38 tests offline vẫn qua sau khi đổi model. Chưa kiểm tra thao tác desktop vì phiên làm việc không có DISPLAY.

Đã mở bản chính bằng `./run_video.sh --chatbot` trên desktop Pi và quan sát tab Chatbot Gemini trong cùng cửa sổ Nhà Rông. Đầu đọc báo sẵn sàng; chưa quét thẻ hoặc đo mic/loa trong lượt xác minh này.
