# Tính năng chatbot Cơ Tu

Chatbot là một tính năng trong `src/cotu_app/features/chatbot/`. SQLite FTS5
tra tư liệu tại Pi, Gemini viết câu trả lời khi có key/mạng. Có CLI, khung
chat nhúng và cửa sổ thử độc lập; không chạy LLM/embedding local.

Corpus đang là ghi chú thử nghiệm: `approved` có 0 đoạn, `research` có 8 đoạn.
Không tự nâng trạng thái duyệt để app trả lời được. Xem
[kế hoạch và chính sách dữ liệu](../KE_HOACH_CHATBOT_CO_TU.md).

## Chạy từ gốc dự án

```bash
./run_video.sh --chatbot
./run_rfid.sh --chatbot
./run_chatbot.sh doctor
./run_chatbot.sh build-index --mode research
./run_chatbot.sh ask --mode research --offline "Gươl dùng để làm gì?"
./run_chatbot.sh desktop --mode research --offline
./run_chatbot.sh chat --mode research
```

Lõi chatbot chỉ cần Python tiêu chuẩn/SQLite; cửa sổ cần Tkinter hệ điều hành.
Thiếu key/mạng/quota thì hiện đoạn tư liệu, không trình bày đó là câu trả lời
Gemini. Mỗi lệnh có `--help`.

## Cấu hình

Key phát triển nằm ở `config/chatbot/.env`, theo `.env.example`. File được đọc
như KEY=VALUE, không thực thi như shell và không đưa vào gói phát hành. Các mục
chính: `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_THINKING_LEVEL`. `doctor` chỉ báo
đã có key hay chưa; không in key và không gọi API.

Trong `config/video_stories.json`:

```json
"chatbot": {"enabled": true, "mode": "research"}
```

`research` luôn có nhãn thử nghiệm, chưa duyệt. Dùng `approved` sau khi duyệt
nguồn; `enabled: false` tắt panel. Mỗi lượt tối đa một lời gọi Gemini, không tự
retry hay chuyển model. Câu hỏi, lịch sử ngắn và tư liệu chọn sẽ gửi Google khi
dùng API. Người quản lý project kiểm tra tài khoản/billing/quota; chính sách
chi tiết và nguồn tham khảo nằm trong kế hoạch.

## Mã và dữ liệu

| Vị trí | Vai trò |
| --- | --- |
| `features/chatbot/retrieval.py` | Nạp corpus, kiểm tra chính sách và tìm BM25 |
| `features/chatbot/gemini.py` | HTTPS/SSE, timeout, lỗi API đã làm sạch |
| `features/chatbot/service.py` | Cache, quota, hủy, kiểm tra nguồn và hội thoại |
| `features/chatbot/desktop.py` | Panel Tkinter và cửa sổ thử độc lập |
| `features/chatbot/integration.py` | Gắn panel vào app, đồng bộ nhân vật và TTS |
| `data/chatbot/{raw,manifests,clean}` | Hồ sơ nguồn, hash và ghi chú biên tập |
| `data/chatbot/{corpus,index,evaluation}` | JSONL dùng trong app, SQLite và bộ đánh giá |
| `config/chatbot/aliases.json` | Thuật ngữ và cách gọi tương đương |

Các đường dẫn `features/` trong bảng tính từ `src/cotu_app/`. File raw/provenance
được giữ nguyên; đường dẫn local trong báo cáo cũ phản ánh vị trí lúc thu thập,
không phải đường dẫn chạy app hiện tại.

## Cập nhật và đánh giá

```bash
python3 tools/chatbot/import_corpus.py
./run_chatbot.sh build-index --mode research
./run_chatbot.sh build-index --mode approved
./run_chatbot.sh evaluate --mode research
./tools/test.sh -q
```

Import không thay cờ duyệt, kiểm tra đúng bytes trước khi thay corpus. Index
hai mode tách riêng. Báo cáo ở `reports/chatbot/`. Các test không gọi Gemini
thật hoặc tải model.

Xem [kiến trúc](ARCHITECTURE.md), [đánh giá](EVALUATION.md),
[triển khai Pi](RASPBERRY_PI.md), [báo cáo](../../reports/chatbot/VALIDATION.md).
