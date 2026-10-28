# Kể chuyện bằng MP4 và hỏi đáp qua mic

Ứng dụng mới: `src/cotu_app/app/desktop.py`. Các bản thử nghiệm cũ ở `examples/legacy/`. Xem [kiến trúc](ARCHITECTURE.md).
Chạy trong thư mục dự án, bằng Python đã sử dụng được đầu đọc RFID.

## Giao diện dành cho thiếu nhi

- **1 · Nghe chuyện**: chạm ảnh một trong sáu nhân vật hoặc quét thẻ RFID.
  Có thể dùng **4 nút bấm cơ ngoài** trên Pi 5 khi chạy với `--buttons`
  (sơ đồ đấu dây và cài đặt ở **mục 7**).
  Nhân vật đang chọn có nền vàng và viền cam. Màn chào có minh họa nhà rông;
  chạm vào đó để bắt đầu câu chuyện của nhân vật đang chọn.
- **Tiếp tục / Tạm dừng / Kể lại / Dừng**: các nút lớn ngay dưới video.
  Chạm **Em hỏi nhé! →** để chuyển sang hỏi đáp; video sẽ tạm dừng.
- **2 · Em hỏi nhé!**: chạm câu hỏi mẫu tự xuống dòng, nhập câu hỏi rồi bấm
  **Gửi câu hỏi**, hoặc bấm **Hỏi bằng mic**. Thanh trạng thái đổi màu khi mic
  đang thu; hãy đợi dòng **MIC ĐANG THU** rồi nói. Câu trả lời ở khung bên phải.
  Có thể cuộn danh sách câu hỏi và câu trả lời khi nội dung dài.
  Ở chế độ toàn màn hình, chạm ô **Em muốn hỏi** sẽ mở bàn phím cảm ứng
  ngay trong giao diện. Nút **Bàn phím** dùng để bật/tắt bàn phím này.
- **Thiết lập**: dành cho thầy cô/phụ huynh. Chọn nhân vật tại đây để gán
  MP4, lời thoại, bộ hỏi đáp hoặc thẻ mà không tự chuyển sang phát video.
- **Chatbot Gemini**: nhập câu hỏi hoặc chạm câu mẫu ngay trong cùng cửa sổ;
  có bàn phím cảm ứng, Dừng trả lời, Phiên mới và Đọc trả lời theo nhân vật.
  Nếu gõ/hỏi mic ở mục Em hỏi nhé! mà chưa khớp đáp án mẫu, câu hỏi được chuyển
  sang tab này. Câu khớp mẫu vẫn dùng đáp án và giọng đọc có sẵn.
- **Toàn màn hình** hoặc **F11** để mở rộng; **Esc** để thu nhỏ. Giao diện
  hỗ trợ màn hình từ **800×480**, chọn bố cục gọn trên màn hình thấp.

Ảnh nhân vật đã có trong `resources/images/village_characters.png`; giao diện dùng
Tkinter, hoạt động ngoại tuyến và không cần cài thêm thư viện đồ họa.

## Môi trường đã cài trong dự án

Đã tạo `.venv-video` và cài các gói Python cho video, mic, nhận dạng và đọc tiếng Việt.
VLC và Tkinter sử dụng bản có sẵn của hệ thống. PortAudio được giải
nén từ gói Debian arm64 vào `.venv-video/native` vì cài hệ thống cần mật khẩu sudo.
Script sau tự thiết lập đường dẫn thư viện và cache mô hình trong dự án:

```bash
./run_video.sh
./run_video.sh --chatbot
./run_video.sh --check
./run_video.sh --list-mics
./run_video.sh --check-audio
```

`--chatbot` mở thẳng tab chat trong ứng dụng video/RFID. Khung chat dùng chung
`config/chatbot/.env` (model `gemini-3.1-flash-lite`), corpus, system prompt và service
với bản chatbot riêng; không mở ứng dụng hoặc tiến trình LLM khác. Cần mạng và
API key để Gemini sinh câu trả lời; lỗi mạng/quota thì hiện đoạn tư liệu.
Đáp án Gemini chỉ đọc khi bấm **Đọc trả lời**, dùng lại ZeroTTS/giọng nhân vật.
Đổi nhân vật, bắt đầu phiên mới hoặc đóng ứng dụng sẽ hủy/bỏ kết quả cũ;
rời tab chat sẽ dừng lượt đang chờ và ẩn bàn phím.

Thiết lập trong `config/video_stories.json`:

```json
"chatbot": {"enabled": true, "mode": "research"}
```

`research` đang được chọn để thử ghi chú chưa duyệt và luôn có nhãn trên giao diện.
Đổi thành `approved` khi đã duyệt corpus; `enabled: false` tắt tab. Cần khởi động
lại khi đổi cấu hình. Bộ đọc có thể tạo index còn thiếu khi mở app lần đầu,
không dựng lại trong lượt hỏi. Xem [hướng dẫn chatbot](chatbot/README.md).

Mô hình `base` đã được tải vào `.venv-video/models` và kiểm tra khởi tạo CPU int8.
Dùng script trên sẽ dùng lại mô hình này. Lần kiểm tra thiết bị hiện chưa tìm
thấy mic; cần cắm/chọn mic rồi kiểm tra lại bằng `--list-mics`.

ZeroTTS 0.1.5 đã được cài trong `.venv-video` và trọng số tiếng Việt tải vào
`.venv-video/models/zerotts` (khoảng 1 GB). Bản cache tải về nằm ở
`.venv-video/models/hub`. ONNX Runtime trên Pi yêu cầu các file dữ liệu ngoài
cùng thư mục với model, nên cần chép file thật từ cache sang `zerotts`.
Để cài lại trên máy khác:

```bash
.venv-video/bin/python -m pip install zerotts
.venv-video/bin/python tools/tts/install_model.py
```

