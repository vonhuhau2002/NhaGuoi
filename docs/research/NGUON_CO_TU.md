# Hồ sơ tìm và đối chiếu nguồn Cơ Tu

## Kết luận về “câu chuyện gốc”

Chưa xác định được tài liệu gốc khớp toàn bộ năm đáp án trong `docs/Text cau chuyen co tu.txt`. Năm chủ đề không đủ để suy ra có một truyện duy nhất bao quát chúng. Không ghép các bài viết đã tìm thành một nguyên tác giả định.

Đã tìm được nguồn nghiên cứu có tổng thuật dị bản nguồn gốc và nguồn điền dã ghi truyền thuyết dòng họ. Đây là dữ liệu nền tốt hơn việc chỉ tìm cách hỏi giống năm câu mẫu; vẫn cần tìm bản sưu tầm đầy đủ và duyệt nội dung trước khi dùng cho khách.

## Các nguồn đã lưu

Mã raw và SHA-256 đầy đủ nằm trong [nhật ký tải](../../data/chatbot/manifests/downloads.jsonl). Thông tin đối chiếu mới nhất nằm ở [source_reviews.json](../../data/chatbot/manifests/source_reviews.json). Các trạng thái ban đầu trong `sources.json` chỉ là danh mục ứng viên.

| Mã | Tài liệu và xuất xứ | Kết quả sử dụng |
|---|---|---|
| S01 | File mẫu của người dùng | Raw TXT; cách ly khỏi kho bằng chứng cho tới khi đối chiếu |
| S02 | Đinh Thị Hựu, [Truyền thuyết về dòng họ của người Cơ Tu](https://vannghedanang.org.vn/truyen-thuyet-ve-dong-ho-cua-nguoi-co-tu-8931.html), 05/07/2021 | Raw HTML; nguồn điền dã, có nhiều dị bản; [ghi chú](../../data/chatbot/clean/S02.md) |
| S03 | Hà Nam, [Bên trong ngôi nhà được người Cơ Tu xem là “hồn làng”](https://dantocphattrien.vietnamnet.vn/ben-trong-ngoi-nha-duoc-nguoi-co-tu-xem-la-hon-lang-77109.html), 29/07/2026 | Raw HTML; phỏng vấn trong cộng đồng; [ghi chú](../../data/chatbot/clean/S03.md) |
| S04 | Trần Tấn Vịnh, [Nghệ thuật trang trí trên cây cột lễ của dân tộc Cơtu](https://vanhoanghethuat.vn/nghe-thuat-trang-tri-tren-cay-cot-le-cua-dan-toc-cotu-77751251.html), VHNT 472, 8/2021; web 11/09/2021 | Raw HTML; phân tích cột lễ; [ghi chú](../../data/chatbot/clean/S04.md) |
| S05 | Nguyễn Văn Sơn, [Biểu tượng chim Tring trong văn hóa Cơ Tu](https://baodaklak.vn/channel/9803/202010/bieu-tuong-chim-tring-trong-van-hoa-co-tu-5703869/), 11/10/2020 | Raw HTML; nguồn văn hóa, chưa phải định danh động vật học; [ghi chú](../../data/chatbot/clean/S05.md) |
| S06 | Ngọc Anh–VOV5, [Tân tung da dă](https://vov4.vov.vn/cotu/xoong-pra-xa-nay-coh-guol-duoi-mai-nha-guol/tan-tung-da-da-prmua-ty-danh-ang-acoon-coh-co-tu-429010.vov4), 13/09/2023 | Raw HTML; có phỏng vấn, hai phần ngôn ngữ; [ghi chú](../../data/chatbot/clean/S06.md) |
| S07 | Hứa Chung, [Về Quảng Nam nghe nói lý, hát lý Cơ Tu](https://baotintuc.vn/ve-quang-nam-nghe-noi-ly-hat-ly-co-tu-n20120120213845120.htm), 20/01/2012 | Raw HTML; ghi chép và phỏng vấn; [ghi chú](../../data/chatbot/clean/S07.md) |
| S08 | Bản nghiên cứu ở [kho DLU](https://scholar.dlu.edu.vn/thuvienso/bitstream/DLU123456789/186491/1/CVv517S042022069.pdf) | Tải lỗi chứng chỉ; được thay bằng bản tạp chí S12, không đếm thêm nguồn độc lập |
| S09 | [URL PDF VJOL](https://vjol.info.vn/index.php/ncdt/article/download/51704/42568/) | Trả HTML đăng nhập; không có PDF; tiêu đề/tác giả chưa được xác minh |
| S10 | Đặng Quốc Minh Dương, Lê Văn Thiện, [Motif đồng sinh trong truyện dân gian Việt Nam](https://js.vhu.edu.vn/index.php/vhujsvn/article/download/356/182/312), 8(4), 2022 | Raw PDF 13 trang; nghiên cứu so sánh, chỉ dùng đầu mối; [ghi chú](../../data/chatbot/clean/S10.md) |
| S11 | [Đưa vũ điệu dâng trời của người Cơ Tu vào phục vụ du khách](https://bvhttdl.gov.vn/dua-vu-dieu-dang-troi-cua-nguoi-co-tu-vao-phuc-vu-du-khach-20220719090105499.htm), Bộ VHTTDL, 19/07/2022 | Raw HTML; nội dung đăng lại có phỏng vấn Báo Tổ Quốc; [ghi chú](../../data/chatbot/clean/S11.md) |
| S12 | Hoàng Thị Thêm, [Cấu trúc loại mục từ “thần thoại tộc người” trong Từ điển bách khoa Thần thoại Việt Nam](https://jol.vn/index.php/tudienhoc/vi/article/download/616/551), 4(78), 7/2022, tr.69–73 | Raw PDF 5 trang từ tạp chí; mục từ mẫu ở tr.71–72; [ghi chú](../../data/chatbot/clean/S12.md) |

Tổng: 12 mã ứng viên; 10 bản raw tải thành công gồm cả file người dùng; hai lỗi tải được ghi nhận. Chỉ đọc công khai trên web chưa đồng nghĩa có quyền tái phát hành toàn văn. Bản sạch hiện tại là ghi chú biên tập ngắn, giữ liên kết tới raw, chưa phải corpus đầy đủ được duyệt.

## Đối chiếu năm chủ đề

| Chủ đề mẫu | Bằng chứng đã có | Phần cần giữ lại để kiểm tra |
|---|---|---|
| Nguồn gốc, hồng thủy, quả bầu | S12 có nhiều bản kể riêng; S02 có truyền thuyết dòng họ | Không nối các bản thành một cốt truyện; chưa xác minh chuỗi tình tiết khớp mẫu |
| Gươl | S03 có mô tả và lời người trong cộng đồng | Tránh khẳng định mọi gươl cùng cấu trúc/trang trí hoặc trích lời mẫu như nguyên văn người kể |
| Cột lễ, Tring | S04 phân tích bộ phận cột; S05 mô tả ý nghĩa biểu tượng | Tên phiên âm, cây nêu/cột lễ; cách gọi “chim trĩ rừng” chưa được nguồn đã đọc xác nhận |
| Tân tung, Da dá | S06 có lời Bríu Pố; S11 có thực hành ở bối cảnh du lịch | Phân biệt nghi lễ và biểu diễn; các cách viết tên điệu múa cần từ điển thuật ngữ |
| Nói lý, hát lý | S07 mô tả ứng khẩu, ví von và đối đáp | Chưa tìm căn cứ cho từng câu trích trong mẫu; không gọi câu biên soạn là lời cổ truyền nguyên văn |

## Đầu mối truy nguyên tiếp theo

1. **Trần Nguyễn Khánh Phong, Văn học dân gian dân tộc Cơ Tu, NXB Khoa học xã hội, 2015.** S12 dẫn sách; [Thư mục Quốc gia 2015](https://nlv.gov.vn/dmdocuments/tmqg_2015_part_04.pdf) xác nhận tên, tác giả và 478 trang. Đây mới là xác nhận thư mục, chưa tải được sách. Cần đối chiếu mục lục và trang truyện khi có bản đọc.
2. **Trần Nguyễn Khánh Phong, Chàng Phuật Nà (Truyện cổ Tà Ôi, Cơ Tu), NXB Thuận Hóa, 2006.** Đầu mối từ tài liệu tham khảo S12; chưa kiểm tra bản sách.
3. **Hội Văn nghệ Dân gian Đà Nẵng, Truyện kể dân gian đất Quảng, NXB Đà Nẵng, 2007** và **Bh’riu Liếc, P’ra Cơ Tu, NXB Hội Nhà văn, 2018.** Đầu mối từ S02; chưa tải toàn văn.
4. **Đỗ Như Túy, Mai Văn Tấn, Truyện cổ Vân Kiều, Cơ Tu, NXB Hội Nhà văn, 2018.** Đầu mối trong tham khảo chung S12; chưa đối chiếu bản sách, không suy ra mọi dị bản của mục từ đều trích từ riêng cuốn này.

Tìm tiếp ở thư viện, nhà xuất bản, bảo tàng hoặc đơn vị sưu tầm theo tên tác giả và tên truyện. Bản kể được người trong cộng đồng cung cấp cần lưu người kể, địa bàn, thời điểm, ngôn ngữ và quyền sử dụng. Không nhận bản viết lại không rõ nguồn là nguyên tác chỉ vì có tiêu đề tương tự.

## Phạm vi rà soát đã thực hiện

Tra theo cụm “nguồn gốc người Cơ Tu”, “quả bầu”, “hồng thủy”, “truyền thuyết dòng họ”, “gươl”, “x’nur/sanuôr”, “chim Tring”, “Tân tung Da dá”, “nói lý hát lý”; lần ngược tài liệu tham khảo của các bài nghiên cứu. Ưu tiên tạp chí, báo có tác giả/phỏng vấn và cơ quan lưu trữ. Không dùng trang bán tài liệu hoặc bài tổng hợp không rõ xuất xứ làm nguồn chuẩn.

Nguồn đã tải được đặt tên theo hash; lần tải lỗi vẫn giữ trong manifest. Ghi chú gắn hash raw đã được đọc: tải lại một phiên bản mới phải đối chiếu lại trước khi dựng lại ghi chú. Chưa có người chuyên môn xác nhận nội dung và chưa có phép đo truy xuất/embedding từ bộ dữ liệu này.
