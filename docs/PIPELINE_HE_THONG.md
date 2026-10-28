# Pipeline hiện tại của hệ thống Nhà Rông Cơ Tu

Tài liệu mô tả **mã nguồn và cấu hình đang có trong dự án**, không phải thiết kế dự kiến. Hệ thống có hai ứng dụng độc lập, dùng chung bảng thẻ RFID và bộ phát giọng ZeroTTS:

| Chế độ | Lệnh chạy | Chức năng chính |
| --- | --- | --- |
| Video và hỏi đáp | `./run_video.sh` | Quét/chọn nhân vật → phát MP4 → hỏi bằng mic, gõ chữ hoặc chọn câu mẫu → hiển thị và đọc đáp án đã duyệt. |
| Truyện chữ RFID | `./run_rfid.sh` | Quét thẻ → hiện truyện chữ và đọc bằng ZeroTTS; Già làng có thể kể truyện nhân vật khác rồi mở hỏi đáp mẫu. |

`run_video.sh` và `run_rfid.sh` chạy Python trong `.venv-video`, thiết lập đường dẫn thư viện âm thanh và cache mô hình. Mỗi lệnh mở một giao diện riêng, không tự mở ứng dụng kia. Phần mềm cần màn hình desktop cho Tkinter; video nhúng cần libVLC và X11/XWayland.

Tính năng [chatbot](chatbot/README.md): SQLite FTS5 tại Pi → Gemini API → văn bản có nguồn, đã tích hợp tab **Chatbot Gemini** vào cả hai giao diện qua `src/cotu_app/features/chatbot/integration.py`. Chạy `./run_video.sh --chatbot` hoặc `./run_rfid.sh --chatbot` để mở thẳng tab này. Khung chat có bàn phím cảm ứng, streaming, Dừng/Phiên mới và **Đọc trả lời** dùng ZeroTTS/nhân vật hiện hành. Ở ứng dụng video, câu hỏi gõ/mic chưa khớp đáp án mẫu chuyển sang tab chat; đáp án mẫu vẫn xử lý như trước. Rời tab hủy lượt chờ; đổi nhân vật xóa lịch sử và bỏ phản hồi cũ. Không nạp LLM/embedding local; thiếu key/mạng/quota thì hiện đoạn tư liệu. Cấu hình `config/video_stories.json → chatbot` đang chọn research để thử và hiển thị nhãn chưa duyệt. Bản độc lập `./run_chatbot.sh desktop --mode research` / CLI vẫn dùng được. Xem [kế hoạch](KE_HOACH_CHATBOT_CO_TU.md) và [kiểm chứng](../reports/chatbot/VALIDATION.md).

## 1. Đầu vào và dữ liệu dùng chung

| Đầu vào | Nguồn | Được dùng để làm gì |
| --- | --- | --- |
| UID thẻ | Đầu đọc RFID/MFRC522 | Tra `config/rfid_cards.json` để chọn một trong sáu nhân vật. Không ghi nội dung truyện lên thẻ. |
| Chạm màn hình | Nút nhân vật, nút điều khiển, câu hỏi mẫu, ô nhập | Chọn truyện/video, điều khiển phát, hỏi hoặc cấu hình. |
| Nút GPIO (tùy chọn) | Bốn nút khi chạy video với `--buttons` | Chọn `person_1`–`person_4` theo `gpio_buttons` trong `config/video_stories.json`. |
| MP4 và dữ liệu video | `config/video_stories.json`, `data/videos/*.mp4`, TXT/SRT, JSON hỏi đáp | Phát hình/tiếng gốc; nạp lời thoại và đáp án của đúng video. |
| Mẫu chuyện bổ sung | `data/stories/Text cau chuyen co tu.txt`, `data/stories/co_tu_story.questions.json` | Thêm 5 câu của Già làng từ tài liệu, có nguồn TXT và SHA-256 riêng. |
| Giọng nói câu hỏi (chỉ chế độ video) | Mic được chọn trong `config/video_stories.json` | Ghi WAV tạm rồi chuyển tiếng Việt thành chữ bằng `faster-whisper`. |
| Giọng nhân vật và loa | `config/tts_voices.json`, `config/tts_output.json` | Chọn giọng ZeroTTS và thiết bị phát câu trả lời/truyện chữ. |

`config/rfid_cards.json` ánh xạ UID sang `elder`, `person_1` … `person_5`; cả hai ứng dụng đọc cùng file này. Quét thẻ chưa gán chỉ báo trạng thái, không tự chọn truyện. Việc gán lại thẻ lưu vào file sau khi người dùng xác nhận nếu đụng ánh xạ cũ.

