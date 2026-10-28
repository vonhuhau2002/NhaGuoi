"""Vietnamese matching rules for the curated story questions."""
import re
import unicodedata

def normalize(text):
    text = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(re.findall(r"\w+", text))


def question_key(text):
    """Normalize equivalent question forms without dropping facts/negation.

    Rules describe grammar, not a similarity score: all subject words,
    qualifiers, numbers and negatives remain part of the lookup key.
    """
    text = normalize(text)
    # Tên riêng dễ được gõ/nhận dạng thành các biến thể khác nhau.
    text = re.sub(r"\bnha (?:guoi|goi|guoil|gul)\b", "nha guol", text)
    prefix = (r"^(?:(?:gia lang|thay|co|bac|ong|ba) oi|"
              r"thua (?:gia lang|thay|co|bac|ong|ba)|"
              r"(?:ban (?:co the )?)?cho (?:con|em|chau|toi) (?:hoi|biet)(?: la)?|"
              r"(?:con|em|chau|toi)(?: muon)? (?:hoi|biet)(?: la)?|"
              r"(?:ban (?:co the )?)?(?:giai thich|noi ro)"
              r"(?: giup (?:con|em|chau|toi))?(?: cho (?:con|em|chau|toi))?(?: ve)?|"
              r"xin (?:hoi|cho biet)|hay cho biet|"
              r"(?:trong|theo) (?:video|cau chuyen)(?: nay)?)\s+")
    while True:
        trimmed = re.sub(prefix, "", text)
        if trimmed == text:
            break
        text = trimmed
    text = re.sub(r"(?:\s+(?:a|nhe|voi|vay|the))+$", "", text)
    text = re.sub(r"\s+(?:trong|theo) (?:video|cau chuyen)(?: nay)?$", "", text)

    # Gươl is the named community house, with or without the noun 'nhà'.
    text = re.sub(r"\b(?:ngoi )?nha guol\b", "guol", text)
    # 'là cái gì' asks for the same definition as 'là gì'. Do not remove
    # 'cái' elsewhere: 'cột cái' is different from 'cột con'.
    text = re.sub(r"\bla (?:cai|dieu|thu) gi\b", "la gi", text)
    text = re.sub(r"\b(?:duoc hieu la|co nghia la|nghia la) gi$", "la gi", text)
    text = re.sub(r"^the nao la (.+)$", r"\1 la gi", text)
    text = re.sub(r"\bvi sao\b", "tai sao", text)
    text = re.sub(r"\bco may\b", "co bao nhieu", text)

    # Meaning/symbolism is its own intent, not a definition of the object.
    text = re.sub(r"^(.+?) (?:co )?y nghia(?: la)? gi$", r"y nghia cua \1", text)
    text = re.sub(r"^y nghia cua (.+?) la gi$", r"y nghia cua \1", text)

    # Purpose/function remains separate from definition, meaning and reason.
    text = re.sub(r"^(.+?) (?:co )?(?:chuc nang|cong dung)(?: la)? gi$",
                  r"\1 dung de lam gi", text)
    text = re.sub(r"^(?:chuc nang|cong dung) cua (.+?)(?: la)? gi$",
                  r"\1 dung de lam gi", text)
    text = re.sub(r"^(.+?) (?:duoc )?(?:(?:su dung|dung) )?de lam (?:cai )?gi$",
                  r"\1 dung de lam gi", text)

    # Generic material questions only. Specifics such as 'lá cây gì',
    # 'loại tre nào', dates, places and measurements must not disappear.
    text = re.sub(r"\b(?:bang|tu) (?:nhung )?(?:vat lieu|chat lieu) (?:gi|nao)$",
                  "bang gi", text)
    text = re.sub(r"\b(?:duoc )?(lam|lop|lat|xay|dung) (?:bang|tu)\b",
                  r"\1 bang", text)
    text = re.sub(r"\bbang cai gi$", "bang gi", text)
    return text