Lần tải model cần mạng; sau đó ứng dụng dùng cache model trong môi trường phát triển và phát giọng
ngoại tuyến. Trên Raspberry Pi 4 GB RAM, quá trình nạp và tổng hợp có thể chậm;
cần kiểm tra thực tế với loa và khi nhận dạng mic chạy cùng lúc.

Trên Pi/Linux, chạy trực tiếp `PYTHONPATH=src python3 -m cotu_app` cũng sẽ tự chuyển qua
script này nếu `.venv-video` đã có. Cách này xử lý lỗi `No module named 'vlc'`
khi Python hệ thống chưa có gói đã cài trong venv, đồng thời nạp PortAudio cục bộ.
Những bước cài bên dưới dành cho trường hợp chuẩn bị lại môi trường hoặc chuyển
sang máy khác.

## 1. Cài đặt trên Raspberry Pi

```bash
sudo apt update
sudo apt install vlc libvlc5 libportaudio2 python3-venv python3-tk
python3 -m venv --system-site-packages .venv-video
.venv-video/bin/python -m pip install -r requirements-video.txt
./run_video.sh --check
./run_video.sh
```

Môi trường ảo có `--system-site-packages` để dùng lại thư viện SPI/GPIO đã cài.
Nếu RFID trước đây chạy trong một môi trường ảo khác, hãy cài các gói trong
`requirements-video.txt` vào chính môi trường đó. Adapter RFID đã được giữ trong `vendor/mfrc522/`; bộ đọc nằm ở
`src/cotu_app/features/rfid/reader.py`.

Video nhúng sử dụng X11 trên Linux. Trên desktop Wayland cần XWayland và biến
`DISPLAY` hợp lệ; nếu không hiển thị được, thử phiên desktop X11 của Pi.
Phải chạy tại desktop có màn hình, không chạy qua SSH thuần văn bản.

`faster-whisper` dùng CPU int8. Gói CTranslate2/PyAV cần bản tương thích với
Python và hệ điều hành của Pi; nếu pip báo không có bản phù hợp, kiểm tra
hỗ trợ wheel cho hệ điều hành 64 bit/Python đang dùng. Chưa đo tốc độ trên Pi
trong phiên phát triển này. Có thể chuẩn bị lời thoại/bộ hỏi đáp trên máy mạnh
hơn để Pi dùng ngay mà không phải nhận dạng lại toàn bộ video.

Lần đầu nhận dạng cần mạng để tải mô hình `base`; sau khi có mô hình trong
cache, nhận dạng chạy tại máy. Có thể đặt `whisper_model` thành đường dẫn thư
mục mô hình CTranslate2 đã tải sẵn. Không dùng mô hình `.en` cho tiếng Việt.
Không cần API key. Âm thanh mic/video không được gửi tới dịch vụ nhận dạng.

## 2. Gán video cho từng thẻ

Ứng dụng đọc lại sáu UID từ `config/rfid_cards.json`:

| Nhân vật | MP4 trong cấu hình hiện tại |
| --- | --- |
| Già làng | `data/videos/person_5.mp4` |
| Người giữ lửa | `data/videos/person_5.mp4` |
| Người dẫn đường | `data/videos/person_5.mp4` |
| Người dệt vải | `data/videos/person_5.mp4` |
| Người làm nhạc cụ | `data/videos/person_5.mp4` |
| Người kể chuyện | `data/videos/person_5.mp4` |

Hiện chỉ có một MP4 gốc dùng chung cho sáu nhân vật; các nhân vật có nhóm
câu hỏi và giọng trả lời riêng, không phải sáu cảnh/nhân vật xuất hiện trong video.
Muốn thay video cho một nhân vật, chọn **Thiết lập → Chọn MP4**. Đường dẫn
lưu trong `config/video_stories.json`; đường dẫn tương đối tính từ file cấu hình.

- Quét thẻ đã gán: dừng video/giọng trả lời cũ, xóa nội dung hỏi đáp cũ,
  mở MP4 và nạp dữ liệu của đúng video mới.
- Thẻ chưa gán: chọn nhân vật, vào **Thiết lập → Gán thẻ cho nhân vật đang chọn**,
  rút thẻ, chờ 2 giây rồi quét lại. Ánh xạ này cũng được ứng dụng cũ sử dụng.
- Có thể chạm ảnh nhân vật để thử mà không cần thẻ. Hộp chọn nhân vật trong
  **Thiết lập** dùng để gán nội dung, không tự phát video.
- Chọn MP4 khác sẽ bỏ liên kết lời thoại/bộ câu hỏi cũ của nhân vật đó;
  cần chọn lại tài liệu phù hợp. Cache được phân biệt bằng SHA256 nội dung MP4.
- Các nút **Kể lại / Tiếp tục / Tạm dừng / Dừng** điều khiển video.
  F11 bật/tắt toàn màn hình, Esc thoát toàn màn hình.

## 3. “Học video” và trả lời chính xác

### Bộ hỏi đáp đã gắn cho video hiện có

Đã biên soạn **32 câu hỏi và đáp án, kèm 167 cách hỏi tương đương** cho
`data/videos/person_5.mp4` về **nhà Gươl của người Cơ Tu**. Mỗi câu trong JSON
có `character_id` và chỉ thuộc một nhân vật trả lời. Cả sáu nhân vật dùng cùng
MP4/SRT/JSON; ứng dụng nạp **đủ 32 câu của video**, bổ sung **5 câu từ tài liệu
mới** (mô tả bên dưới), và hiển thị tên người trả lời
trước mỗi câu. Có thể hỏi bất kỳ câu nào, dù đang phát video qua thẻ khác.

