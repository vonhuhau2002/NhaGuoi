"""Match curated answers; show suggestions without inventing answers."""
from difflib import SequenceMatcher
from cotu_app.core.text import normalize, question_key
from .models import Answer

UNKNOWN = "Chưa có câu trả lời đã duyệt cho câu hỏi này trong nội dung đã nạp."

def answer_question(question, knowledge):
    """Match equivalent approved question forms, never choose by similarity."""
    query = question_key(question)
    if not query:
        return Answer("Chưa nhận được câu hỏi. Hãy nói lại hoặc nhập câu hỏi.")
    if knowledge is None:
        return Answer("Hãy chọn video và nạp bộ hỏi đáp hoặc học lời thoại trước.")
    candidates = [(item, [question_key(s) for s in [item["question"], *item.get("aliases", [])]])
                  for item in knowledge.questions]
    matches = [item for item, variants in candidates if query in variants]
    if len(matches) == 1:
        return Answer(matches[0]["answer"], approved=True,
                      character_id=matches[0].get("character_id"),
                      source=matches[0].get("source_label"))
    ranked = [(max(SequenceMatcher(None, query, variant).ratio() for variant in variants),
               item["question"]) for item, variants in candidates]
    suggestions = tuple(q for score, q in sorted(ranked, reverse=True)[:3] if score >= 0.50)
    # Đoạn liên quan chỉ là nguồn đối chiếu, không được trình bày như đáp án đã xác minh.
    ignored = set("ai la gi tai sao vi o dau nao nhu the va cua trong cau chuyen video hay cho biet em con toi hoi".split())
    keywords = set(query.split()) - ignored
    passages = []
    for segment in knowledge.segments:
        words = set(normalize(segment["text"]).split())
        overlap = len(keywords & words)
        if len(keywords) >= 2 and overlap >= 2 and overlap / len(keywords) >= 0.65:
            passages.append((overlap / max(len(words), 1), segment))
    text = UNKNOWN
    if not knowledge.questions:
        text += ("\nVideo hiện mới có lời thoại, chưa có bộ hỏi đáp. "
                 "Vào Thiết lập → Bộ hỏi đáp, rồi Nạp nội dung.")
    if suggestions:
        text += "\nCó thể bạn muốn hỏi:\n" + "\n".join(f"• {q}" for q in suggestions)
        text += "\nChọn câu tương ứng trong danh sách để nghe đáp án."
    if passages:
        segment = max(passages, key=lambda pair: pair[0])[1]
        start = segment["start"]
        stamp = "TXT" if start is None else f"{int(start) // 60:02d}:{int(start) % 60:02d}"
        text += f"\n\nLời thoại liên quan [{stamp}; {knowledge.source}]:\n{segment['text']}"
    return Answer(text, suggestions=suggestions)
