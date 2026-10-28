# Kiến trúc chatbot Nhà Gươi

```text
CLI / Tkinter
    → ChatService (một lock, history do caller giữ)
    → app nhúng: CuratedCatalog khớp câu/alias → đáp án duyệt + nguyên văn cho WAV
    → chưa khớp: tiếp tục Retriever/AI bên dưới
    → Retriever (SQLite read-only, kết nối theo lượt)
    → không có evidence: thiếu dữ liệu/hỏi rõ
    → offline/thiếu key/cooldown: thông báo ngắn, không đổ đoạn tư liệu
    → cache hợp lệ: kết quả cũ đúng context
    → GeminiClient: HTTPS POST, SSE, JSON schema
    → kiểm tra status + ID nguồn trong context
    → ChatResult + citations từ corpus
```

FTS5 dùng cột tiêu đề, nội dung và thuật ngữ, trọng số BM25 3/1/2. Văn bản tìm kiếm bỏ dấu và đổi `đ → d`; văn bản hiển thị giữ nguyên. Từ phổ biến bị bỏ; truy vấn dùng OR trên token đã giới hạn và truyền bằng SQL parameter. Câu dài cần ít nhất hai token trùng để bớt match nhầm một âm tiết (giá/giả, tỷ/ty); đây là heuristic có thể giảm Recall. Không gọi embedding/query rewrite. Follow-up có dấu hiệu nối tiếp ghép câu USER gần nhất, không dùng lời assistant như bằng chứng; tối đa hai lượt ngữ cảnh gửi API.

Index research/approved có mode và fingerprint corpus+alias+schema. Giữ nguyên JSON metadata trong bảng documents. Không dùng điểm BM25 làm độ tin cậy hoặc tự khẳng định tài liệu đủ để trả lời. Có đoạn trùng từ nhưng thiếu chi tiết vẫn có thể gọi Gemini; model phải trả `insufficient_evidence`/`clarification_needed`. Khi ngoại tuyến hoặc lỗi API, app báo chưa thể tổng hợp; không coi nội dung tìm được là đáp án.

API sinh JSON `{answer_text, status, citation_ids}`. Bộ đọc SSE ghép JSON bị chia giữa các gói, bỏ phần `thought`. Cuối luồng phải có finishReason STOP và JSON hợp lệ; câu answered cần ít nhất một ID thật trong context. Đây không phải bộ kiểm tra factuality: ID hợp lệ chưa chứng minh mệnh đề được nguồn hỗ trợ.

Từ `1.1.4`, prompt yêu cầu đúng một đoạn trả lời tổng hợp 2–3 câu, khoảng 40–80 từ, ngân sách đầu ra mặc định 384 token. `presentation.py` bỏ định dạng danh sách, mã trích dẫn và URL khỏi lời đáp. Giao diện chỉ hiện một đáp án hoàn chỉnh, không hiện bản nháp, danh sách tài liệu, nguồn hay số liệu kỹ thuật kèm mỗi câu trả lời. TTS và lịch sử dùng cùng nội dung đã làm gọn. CLI mặc định cũng chỉ in đáp án; `ask --json` vẫn giữ citations/notice/metrics cho kiểm tra nội bộ. Nguồn tiếp tục được xác thực; chế độ research vẫn được ghi rõ ở thông báo chung của giao diện.

Cache LRU RAM 64 kết quả, TTL 900 giây. Khóa gồm system prompt, JSON prompt (question/history/character/mode/evidence), model/thinking/output và fingerprint index. Chỉ cache kết quả API đã qua kiểm tra; không lưu key, câu hỏi hay cache xuống đĩa. Kết quả cache có usage rỗng và `metrics.api_called=false`, không tính lại token đã dùng trước.

Một yêu cầu API đang chạy; không retry tự động. Khoảng cách cục bộ mặc định 6 giây chỉ giúp giảm burst, không bảo đảm RPM/TPM/RPD. 429/503 đặt cooldown theo header hoặc RetryInfo (mặc định 60 giây). Nếu lỗi, trả thông báo ngắn thay vì sao chép đoạn tư liệu. Server có thể vẫn tính lượt đã gửi khi người dùng bấm Dừng.

Tkinter chỉ cập nhật widget ở main thread; worker đưa kết quả hoàn chỉnh vào queue; poll 40 ms, tối đa 100 sự kiện mỗi lần. Phiên mới tăng generation để loại sự kiện cũ, xóa history. Không gửi lượt khác cho đến khi worker cũ kết thúc. Cancel được kiểm tra trước/sau đọc socket; đang chờ mạng có thể phải chờ socket timeout (15 giây mặc định), không hứa ngắt tức thì. Deadline tổng 35 giây được kiểm tra giữa các lần đọc, có thể vượt thêm tối đa một lần chờ socket; không phải deadline cứng.