| Nhân vật | Số câu | Nhóm nội dung trong video |
| --- | ---: | --- |
| Già làng | 6 | Tổng quan, ý nghĩa, sử dụng và bảo tồn nhà Gươl. |
| Người giữ lửa | 5 | Vai trò cộng đồng, quy mô làng và thế hệ trẻ. |
| Người dẫn đường | 5 | Vị trí, bố cục làng và các vùng được nhắc đến. |
| Người dệt vải | 6 | Vật liệu, sàn, mái, chạm khắc và vật trưng bày. |
| Người làm nhạc cụ | 5 | Kết cấu, hệ cột và một hiện vật trong nhà Gươl. |
| Người kể chuyện | 5 | Gìn giữ, quần thể làng và nét đặc sắc của công trình. |

Đây là **phân vai trả lời theo chủ đề**, không khẳng định người dệt vải hoặc
người làm nhạc cụ xuất hiện trong video. Câu nào được hỏi thì nhân vật
được gán cho câu ấy đọc đáp án. Bộ JSON cũ không có `character_id` vẫn
hoạt động như trước: nhân vật đang chọn đọc đáp án.

- Bộ dùng trong ứng dụng: [`data/videos/person_5.questions.json`](../data/videos/person_5.questions.json).
- Bản dễ đọc để xem/sửa nội dung: [`data/videos/HOI_DAP_NHA_GUOL.md`](../data/videos/HOI_DAP_NHA_GUOL.md).
- Lược ghi thuyết minh có mốc thời gian: `data/videos/person_5.notes.srt`.
  Đây là bản biên tập các đoạn rõ nội dung, không phải phụ đề đầy đủ/nguyên văn;
  các lời phỏng vấn khó nghe không dùng để suy đoán chi tiết.

Đóng ứng dụng đang chạy, mở lại bằng `./run_video.sh --buttons`, chọn một
nhân vật đang có video rồi mở **2 · Em hỏi nhé!**. Đợi thanh trạng thái báo
**Đã nạp 37 câu hỏi** với cấu hình hiện tại. Không cần chọn JSON thủ công hay tải lại mô hình để nạp
bộ hỏi đáp. Nếu giao diện đang mở khi cấu hình được sửa, phải đóng/mở lại
để đọc cấu hình mới.

### Mẫu chuyện bổ sung từ file TXT

File [`Text cau chuyen co tu.txt`](../data/stories/Text%20cau%20chuyen%20co%20tu.txt) có 5 câu
hỏi và lời đáp của Già làng: nguồn gốc người Cơ Tu theo thần thoại quả bầu;
ý nghĩa “mất Gươl là mất làng”; cột tế x'nur và chim Tring; múa Tung tung
Da dá; nói lý, hát lý. Bộ [`co_tu_story.questions.json`](../data/stories/co_tu_story.questions.json)
giữ nguyên câu hỏi/lời đáp, bổ sung 29 cách hỏi ngắn để gõ hoặc nhận dạng mic.
Đây là nạp nội dung để tra cứu và đọc, không huấn luyện lại ZeroTTS hay Whisper.

`document_questions` trong `config/video_stories.json` trỏ tới bộ tài liệu này. Cả
sáu nhân vật nạp đủ 37 câu; 5 câu mới luôn do Già làng đọc bằng giọng `huuduc`.
Chúng nằm đầu nhóm Già làng, có nhãn **Mẫu chuyện**. Khi trả lời, màn hình ghi
tên file và số câu làm nguồn. Nội dung này đến từ tài liệu được cung cấp,
không được gắn thành lời thoại hoặc mốc thời gian của MP4.

Nguồn TXT được kiểm tra SHA-256 và đối chiếu nguyên văn từng lời đáp. Nếu sửa
file nguồn, nhập lại bộ hỏi đáp bằng lệnh sau rồi bấm **Nạp / học lời thoại**:

```bash
.venv-video/bin/python tools/stories/import_questions.py "data/stories/Text cau chuyen co tu.txt" --output data/stories/co_tu_story.questions.json
```

Lệnh giữ các cách hỏi ngắn khi câu hỏi gốc và nhân vật không đổi. Nếu sửa
câu hỏi gốc, cần thêm lại cách hỏi tương đương sau khi duyệt nội dung.

Có thể chạm câu mẫu hoặc thử nhập/nói:

| Nhân vật trả lời | Cách hỏi | Nội dung trả lời |
| --- | --- | --- |
| Già làng | Nhà Gươl là gì? | Ngôi nhà chung, nơi sinh hoạt cộng đồng của người Cơ Tu. |
| Già làng | Già làng ơi, cho con hỏi nhà gươi để làm gì ạ? | Nơi sinh hoạt chung, hội họp và bàn việc làng. |
| Người dệt vải | Mái nhà Gươl làm bằng gì? | Lá tự nhiên. |
| Người dệt vải | Sàn nhà Gươl làm bằng gì? | Tre, có khe hở giúp thông thoáng. |
| Già làng | Vì sao cần bảo tồn nhà Gươl? | Gìn giữ văn hóa để thế hệ sau hiểu, kế thừa và phát huy. |

Ứng dụng bỏ lời xưng hô mở đầu thông dụng, các từ lịch sự cuối câu và nhận
các cách gõ **nhà gươi / nhà gơi / nhà Gươl**. Các cách hỏi tương đương khác
nằm trong `aliases`. Câu chưa khớp vẫn có gợi ý để chọn, không tự lấy đáp án
gần giống cho một câu khác nghĩa. Ví dụ video không nêu chi phí xây dựng,
năm xây hay loài cây lấy lá lợp mái, nên không có đáp án cụ thể cho các câu đó.

Tất cả đáp án gắn với SHA256 của đúng MP4, có mốc `source_start`/`source_end`
để người phụ trách đối chiếu. Địa danh dùng theo lời kể của video. Khi thay
MP4 bằng câu chuyện khác, cần soạn/gắn bộ hỏi đáp của video mới.

### Cách ứng dụng nạp nội dung

