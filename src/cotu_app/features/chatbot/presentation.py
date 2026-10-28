"""Visitor-facing answers; evidence metadata stays in structured results."""

import re


UNAVAILABLE_ANSWER = 'Hiện Nhà Gươi chưa tổng hợp được câu trả lời. Em thử lại sau một chút nhé.'


def compact_answer(text):
    text = re.sub(r'^\s*(?:Nguồn(?: tham khảo| trích dẫn)?|Tài liệu tham khảo|Trích dẫn)\s*:.*$',
                  '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\[([^\]]+)\]\(https?://[^\s)]+\)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\[(?:S\d+:[\w.-]+(?:\s*[,;]\s*S\d+:[\w.-]+)*|\d{1,2}(?:\s*[,;]\s*\d{1,2})*)\]', '', text)
    text = re.sub(r'\bS\d+:[\w.-]+\b', '', text)
    text = re.sub(r'^\s*(?:#{1,6}\s+|[-*•]\s+|\d+[.)]\s+)', '', text, flags=re.MULTILINE)
    text = text.replace('**', '').replace('__', '').replace('`', '')
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)
    return ' '.join(text.split()).strip()


def visitor_answer(result):
    if result.status == 'extractive_fallback':
        return UNAVAILABLE_ANSWER
    return compact_answer(result.answer_text)