`ChatService.ask(question, history, character_id, offline, on_delta, cancel)` là điểm nối dùng chung. Đầu ra `ChatResult.to_dict()` gồm answer_text/status/citations/character_id/mode/notice/cached/metrics. `on_delta` chạy ở worker; UI gọi qua queue. Lịch sử chỉ nhận status answered; không nối fallback/lỗi/hủy vào lịch sử.

`ChatPanel` là Frame nhúng được, không đổi root/title/protocol của ứng dụng cha; `ChatWindow` bọc panel để chạy độc lập. `src/cotu_app/features/chatbot/integration.py` gắn panel vào Notebook của VideoApp và LiveApp, dùng TouchKeyboard hiện có, pause video/stop giọng trước khi gửi, đồng bộ nhân vật và hủy khi chuyển tab/đóng app. Không tạo Tk root hoặc mainloop thứ hai. Khi không có index, dựng một lần lúc khởi động; lỗi chatbot không làm sập giao diện video.

VideoApp giữ đáp án mẫu đã duyệt; câu gõ/mic không khớp sẽ chọn tab Trò chuyện Nhà Gươi và gửi cùng câu hỏi. Câu answered được tự đọc bằng ZeroTTS; model được chuẩn bị ở nền từ lúc mở app. Từ `1.1.5`, âm thanh của lời đáp được tạo và nạp đầy đủ trước khi phát để không ngắt giữa vài từ khi Pi tạo giọng chậm hơn thời gian thực. Chân trang báo trạng thái chuẩn bị/đọc; nút Nghe trả lời dùng lại WAV đã lưu. Phiên mới/đổi nhân vật xóa câu trả lời có thể đọc và hủy audio cũ. Cấu hình bật/tắt/mode dùng `config/video_stories.json`, mặc định code vẫn approved, file cấu hình thử hiện chọn research.

Từ `1.1.6`, app nhúng nạp `stories.catalog.CuratedCatalog` từ cấu hình thực tế
trước khi dựng ChatPanel. Tra câu/alias bằng `question_key`, dùng chung quy tắc
với Hỏi đáp; không so độ giống để chọn đáp án. Kiểm tra SHA256 video, SHA256 và
nguyên văn TXT bằng các bộ nạp sẵn có; đọc mỗi bank dùng chung một lần khi mở
app. Bank sai nguồn bị loại và ghi log. Nút đổi video/bộ hỏi đáp trong Thiết lập
thay snapshot tra cứu. Không đọc lại MP4 hoặc chạy ASR trong mỗi câu hỏi.

Từ `1.1.7`, `core.text.question_key` còn chuẩn hóa các mẫu hỏi tương đương:
định nghĩa “là cái gì / được hiểu là gì / thế nào là”, công dụng “chức năng /
công dụng / dùng để làm gì”, ý nghĩa “ý nghĩa của X / X có ý nghĩa gì”,
nguyên nhân “vì sao / tại sao”, số lượng “có mấy / có bao nhiêu” và vật liệu
chung. Nhận các lời mở đầu “bạn có thể giải thích giúp tôi…”. Quy tắc dùng
chung ở cả Hỏi đáp và Trò chuyện, không thêm model/mạng hoặc đổi dữ liệu
gốc. Giữ từ phủ định, chi tiết riêng, địa bàn và số; không chọn theo độ giống
chữ. Đây là bộ quy tắc có phạm vi giới hạn, không phải semantic model tổng
quát. Chuẩn hóa gây trùng nhiều đáp án vẫn bị từ chối; nguồn và WAV không đổi.

Kết quả khớp có `status=answered`, `mode=approved`, `metrics.route=curated`,
`api_called=false`; không cần retrieval, key, mạng hoặc hết cooldown. Metadata
nguồn giữ nội bộ. `audio_text` giữ nguyên văn đáp án và `character_id` của chủ
câu hỏi để khớp khóa WAV đã chuẩn bị; phần chữ hiển thị/lịch sử vẫn được làm
gọn. Đáp án AI không có `audio_text`, tiếp tục đọc nội dung đã làm gọn như cũ.
WAV hợp lệ đi thẳng sang luồng phát sẵn có, kể cả khi model đang nạp nền; WAV
thiếu vẫn cần tạo toàn bộ trước khi phát. Cách hỏi mới hoặc trùng nhiều đáp án
được đưa qua luồng Retriever/AI. CLI trực tiếp vẫn dùng Retriever/AI mặc định.
