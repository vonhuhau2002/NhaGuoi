"""The six characters and sample stories, independent of any UI."""

VILLAGERS = [
    {
        "name": "Người giữ lửa",
        "role": "Giữ hơi ấm cộng đồng",
        "color": "#B65D35",
        "symbol": "✦",
        "story": (
            "Xin chào các bạn! Tôi là người giữ lửa. "
            "Ngọn lửa mang đến hơi ấm và giúp mọi người quây quần bên nhau. "
            "Chúng ta hãy cùng học cách sẻ chia, quan tâm và giúp đỡ cộng đồng."
        ),
    },
    {
        "name": "Người dẫn đường",
        "role": "Yêu núi rừng",
        "color": "#54784B",
        "symbol": "❋",
        "story": (
            "Xin chào các bạn! Tôi yêu thiên nhiên và những con đường trong núi rừng. "
            "Khi khám phá quê hương, chúng ta hãy quan sát cẩn thận, bảo vệ cây xanh "
            "và giữ gìn môi trường."
        ),
    },
    {
        "name": "Người dệt vải",
        "role": "Gìn giữ hoa văn",
        "color": "#B18032",
        "symbol": "◇",
        "story": (
            "Xin chào các bạn! Những hoa văn trên vải có thể kể nhiều câu chuyện "
            "về cuộc sống. Các nghề thủ công truyền thống cần được trân trọng "
            "và truyền lại cho thế hệ sau."
        ),
    },
    {
        "name": "Người làm nhạc cụ",
        "role": "Âm thanh lễ hội",
        "color": "#8260A0",
        "symbol": "♫",
        "story": (
            "Xin chào các bạn! Âm nhạc giúp mọi người gắn kết với nhau trong những "
            "dịp gặp gỡ và lễ hội. Hãy cùng lắng nghe, tìm hiểu và trân trọng "
            "những giá trị văn hóa."
        ),
    },
    {
        "name": "Người kể chuyện",
        "role": "Truyền lại ký ức",
        "color": "#287D91",
        "symbol": "❝",
        "story": (
            "Xin chào các bạn! Những câu chuyện được truyền lại giúp chúng ta hiểu "
            "hơn về quê hương và gia đình. Hãy lắng nghe người đi trước và tìm hiểu "
            "văn hóa Cơ Tu bằng sự tôn trọng."
        ),
    },
]

CHARACTERS = {
    "elder": {
        "name": "Già làng",
        "role": "Người dẫn chuyện",
        "story": (
            "Xin chào các bạn nhỏ! Ta là Già làng.\n\n"
            "Hãy chọn một người bạn để khám phá câu chuyện của họ. "
            "Khi chọn Già làng, các bạn có thể chọn câu chuyện bên dưới "
            "để ta kể lại."
        ),
    },
    **{f"person_{i}": dict(person) for i, person in enumerate(VILLAGERS, 1)},
}
