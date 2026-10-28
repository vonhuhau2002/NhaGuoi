"""Hỏi đáp mẫu dùng ngoại tuyến, bám theo năm truyện mẫu trong characters.py.

Đây là gợi ý giáo dục về nội dung truyện, không phải tài liệu xác minh
phong tục Cơ Tu. Người phụ trách cần duyệt trước khi sử dụng giảng dạy.
"""

STORY_QUESTIONS = {
    "person_1": [
        ("Vì sao mọi người quây quần bên lửa?",
         "Trong câu chuyện, ngọn lửa mang lại hơi ấm và tạo dịp để mọi người ngồi gần nhau. "
         "Khi cùng trò chuyện, mỗi người có thể kể việc đã làm, lắng nghe người khác và nhận ra ai đang cần giúp đỡ. "
         "Vì vậy, điều câu chuyện muốn nhắc đến còn là sự quan tâm giữa con người với nhau."),
        ("Sẻ chia có nghĩa là gì?",
         "Sẻ chia là dành một phần thời gian, công sức hoặc những gì mình có để giúp người khác. "
         "Ví dụ, con có thể cho bạn dùng chung đồ học tập, lắng nghe khi bạn buồn hoặc cùng bạn hoàn thành một việc. "
         "Hãy hỏi xem người khác cần gì để sự giúp đỡ thực sự có ích."),
        ("Con có thể làm gì cho cộng đồng?",
         "Con có thể bắt đầu từ những việc phù hợp với tuổi của mình: giữ nơi sinh hoạt sạch sẽ, "
         "xếp đồ sau khi dùng và giúp người lớn những việc được hướng dẫn. Một việc nhỏ được làm đều đặn "
         "cũng thể hiện tinh thần trách nhiệm. Với bếp lửa, con cần có người lớn hướng dẫn và giám sát."),
    ],
    "person_2": [
        ("Vì sao cần quan sát khi khám phá?",
         "Quan sát giúp con nhận ra đường đi, cây cối và những thay đổi xung quanh. "
         "Thay vì vội vàng, con có thể dừng lại ở chỗ an toàn, nhìn và đặt câu hỏi. "
         "Khi đi rừng hoặc đi xa, hãy đi cùng người lớn có kinh nghiệm và theo hướng dẫn của họ."),
        ("Bảo vệ thiên nhiên bằng cách nào?",
         "Câu chuyện nhắc chúng ta giữ cây xanh và môi trường. Con có thể mang rác của mình về đúng nơi thu gom, "
         "quan sát động vật từ xa và không tự ý bẻ cành hay hái cây. Giữ nguyên nơi mình đến "
         "giúp những người sau cũng được khám phá và giúp sinh vật có nơi sống."),
        ("Người dẫn đường dạy ta điều gì?",
         "Người dẫn đường gợi cho chúng ta sự cẩn thận và tinh thần học hỏi. Biết đường không chỉ là nhớ lối đi, "
         "mà còn là biết quan sát và hỏi khi chưa chắc chắn. Trong cuộc sống, con cũng có thể lắng nghe "
         "người có kinh nghiệm trước khi thử một việc mới."),
    ],
    "person_3": [
        ("Hoa văn có thể kể chuyện thế nào?",
         "Trong truyện mẫu, màu sắc và hình trên vải gợi nhắc về cuộc sống của người làm ra nó. "
         "Một họa tiết có thể khiến ta liên tưởng đến thiên nhiên hoặc sinh hoạt. Tuy nhiên, không nên tự kết luận "
         "ý nghĩa của hoa văn cụ thể; hãy hỏi người dệt hoặc đọc nguồn đã được xác minh."),
        ("Vì sao cần giữ nghề thủ công?",
         "Một sản phẩm thủ công chứa thời gian, kỹ năng và kinh nghiệm của người làm. "
         "Khi người có kinh nghiệm truyền lại cách làm, thế hệ sau có cơ hội hiểu quá trình tạo ra sản phẩm "
         "và tiếp tục học nghề. Trân trọng nghề cũng là trân trọng công sức của người lao động."),
        ("Con có thể tìm hiểu nghề dệt ra sao?",
         "Con có thể quan sát người dệt khi được cho phép, hỏi về vật liệu và các bước làm, "
         "rồi thử vẽ một mẫu hoa văn của riêng mình. Khi giới thiệu mẫu tự vẽ, hãy nói rõ đó là sáng tạo của con, "
         "không phải hoa văn truyền thống đã được xác nhận."),
    ],
    "person_4": [
        ("Âm nhạc giúp mọi người gắn kết ra sao?",
         "Trong câu chuyện, mọi người cùng nghe nhạc khi gặp gỡ. Cùng lắng nghe, hát hoặc giữ nhịp "
         "có thể giúp chúng ta chú ý đến nhau và chia sẻ cảm xúc. Mỗi người có thể cảm nhận khác nhau, "
         "vì vậy biết lắng nghe và tôn trọng nhau cũng quan trọng như việc biểu diễn."),
        ("Nhạc cụ tạo âm thanh như thế nào?",
         "Âm thanh xuất hiện khi có vật rung động. Tùy loại nhạc cụ, người chơi có thể gõ, gảy hoặc thổi "
         "để tạo rung động. Đây là giải thích khoa học chung; truyện mẫu chưa nêu tên hay cấu tạo "
         "của một nhạc cụ Cơ Tu cụ thể."),
        ("Làm sao trân trọng người làm nhạc cụ?",
         "Con có thể hỏi về công việc của họ, lắng nghe khi họ giới thiệu và chỉ chạm vào nhạc cụ khi được phép. "
         "Mỗi nhạc cụ cần thời gian chọn vật liệu và chế tác. Giữ gìn nhạc cụ, không đùa nghịch gây hỏng "
         "là một cách thể hiện sự trân trọng."),
    ],
    "person_5": [
        ("Vì sao cần nghe chuyện người đi trước?",
         "Những câu chuyện có thể giúp con hiểu trải nghiệm, niềm vui và khó khăn của người khác. "
         "Khi nghe người đi trước, con có thêm góc nhìn về gia đình và quê hương. Tuy nhiên, truyện kể "
         "có thể chứa ký ức hoặc tưởng tượng; nếu cần khẳng định một sự kiện, hãy tìm hiểu thêm nguồn đáng tin cậy."),
        ("Lắng nghe có nghĩa là gì?",
         "Lắng nghe là chú ý đến điều người khác đang chia sẻ, để họ nói hết và hỏi lại khi chưa hiểu. "
         "Con có thể nói: ‘Con hiểu như thế này có đúng không?’ Cách hỏi đó giúp người kể biết "
         "con đã hiểu đến đâu và có thể giải thích rõ hơn."),
        ("Con có thể lưu giữ câu chuyện ra sao?",
         "Con có thể ghi lại ý chính, vẽ tranh hoặc kể lại bằng lời của mình. Hãy ghi tên người kể "
         "và xin phép trước khi ghi âm hoặc chia sẻ câu chuyện của họ. Khi kể lại, cần phân biệt "
         "điều người kể đã nói với phần con tự tưởng tượng thêm."),
    ],
}


def questions_for(character_id, story_id, completed_story):
    """Chỉ mở hỏi đáp khi Già làng đã kể xong đúng truyện hiện tại."""
    if character_id != "elder" or story_id != completed_story:
        return []
    return STORY_QUESTIONS.get(story_id, [])