## 2. Pipeline video và hỏi đáp (`src/cotu_app/app/desktop.py`)

```text
Thẻ RFID / chạm nhân vật / nút GPIO tùy chọn
  → chọn nhân vật, dừng video/giọng cũ, bỏ kết quả xử lý cũ
  ├─→ lấy đường dẫn MP4 → libVLC → hình trên màn hình + tiếng gốc của video
  └─→ nạp 32 câu của MP4 + 5 câu từ mẫu chuyện TXT → 37 câu, nhóm theo nhân vật trả lời

Chạm câu mẫu / gõ câu hỏi / bấm Hỏi bằng mic
  → nếu dùng mic: thu WAV tạm → faster-whisper (tiếng Việt) → văn bản
  → chuẩn hóa câu hỏi, so với câu hỏi và aliases đã duyệt
  ├─→ khớp đúng một câu → lấy nhân vật của câu → hiện đáp án → giọng ZeroTTS tương ứng → loa
  └─→ không khớp → hiện thông báo/gợi ý/đoạn lời thoại liên quan; không đọc đáp án suy đoán
```

### Nạp dữ liệu của video

Khi chọn nhân vật, ứng dụng phát MP4 và tự gọi tác vụ nạp nội dung. Nút **Nạp / học lời thoại** cho phép gọi lại tác vụ. Các đường dẫn trong `config/video_stories.json` có thể là tuyệt đối hoặc tương đối tính từ file cấu hình.

1. Tính SHA-256 của **nội dung MP4**. Nếu đã chỉ định JSON hỏi đáp, `video_sha256` trong JSON phải trùng mã này; sai hoặc thiếu file thì báo lỗi, không lấy bộ khác thay thế. Bộ hiện tại gắn `character_id` cho từng câu và vẫn nạp đủ mọi câu; giao diện nhóm theo nhân vật trả lời. Bộ cũ không có trường này vẫn dùng được.
2. Nếu có TXT/SRT: đọc các đoạn lời thoại; SRT có mốc thời gian, TXT chỉ có từng dòng. Nếu không có lời thoại nhưng có bộ hỏi đáp hợp lệ: dùng ngay bộ hỏi đáp, không cần nhận dạng MP4.
3. Chỉ khi **không có cả TXT/SRT lẫn bộ hỏi đáp**, ứng dụng đọc `.video_cache` theo mã video + tên model; cache chưa có/hỏng thì `faster-whisper` nhận dạng tiếng trong MP4 và ghi các đoạn có mốc thời gian vào cache.
4. Đưa câu hỏi mẫu lên giao diện. Đây là nạp/lập chỉ mục nội dung, **không huấn luyện lại model**. Ứng dụng không phân tích hình ảnh trong video để tự tạo đáp án.

Các bộ trong `document_questions` được nạp bổ sung bằng nguồn TXT riêng: kiểm
tra `source_sha256`, đọc các khối `Câu N:`, đối chiếu nguyên văn câu hỏi/lời đáp
với JSON và kiểm tra trùng cách hỏi với các bộ đang nạp. Tài liệu hiện tại có
5 câu, 29 cách hỏi ngắn, đều gán `elder`. Chúng có nhãn **Mẫu chuyện**, nằm
đầu nhóm Già làng và hiện nguồn file + số câu khi trả lời. Thần thoại và lời
kể được giữ như mẫu chuyện người dùng cung cấp, không trở thành lời thoại MP4.
Sau khi sửa TXT, chạy `tools/stories/import_questions.py` theo hướng dẫn video
rồi nạp lại nội dung; không dùng âm thầm một bộ đã lệch nguồn.

### Xử lý một câu hỏi

Video được tạm dừng khi mở phần hỏi đáp/thu mic. Mic chỉ thu khi bấm **Hỏi bằng mic**, mặc định 8 giây (`record_seconds` cho phép 2–30 giây); không nghe liên tục. Tác vụ mic và ASR chạy trong tiến trình riêng. Câu nhận dạng được đưa vào cùng luồng xử lý với câu gõ hoặc câu chọn sẵn.

Ứng dụng bỏ khác biệt hoa/thường, dấu tiếng Việt/dấu câu và một số cách xưng hô, sau đó so khớp với `question` hoặc `aliases` **trong toàn bộ câu đã nạp từ video hiện tại và tài liệu bổ sung được cấu hình**. **Chỉ khớp đúng một mục đã duyệt mới lấy `answer` và gọi ZeroTTS bằng giọng của `character_id` thuộc câu đó.** Bộ cũ không có người trả lời thì dùng giọng của nhân vật đang chọn. So khớp gần chỉ để gợi ý tối đa ba câu; lời thoại liên quan, nếu có, chỉ hiển thị kèm nguồn/mốc thời gian để đối chiếu. Khi không có đáp án được duyệt, hệ thống không bịa câu trả lời và không đọc gợi ý ra loa.