Ứng dụng học **lời thoại tiếng Việt** trong MP4 bằng nhận dạng giọng nói,
lưu các đoạn có mốc thời gian vào `.video_cache`. Đây là lập chỉ mục lời thoại,
không huấn luyện lại mô hình và không phân tích hình ảnh. Chi tiết chỉ có
trong hình phải được người phụ trách bổ sung vào lời thoại hoặc bộ hỏi đáp.
Nhận dạng có thể sai tên riêng/tiếng địa phương; cần đối chiếu trước khi dùng.

Ứng dụng dùng dữ liệu theo thứ tự:

1. Bộ hỏi đáp của đúng MP4: trả lời bằng đáp án đã duyệt khi câu hỏi hoặc
   một cách hỏi trong `aliases` khớp. Không phân biệt hoa/thường, dấu tiếng Việt
   hoặc dấu câu; có xử lý lời xưng hô và các biến thể tên nhà Gươl nêu trên.
2. Nếu cách hỏi chưa khớp: gợi ý tối đa ba câu gần giống để người dùng chọn,
   không tự lấy đáp án chỉ vì câu hỏi có nhiều từ giống nhau.
3. Nếu lời thoại có đoạn phù hợp: hiển thị nguyên đoạn để đối chiếu, kèm mốc
   thời gian và nguồn. Đây là đoạn liên quan, không phải đáp án đã xác minh.
4. Nếu chưa có căn cứ: thông báo chưa có câu trả lời đã duyệt. Chỉ đáp án
   đã duyệt được đọc ra loa.

Nút **Nạp / học lời thoại** không tự sinh đáp án cho một MP4 bất kỳ: khi chưa
gắn bộ hỏi đáp, nó chỉ nhận dạng/lưu lời thoại. Nhận dạng không bảo đảm đúng
100%. Bộ 32 câu ở trên đã được chuẩn bị riêng cho video hiện có; bộ 15 câu
trong `story_questions.py` không tự gắn vào MP4 vì nội dung có thể khác nhau.

### Dùng bộ hỏi đáp đã duyệt

Xem video, soạn câu hỏi và đáp án tương ứng, rồi lấy mã SHA256:

```bash
./run_video.sh --video-sha256 data/videos/person_1.mp4
```

Sao chép `data/videos/questions.example.json` thành `data/videos/person_1.questions.json`.
Thay `video_sha256` bằng kết quả lệnh trên; thay toàn bộ nội dung mẫu bằng
câu hỏi và đáp án đã đối chiếu với video. Thêm các cách hỏi nói tự nhiên vào
`aliases`, chẳng hạn câu ngắn và câu có “cho con hỏi”. Không lặp lại cùng
một câu/cách hỏi trong bộ câu hỏi, kể cả biến thể chỉ khác dấu tiếng Việt.

Chọn nhân vật → **Thiết lập → Chọn bộ hỏi đáp JSON** → chọn file đã soạn →
**Em hỏi nhé! → Nạp / học lời thoại**. Có bộ đã duyệt thì dùng được ngay, không cần
nhận dạng lại toàn bộ video. Đổi nội dung MP4 sẽ đổi SHA256; bộ cũ bị từ chối
cho đến khi được kiểm tra và gắn lại đúng video.

### Dùng lời thoại/phụ đề có sẵn

Chọn **Thiết lập → Chọn lời thoại TXT/SRT** rồi nạp lại. TXT dùng UTF-8,
mỗi đoạn một dòng; SRT có mốc thời gian chuẩn. Lời thoại do người dùng chọn
được ưu tiên hơn nhận dạng tự động. Có thể dùng đồng thời với bộ hỏi đáp.
Cần tự kiểm tra TXT/SRT có đúng nội dung MP4; file này không có SHA256 ràng buộc.

Nếu không chọn TXT/SRT và không có bộ câu hỏi, nút **Nạp / học lời thoại**
sẽ nhận dạng âm thanh MP4; lần sau dùng cache khi video và tên mô hình không đổi.
Khi đổi mô hình tại cùng đường dẫn, hãy xóa cache liên quan để nhận dạng lại.

## 4. Mic và giọng trả lời

```bash
./run_video.sh --list-mics
```

Trong **Thiết lập**, nhập số thiết bị có ngõ vào hoặc một phần tên mic duy nhất,
rồi **Lưu mic**. Để trống sẽ dùng mic mặc định. Nạp lại nội dung sau khi lưu.
Thay `record_seconds` trong cấu hình nếu muốn thời gian thu khác, từ 2 đến 30
giây; mặc định 8 giây. Đóng/mở ứng dụng sau khi sửa cấu hình bên ngoài.

Quét thẻ hoặc chọn nhân vật, đợi nạp nội dung xong, mở **Em hỏi nhé! → Hỏi bằng mic**.
Ứng dụng tạm dừng video và dừng giọng trả lời trước khi thu. Chỉ nói khi
thanh trạng thái hiện **MIC ĐANG THU**. Thu đủ số giây đã đặt, ứng dụng nhận
dạng rồi hiện câu vừa nghe và tra đúng bộ hỏi đáp của video hiện tại.
Nếu nghe sai, sửa ở ô nhập hoặc chọn câu mẫu bên trái. Không bật mic liên tục.
Sau khi trả lời, bấm **Tiếp tục** để nghe tiếp video.

Đáp án được hiển thị và đọc bằng ZeroTTS theo `character_id` của câu hỏi;
nếu bộ JSON cũ không có trường này thì dùng nhân vật đang chọn. Bản RFID
không video cũng dùng cùng bộ giọng. Cấu hình nằm ở `config/tts_voices.json`:

| Nhân vật | Giọng ZeroTTS | Nhịp đọc |
| --- | --- | --- |
| Già làng | `huuduc` (nam lớn tuổi) | 0,88 |
| Người giữ lửa | `giahuy` (nam trẻ) | 1,00 |
| Người dẫn đường | `quangminh` (nam trẻ) | 1,00 |
| Người dệt vải | `kimoanh` (nữ trung niên) | 0,95 |
| Người làm nhạc cụ | `tiendat` (nam trẻ) | 1,00 |
| Người kể chuyện | `maichi` (nữ trẻ) | 1,00 |

