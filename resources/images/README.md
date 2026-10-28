# Minh họa nhân vật

`village_characters.png` là ảnh AI được tạo bằng công cụ imagegen tích hợp.
Ảnh được lưu trong dự án để ứng dụng chạy ngoại tuyến, không cần Pillow.

Ảnh có 3 cột × 2 hàng, theo thứ tự: Già làng, người giữ lửa, người dẫn đường,
người dệt vải, người làm nhạc cụ, người kể chuyện.
Ứng dụng tách và thu nhỏ các ô bằng Tkinter khi khởi động.
Đây là hình minh họa sáng tạo; không phải ảnh tư liệu hay bản xác minh trang phục Cơ Tu.

## Prompt đã dùng

```text
Use case: illustration-story. Create one production asset for a Vietnamese children's storytelling touchscreen app: a sprite sheet of SIX distinct portrait illustrations in an exact 3-column by 2-row equal grid, each tile square, no gutters, no text, no lettering, no watermark. Overall image landscape 3:2. Order left-to-right top-to-bottom: (1) kind elderly Vietnamese village storyteller with gray hair and warm smile holding a story book; (2) adult village fire keeper with small warm hearth; (3) adult forest guide holding a walking stick amidst green leaves; (4) adult weaver using a simple loom and fabric; (5) adult musical instrument maker holding a bamboo flute; (6) adult village storyteller holding a book. Inspired by a respectful fictional mountain village in central Vietnam, everyday modest earth toned clothing, subtle woven accents, avoid claiming ethnographic accuracy or elaborate invented ceremonial outfits. Illustrated picture book style, soft gouache, confident clean outlines, warm cream background in every tile, terracotta, forest green, gold palette, friendly expressive faces, waist-up centered subjects, generous safe margins within each tile so individual tiles can be cropped. All six portraits same visual scale and style. This is a conceptual educational illustration, not a documentary depiction.
```