Đáp án đã duyệt xuất hiện trên màn hình trước; việc tổng hợp/phát tiếng là bước riêng. Vì vậy có thể **thấy chữ nhưng chưa nghe tiếng** nếu ZeroTTS, model hoặc thiết bị phát lỗi. Màn hình trạng thái sẽ báo lỗi phát cụ thể. Chọn thẻ khác sẽ dừng tiếng cũ và bỏ kết quả nhận dạng/nạp nội dung cũ.

### Trạng thái dữ liệu video hiện có

Trong thư mục dự án hiện chỉ có `data/videos/person_5.mp4`. Cấu hình `config/video_stories.json` cho **cả sáu nhân vật** cùng trỏ tới MP4 này, `data/videos/person_5.notes.srt` và `data/videos/person_5.questions.json`. Bộ 32 câu được chia: Già làng 6, người giữ lửa 5, dẫn đường 5, dệt vải 6, làm nhạc cụ 5, kể chuyện 5. Đây là phân vai trả lời theo chủ đề, **không khẳng định các nhân vật có mặt trong video**. Nếu thay MP4, phải duyệt lại TXT/SRT và bộ hỏi đáp, rồi cập nhật SHA-256.

## 3. Pipeline truyện chữ RFID (`src/cotu_app/app/story_reader.py`)

```text
Thẻ RFID → tra UID → chọn nhân vật → lấy truyện mẫu trong src/cotu_app/features/stories/characters.py
  → hiện truyện chữ → ZeroTTS (nếu bật Tự đọc khi quét) → loa

Chọn “Già làng kể” → chọn truyện của một nhân vật phụ
  → hiện truyện, đọc bằng giọng Già làng
  → sau khi đọc xong: mở 3 câu hỏi mẫu của truyện
  → chạm câu hỏi → hiện lời giải thích → ZeroTTS → loa
```

Chế độ này **không phát MP4, không dùng mic/Whisper và không tra bộ hỏi đáp JSON của video**. Truyện chữ đến từ `src/cotu_app/features/stories/characters.py` ; 15 câu hỏi mẫu nằm trong `src/cotu_app/features/stories/sample_questions.py`, mỗi truyện ba câu. Hỏi đáp chỉ mở sau khi Già làng kể xong truyện của nhân vật phụ; nếu tắt tự đọc hoặc không có tiếng, có nút **Đã đọc xong** để mở thủ công. Đổi nhân vật sẽ xóa trạng thái hỏi đáp trước.

## 4. Pipeline giọng nói và đầu ra âm thanh (`features/tts/`)

Ứng dụng dùng **một tiến trình ZeroTTS sống suốt phiên**. Model cục bộ `.venv-video/models/zerotts` chỉ nạp khi có âm thanh chưa được lưu, rồi giữ trong RAM; đổi nhân vật chỉ đổi giọng trong cùng model. Dừng đọc/đổi thẻ hủy lượt đọc, không giết model. Đóng cửa sổ mới dừng tiến trình TTS.

Khi nạp bộ hỏi đáp, ứng dụng tự tạo WAV cho các đáp án còn thiếu ở nền và hiển thị tiến độ ngay dưới ô nhập câu hỏi. Văn bản + giọng + tốc độ + phiên bản/model tạo thành khóa trong `var/cache/tts/*.wav`. Lần bấm sau đọc WAV đã có, kể cả sau khi khởi động lại; không nạp model nếu mọi câu đều đã lưu. Đổi đáp án, giọng, tốc độ hoặc trọng số model sẽ dùng khóa mới. WAV hỏng/thiếu được tạo lại; chỉ lưu file sau khi tổng hợp hoàn tất. Câu người dùng bấm được ưu tiên hơn tác vụ tạo nền; phát WAV chạy ở luồng riêng nên không chờ tác vụ tổng hợp khác. Các câu chưa có WAV vẫn phải chờ tạo lần đầu.

Có thể tạo đủ âm thanh trước khi mở giao diện bằng `./run_video.sh --prepare-tts`. Lệnh kiểm tra bộ hỏi đáp với SHA-256 của MP4 và nguồn TXT, chỉ tạo câu còn thiếu, báo tiến độ và không mở loa. Bộ hiện tại có 37 đáp án: 32 câu của video và 5 câu của tài liệu bổ sung. Truyện chữ RFID cũng dùng tiến trình và cache này, tạo lần đầu rồi dùng lại.