Mỗi nhân vật giữ nguyên giọng qua các lần mở ứng dụng. Giọng già
làng được dùng cả khi ông kể truyện của nhân vật khác. Nếu thiếu model/loa,
văn bản vẫn ở màn hình. Các tác vụ nhận dạng chạy trong tiến trình riêng;
đổi thẻ sẽ bỏ kết quả cũ, đóng cửa sổ sẽ dừng các tiến trình nền.

ZeroTTS chạy trong một tiến trình giữ model trong RAM, không nạp lại mỗi câu
hoặc mỗi lần đổi giọng. Khi nạp bộ hỏi đáp, ứng dụng tự chuẩn bị WAV ở nền,
báo số câu đã sẵn sàng dưới ô nhập. Câu được bấm sẽ được ưu tiên; WAV có sẵn
phát qua luồng riêng mà không đợi tác vụ tổng hợp đang chạy. Các file ở
`.tts_cache` được dùng lại sau khi mở lại ứng dụng. Nội dung, giọng, tốc độ
hoặc model thay đổi thì tự tạo file mới; lần đầu chưa có WAV vẫn cần chờ.

Để chuẩn bị đủ 37 đáp án hiện tại (32 từ video, 5 từ tài liệu) trước khi sử dụng, chạy:

```bash
./run_video.sh --prepare-tts
```

Lệnh không mở loa hay giao diện, chỉ tạo phần còn thiếu. Chờ thông báo
`Đã chuẩn bị đủ 37 câu trả lời.` rồi mở ứng dụng như bình thường.

Nếu chữ hiện nhưng không có tiếng, chạy `./run_video.sh --check-audio` trên đúng
desktop Pi đang dùng. Khi không có thiết bị phát, cần cắm/chọn loa HDMI hoặc USB
và xác nhận hệ thống nhìn thấy loa trước. `config/tts_output.json` hiện chọn thiết bị
`alsa-name:USB Audio Device` để chọn trực tiếp ngõ ALSA của loa USB, bỏ qua
các ngõ ảo trùng tên. Tên này vẫn dùng được khi số card USB thay đổi. Trên Pi
đã kiểm tra, loa này là PortAudio `#1`
(`hw:2,0`); `#0` là HDMI (`hw:1,0`). Chỉ số PortAudio có thể đổi, nên dùng tên
ổn định hơn. Nếu có nhiều loa USB vật lý cùng tên, dùng số `#N` được in ra để lưu lựa chọn:

```bash
./run_video.sh --set-audio-device 1
./run_video.sh --check-audio
./run_video.sh
```

Lựa chọn này được dùng cho cả ứng dụng video và RFID. Có thể ghi đè tạm thời
bằng `NHARONG_TTS_OUTPUT_DEVICE=1 ./run_video.sh`.
ZeroTTS thử định dạng PCM 16 bit và tần số 48/44,1 kHz phù hợp với loa USB.
Màn hình sẽ hiển thị lỗi cụ thể từ tiến trình ZeroTTS nếu phát âm thanh thất bại.
Tiến trình phát tự làm mới danh sách PortAudio một lần nếu không tìm thấy loa
sau khi rút/cắm USB; model và các WAV đã tạo vẫn được giữ. Lỗi không tìm thấy
loa và lỗi nhiều loa trùng tên có thông báo riêng, kèm các ngõ ra hiện có.

Để tách lỗi loa khỏi lỗi tổng hợp giọng, chạy hai phép thử **trên desktop Pi**:

```bash
./run_video.sh --test-audio  # tiếng bíp ngắn qua đúng loa ZeroTTS, không nạp model
./run_video.sh --test-tts    # đọc câu thử bằng giọng Già làng qua loa đó
```

`--check-audio` chỉ kiểm tra cấu hình/định dạng, không phát tiếng. Nếu
`--test-audio` im lặng, kiểm tra âm lượng và ngõ ra trước; nếu nghe bíp nhưng
`--test-tts` lỗi, chép nguyên dòng `Không chạy được: ...` ở Terminal để xác
định bước nạp model, tổng hợp hay phát âm thanh. Nếu cả hai lệnh báo thành
công nhưng im lặng, xem lại âm lượng phần cứng/hệ thống và kết nối loa.

### Kiểm tra bút Baseus BS-OH065

Bút đang kết nối có đầu thu `fff1:001a — Baseus Presenter`. Lần kiểm tra ngày
16/10/2026 thấy bốn giao diện USB class `03` (HID), không có đầu vào thu âm
ALSA/PipeWire. `./run_video.sh --list-mics` chỉ hiện HDMI `0 in, 2 out`.
Đổi số mic trong cấu hình chưa thể lấy âm thanh từ cổng HID này.