Hiện `config/tts_output.json` chọn **`alsa-name:USB Audio Device`**, chọn ngõ ALSA theo tên loa USB thay vì cố định số card và bỏ qua các ngõ ảo trùng tên. Khi rút/cắm lại USB mà danh sách PortAudio đã cũ, tiến trình phát tự làm mới danh sách một lần, không nạp lại model. Nếu có hai loa vật lý cùng tên, ứng dụng báo rõ các ngõ ra để chọn. Trên Pi đã kiểm tra, loa là PortAudio **#1**, `hw:2,0`; **#0 là HDMI**, `hw:1,0`. `./run_video.sh --check-audio` kiểm tra thiết bị và định dạng đầu ra; kết quả `#1: int16, 48000 Hz, 2 kênh` nghĩa là đã chọn đúng loa theo cấu hình, **chưa chứng minh đã phát được tiếng**. `./run_video.sh --test-audio` phát tiếng bíp qua loa đó; `./run_video.sh --test-tts` đọc một câu thử qua toàn bộ pipeline ZeroTTS. Âm thanh gốc của MP4 do VLC quản lý riêng, không dùng `config/tts_output.json`.

Giọng cố định qua các lần mở ứng dụng: Già làng `huuduc` (nam lớn tuổi, 0,88); người giữ lửa `giahuy`; người dẫn đường `quangminh`; người dệt vải `kimoanh` (nữ trung niên, 0,95); người làm nhạc cụ `tiendat`; người kể chuyện `maichi` (nữ trẻ). Bốn vai còn lại có tốc độ 1,00. Trình phát ZeroTTS là ngoại tuyến sau khi đã cài model. Tiếng “tích” quét thẻ của ứng dụng truyện chữ là WAV phát qua `aplay`/`paplay` (hoặc chuông hệ thống), **không đi qua ZeroTTS**.

## 5. Đầu ra và file được ghi

| Đầu ra | Nơi xuất hiện / lưu |
| --- | --- |
| Video, câu hỏi, đáp án, lỗi và trạng thái | Cửa sổ Tkinter; video nhúng qua VLC. |
| Tiếng gốc video | Đầu ra âm thanh của VLC/hệ điều hành. |
| Giọng kể và đáp án | Loa được chọn cho ZeroTTS, hiện là USB Audio Device. |
| Âm thanh đáp án/truyện đã tổng hợp | `var/cache/tts/*.wav`, dùng lại qua các lần chạy. |
| Ánh xạ thẻ mới | `config/rfid_cards.json`. |
| Đường dẫn MP4/TXT/SRT/JSON hoặc mic sau khi chỉnh trong giao diện video | `config/video_stories.json` (hoặc file cấu hình đã truyền qua `--config`). |
| Lời thoại ASR của MP4 khi không có TXT/SRT/JSON | `var/cache/video/*.json`; chỉ là cache cục bộ. |
| Bản thu mic | WAV trong thư mục tạm; tự dọn sau tác vụ. |

## 6. Kiểm tra và giới hạn cần nhớ

```bash
./run_video.sh --check         # cấu hình, thư viện, vị trí model; không mở thiết bị
./run_video.sh --check-audio   # liệt kê loa, kiểm tra định dạng; không phát tiếng
./run_video.sh --test-audio    # phát tiếng bíp, kiểm tra loa thực tế
./run_video.sh --test-tts      # đọc câu thử, kiểm tra cả ZeroTTS và loa
./run_video.sh --prepare-tts   # tạo sẵn âm thanh đáp án, không mở loa/giao diện
./run_video.sh --list-mics     # liệt kê thiết bị mic
./run_video.sh --video-sha256 data/videos/person_5.mp4
```

Các lệnh kiểm tra trên **không thay thế thử phát tiếng thật trên màn hình Pi**. Model ZeroTTS có thể cần thời gian nạp trên Pi 5; việc tổng hợp âm thanh không đồng nghĩa đã nghe được tiếng qua loa. Bút Baseus đang dùng chưa được xác nhận là nguồn mic ALSA/PipeWire trên Linux; muốn hỏi bằng giọng nói cần một mic hiện trong `--list-mics`.

Hướng dẫn thao tác và cài đặt chi tiết: [HUONG_DAN_VIDEO.md](HUONG_DAN_VIDEO.md), [HUONG_DAN_RFID.md](HUONG_DAN_RFID.md).