Trang thông số của [Baseus Việt Nam](https://baseus.vn/products/but-trinh-chieu-thong-minh-baseus-orange-dot-ai-voice)
ghi BS-OH065 có mic và hỗ trợ Windows/macOS; chưa công bố hỗ trợ Linux.
Chưa xác minh được driver đọc mic tích hợp của đúng thiết bị này trên Pi.
Có dữ liệu HID không đồng nghĩa dữ liệu đó là âm thanh; cần kiểm tra gói tin
khi bấm nút trước khi viết phần tích hợp.

Công cụ `kiem_tra_baseus.py` chỉ dùng thư viện chuẩn Python, không cài driver,
không gửi lệnh USB và không đổi quyền thiết bị. Xem thiết bị, không cần sudo:

```bash
cd /home/admin/NhaRongCoTu
python3 tools/diagnostics/baseus.py
```

Để kiểm tra dữ liệu thực, mở Terminal trên chính Pi và chạy:

```bash
cd /home/admin/NhaRongCoTu
sudo python3 tools/diagnostics/baseus.py --capture
```

Cần sudo vì các cổng `/dev/hidraw*` của bút hiện chỉ cho root đọc. Nhập mật
khẩu ở Terminal nếu được yêu cầu. Bật bút, tạm dừng video, làm theo từng bước:

1. Nhấn Enter, để bút nằm yên trong 6 giây.
2. Nhấn Enter, chờ dòng **ĐANG ĐỌC**, nhấn giữ nút mic và nói câu thử trong
   khoảng 10 giây, sau đó thả nút.
3. Nhấn Enter, chờ **ĐANG ĐỌC**, bấm một lần nút mic, nói câu thử rồi bấm lại
   để dừng trong khoảng 10 giây.
4. Nhấn Enter, chờ **ĐANG ĐỌC**, bấm nút chuyển trang vài lần trong 6 giây.

Báo cáo `baseus_capture_*.json` nằm trong `reports/diagnostics/`, gồm dữ liệu thô
của riêng đầu thu Baseus; không thu bàn phím khác và không gửi lên mạng.
Công cụ không nhận dạng tiếng nói và chưa tạo ra file âm thanh nghe được.
Cần đối chiếu số gói, độ dài và nội dung giữa các bước để xác định hướng xử lý:

- Có luồng dữ liệu thay đổi khi nói: tiếp tục xác định định dạng/giải mã;
  chưa đủ để khẳng định đó là âm thanh hoặc đã dùng được mic.
- Chỉ thấy sự kiện nút: có thể nghiên cứu dùng bút để điều khiển nút hỏi;
  chưa lấy được giọng nói. Chương trình hiện chưa gán nút của bút.
- Không thấy gói: kiểm tra bút có bật/pin/ghép nối và thử nút chuyển trang.
  Cũng có khả năng mic cần lệnh kích hoạt riêng từ phần mềm Baseus; phép thử
  đọc thụ động này không loại trừ khả năng đó.

## 5. Nhập câu hỏi tiếng Việt có dấu

### Bàn phím cảm ứng khi toàn màn hình

Đã bổ sung bàn phím ngay bên trong ứng dụng để nhập câu hỏi khi bàn phím
ảo của desktop không xuất hiện ở chế độ toàn màn hình. Không cần cài thêm
gói hoặc thay cấu hình hệ điều hành cho bàn phím tích hợp.

1. Đóng ứng dụng cũ và mở lại bằng `./run_video.sh --buttons`.
2. Bật **Toàn màn hình**, mở **2 · Em hỏi nhé!** rồi chạm ô **Em muốn hỏi**.
   Bàn phím tích hợp mở rộng vùng nội dung; ô nhập chữ lớn vẫn ở phía trên.
   Danh sách hỏi đáp và hàng nút mic tạm ẩn để dành chỗ cho phím lớn, có
   khoảng cách giữa các phím. Khi ẩn bàn phím, các mục này xuất hiện lại.
3. Ngoài chế độ toàn màn hình, bấm **Bàn phím** bên cạnh ô nhập để mở/ẩn.
4. Gõ câu hỏi, bấm **Gửi** trên bàn phím hoặc **Gửi câu hỏi →** cạnh ô nhập.
   Bàn phím tự ẩn để xem câu trả lời. Nút **Ẩn** chỉ đóng bàn phím, giữ câu đã gõ.

Bàn phím có **ABC/abc**, số/ký hiệu qua **123**, xóa lùi **⌫**, **Xóa hết**,
**Dấu cách** và mũi tên để di chuyển con trỏ. Bấm **Dấu Việt** để mở trang
riêng với các chữ **ă â ê ô ơ ư đ** và các phím lớn
**Sắc / Huyền / Hỏi / Ngã / Nặng / Bỏ dấu**; bấm **ABC** ở hàng dưới để
trở lại trang chữ. Phím chữ dùng cỡ 20 đậm; phím cao tối thiểu 50 px.

Các phím dấu tác động lên **nguyên âm ngay trước con trỏ**: gõ `ơ`, bấm
**Hỏi** được `ở`; gõ `ê`, bấm **Nặng** được `ệ`. Hãy thêm dấu ngay sau
nguyên âm rồi gõ tiếp phần còn lại của từ. **Bỏ dấu** xóa dấu thanh nhưng
giữ dấu mũ/móc, ví dụ `ố → ô`. Bàn phím tích hợp nhập chữ trực tiếp, không dùng
quy tắc Telex. Bàn phím vật lý và bộ gõ IBus vẫn có thể dùng như trước.

Bàn phím nằm trong cùng cửa sổ Tk nên không cần hiện một cửa sổ bàn phím
khác lên trên cửa sổ fullscreen. Đã kiểm tra bố cục và nhập/xóa/gửi bằng màn
hình ảo 800×480; cần thử lại thao tác chạm trên desktop Pi đang sử dụng.
Tham khảo API [Tk Entry](https://www.tcl-lang.org/man/tcl/TkCmd/entry.html).

### Bộ gõ IBus cho bàn phím vật lý / bàn phím desktop

Chạy trên Terminal của desktop Raspberry Pi bằng tài khoản đang sử dụng:

```bash
cd /home/admin/NhaRongCoTu
./tools/setup/install_vietnamese_input.sh
```

Script cài `ibus`, `ibus-unikey`, `ibus-gtk3`, `im-config` và chạy
`im-config -n ibus` cho tài khoản hiện tại. Hệ thống sẽ hỏi mật khẩu sudo tại
Terminal; không cần gửi mật khẩu vào chat. Không chạy cả script bằng sudo,
vì cấu hình bộ gõ cần thuộc tài khoản desktop của bạn.

Sau khi cài thành công:

1. Lưu công việc, đăng xuất desktop và đăng nhập lại.
2. Mở Terminal và chạy `ibus-setup`.
3. Trong **Input Method**, chọn **Add → Vietnamese → Unikey → Add**.
   Nếu không thấy Vietnamese, mở danh sách đầy đủ bằng dấu ba chấm/Show all.
4. Chọn Unikey trên biểu tượng bộ gõ ở thanh hệ thống. Trong Preferences của
   Unikey chọn **Telex** nếu muốn nhập bằng cách dưới đây.
5. Mở lại ứng dụng bằng `./run_video.sh`, đặt con trỏ vào ô nhập câu hỏi.

Ví dụ Telex: `aa → â`, `aw → ă`, `ee → ê`, `oo → ô`, `ow → ơ`, `uw → ư`,
`dd → đ`; các phím `s/f/r/x/j` thêm dấu sắc/huyền/hỏi/ngã/nặng.
Gõ `tieengs Vieetj` rồi nhấn cách để thử **tiếng Việt**.

Việc cài IBus chưa hoàn thành trong phiên hỗ trợ vì `sudo` yêu cầu mật khẩu.
Cần chạy script trên máy để hoàn tất. Ứng dụng đã dùng ô nhập Unicode, không
cần đổi ngôn ngữ giao diện hệ điều hành để gõ tiếng Việt.

Tham khảo: [gói IBus UniKey của Debian](https://packages.debian.org/trixie/ibus-unikey),
[cấu hình bộ gõ với im-config](https://manpages.debian.org/trixie/im-config/im-config.8.en.html).

## 6. Kiểm tra

```bash
./tools/test.sh -v
./tools/test.sh -v
./tools/test.sh -v
./run_video.sh --check
./run_video.sh --no-rfid
```

`--check` kiểm tra cấu hình, ánh xạ thẻ và sự hiện diện của các module Python;
trả mã 1 nếu thiếu module. Lệnh in những MP4 chưa có nhưng không mở màn hình,
mic, GPIO, tải mô hình hoặc xác nhận libVLC hoạt động.
`--no-rfid` vẫn dùng video/mic thật, chỉ tắt tiến trình đọc thẻ.

Trên Pi cần thử: đúng MP4 cho cả sáu thẻ; quét lại và đổi thẻ giữa lúc trả lời;
đổi thẻ trong lúc học/thu mic; loa và mic không bị vọng video; câu không thuộc
bộ hỏi đáp; MP4 thiếu âm thanh; bộ câu hỏi sai SHA256; đóng khi đang nhận dạng.
Đã kiểm tra giao diện trên màn hình ảo ở 800×480 và 1100×720: chọn đủ sáu
nhân vật, hỏi đáp, trạng thái mic và chọn nhân vật trong Thiết lập. Chưa kiểm
tra phát MP4, RFID, mic và thao tác chạm trên phần cứng thật trong lần sửa giao diện này.

Tài liệu API đối chiếu:
[python-vlc](https://python-vlc.readthedocs.io/en/latest/api/vlc/MediaPlayer.html),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[sounddevice](https://python-sounddevice.readthedocs.io/en/0.5.3/api/streams.html).

## 7. Bốn nút bấm cơ ngoài trên Raspberry Pi 5

Phần nút được tích hợp trong `src/cotu_app/app/desktop.py`, dùng `src/cotu_app/features/gpio/buttons.py`.
Mặc định gán cho **4 người đầu tiên** (`person_1` đến `person_4`). Có thể thay
bất kỳ nút nào bằng Già làng hoặc Người kể chuyện theo cấu hình bên dưới.
RFID và màn hình cảm ứng vẫn dùng đồng thời được.

### Chuẩn bị và đấu dây

Chuẩn bị 4 nút nhấn nhả **thường hở (NO)**, dây Dupont và cầu đấu/breadboard
để chia GND chung. Nút có chân **COM/NO/NC**: dùng **COM và NO**. Nếu nút
có đèn, phần dưới chỉ đấu tiếp điểm nút; chân đèn cần mạch riêng phù hợp.

**Tắt Pi và rút nguồn trước khi đấu dây.** Các số GPIO trong code là **BCM**,
khác số thứ tự chân trên hàng 40 chân. Mỗi nút nối giữa một GPIO và GND;
chương trình bật điện trở kéo lên nội, không cần cấp nguồn cho tiếp điểm nút.
**Không nối GPIO với 5V.** Xem sơ đồ chính thức bằng lệnh `pinout` trên Pi,
hoặc `.venv-video/bin/python -m gpiozero.pinout`.

| Nút | Nhân vật mặc định | GPIO BCM | Chân vật lý trên Pi 5 | Đầu còn lại |
| --- | --- | --- | --- | --- |
| 1 | Người giữ lửa (`person_1`) | GPIO17 | **11** | GND |
| 2 | Người dẫn đường (`person_2`) | GPIO27 | **13** | GND |
| 3 | Người dệt vải (`person_3`) | GPIO23 | **16** | GND |
| 4 | Người làm nhạc cụ (`person_4`) | GPIO24 | **18** | GND |

Dùng **GND chân vật lý 6** làm đường chung cho cả 4 nút (hoặc chân GND khác
như 9, 14, 20). Chia đường GND qua cầu đấu, không cố cắm nhiều đầu Dupont
lên một chân Pi.

```text
Pi 5                                       Nút nhấn thường hở
GPIO17 — chân 11 ─────────────────────────── NO [Nút 1] COM ──┐
GPIO27 — chân 13 ─────────────────────────── NO [Nút 2] COM ──┤
GPIO23 — chân 16 ─────────────────────────── NO [Nút 3] COM ──┤
GPIO24 — chân 18 ─────────────────────────── NO [Nút 4] COM ──┤
GND    — chân  6 ───────────────────────────────────────────┘
```

Với nút tact 4 chân, xác định hai nhóm chân bằng đồng hồ đo: các chân cùng
nhóm luôn thông nhau, hai nhóm chỉ thông khi nhấn. Lấy **một chân ở mỗi
nhóm** để đấu GPIO và GND; lấy nhầm hai chân luôn thông sẽ thành giữ nút.

**Đã đối chiếu thư viện RFID đang dùng tại
`vendor/mfrc522/MFRC522.py`: RST mặc định là GPIO22
(chân vật lý 15). Không dùng GPIO22 cho nút.** Các chân SPI0 GPIO7–11 và
GPIO25 cũng được loại khỏi cấu hình nút để tránh trùng dây RFID thông dụng.
Nếu đầu đọc đã đấu RST khác mặc định, kiểm tra lại chân RST thực tế trước
khi đổi cấu hình. Không bật chức năng SPI1/UART/HAT khác trên các GPIO của nút.

### Cài thư viện và thử từng nút

Trên Terminal của Pi:

```bash
cd /home/admin/NhaRongCoTu
sudo apt update
sudo apt install python3-gpiozero python3-lgpio
./run_video.sh --check --buttons
./run_video.sh --test-buttons
```

`--test-buttons` chỉ đọc 4 nút và in tên nhân vật vào Terminal; không mở
màn hình, RFID, mic hay mô hình nhận dạng. Bấm lần lượt từng nút rồi nhấn
**Ctrl+C** để thoát. **Đóng ứng dụng kể chuyện trước khi thử** để hai chương
trình không cùng chiếm GPIO. Lệnh thử hoạt động được qua SSH.

Venv cần được tạo với `--system-site-packages` như mục 1 để thấy hai gói apt.
Nếu venv riêng không thấy gói, có thể cài vào chính venv đó:

```bash
.venv-video/bin/python -m pip install 'gpiozero>=2,<3' 'lgpio>=0.2.2,<1'
```

Code dùng `LGPIOFactory` cho Pi 5, tự chọn gpiochip theo GPIO Zero; không ép
`gpiochip4`, vì chỉ số có thể khác theo phiên bản kernel. Không dùng backend
RPi.GPIO cũ cho phần nút này. Nếu báo quyền truy cập `/dev/gpiochip*`, kiểm
tra tài khoản thuộc nhóm `gpio`; nếu chưa có, chạy `sudo usermod -aG gpio "$USER"`
rồi đăng xuất/đăng nhập lại. Nếu báo GPIO đang bận, đóng bản ứng dụng/lệnh thử
khác và kiểm tra thiết bị đang dùng chân đó.

### Chạy kể chuyện bằng nút

```bash
# Dùng đồng thời nút cơ, RFID và cảm ứng:
./run_video.sh --buttons

# Chỉ dùng nút cơ và cảm ứng, không mở đầu đọc RFID:
./run_video.sh --buttons --no-rfid
```

Chạy `./run_video.sh` không có `--buttons` sẽ không mở GPIO của các nút.
Nếu khởi tạo nút thất bại, ứng dụng báo **Lỗi nút GPIO** ở trạng thái/Terminal;
vẫn có thể chọn nhân vật bằng màn hình hoặc RFID. Dùng `--test-buttons` để
xem lỗi phần nút riêng, không bị trạng thái RFID che mất.

- Bấm một nút: tự chuyển về **Nghe chuyện** và phát MP4 của đúng người đó.
- Bấm lại cùng nút: kể lại từ đầu. Giữ nút không lặp phát; thả rồi bấm lại.
- Bấm nút khác trong lúc video/hỏi đáp/thu mic: dừng chuyện/giọng trả lời cũ,
  hủy kết quả tác vụ cũ rồi chuyển sang người mới, như khi quét thẻ.
- Chống dội tiếp điểm 80 ms. GPIO đưa sự kiện qua hàng đợi để giao diện xử lý.
- Khi đóng ứng dụng hoặc thoát lệnh thử, chương trình trả lại các chân nút.

Cần gán đủ MP4 cho 4 người ở **Thiết lập → Chọn MP4** hoặc chép đúng file:

```text
data/videos/person_1.mp4
data/videos/person_2.mp4
data/videos/person_3.mp4
data/videos/person_4.mp4
```

Hiện kho dự án chỉ có `data/videos/person_5.mp4`; các file cho 4 người trên cần
được bổ sung/gán trước khi nghe bằng nút. Thiếu file sẽ báo trên màn hình.
Việc nạp hỏi đáp/nhận dạng vẫn diễn ra như khi chọn nhân vật bằng cảm ứng.

### Đổi nhân vật hoặc chân nút

Đóng ứng dụng, sửa mục `gpio_buttons` trong `config/video_stories.json`, rồi mở lại:

```json
"gpio_buttons": {
  "person_1": 17,
  "person_2": 27,
  "person_3": 23,
  "person_4": 24
}
```

Mỗi cặp là **mã nhân vật: số GPIO BCM**. Ví dụ, đổi `"person_4": 24` thành
`"person_5": 24` để nút 4 phát Người kể chuyện, hoặc `"elder": 24` để phát
Già làng. Giữ đúng 4 mã nhân vật khác nhau và 4 GPIO khác nhau; các mã hợp lệ
gồm `elder`, `person_1` đến `person_5`. Cấu hình cũ chưa có mục này vẫn dùng
bốn nút mặc định. Chương trình từ chối số chân trùng hoặc chân dành cho RFID.

Đã có kiểm tra tự động bằng GPIO giả cho ánh xạ, bấm/thả/giữ, chuyển chuyện
và giải phóng GPIO. **Chưa kiểm chứng nút bấm và dây nối trên Pi 5 thật trong
phiên này**; cần chạy `--test-buttons` rồi thử phát đủ 4 MP4 trên phần cứng.

Tài liệu đối chiếu:
[GPIO và pinout Raspberry Pi](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio),
[GPIO Zero Button: nối GPIO–GND, pull-up và chống dội](https://gpiozero.readthedocs.io/en/stable/api_input.html#button),
[backend LGPIO và hỗ trợ Pi 5](https://gpiozero.readthedocs.io/en/stable/api_pins.html#lgpio).
