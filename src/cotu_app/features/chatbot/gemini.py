"""Gemini REST/SSE transport. Never logs key, URL query secrets, or API bodies."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import re
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class Cancelled(Exception):
    pass


class APIError(Exception):
    def __init__(self, message, status=0, retry_after=0):
        super().__init__(message)
        self.status, self.retry_after = status, retry_after


def retry_seconds(headers, body):
    value = headers.get("Retry-After", "") if headers else ""
    delay = 60.0
    try:
        delay = float(value)
    except (ValueError, TypeError):
        try:
            delay = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            for detail in body.get("error", {}).get("details", []):
                raw = detail.get("retryDelay", "")
                if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?s", raw):
                    delay = float(raw[:-1])
    if not 0 <= delay < float("inf"):
        delay = 60
    return max(1, delay)


def sse_events(response, check):
    """Accept CRLF/multiline data, comments and final event without blank line."""
    data, total = [], 0
    while True:
        check()
        line = response.readline(65537)
        check()
        total += len(line)
        if len(line) > 65536 or total > 262144:
            raise APIError("Phản hồi API vượt giới hạn.")
        if not line:
            if data:
                yield "\n".join(data)
            break
        text = line.decode("utf-8").rstrip("\r\n")
        if not text:
            if data:
                yield "\n".join(data)
                data = []
        elif text.startswith("data:"):
            value = text[5:]
            data.append(value[1:] if value.startswith(" ") else value)


def partial_answer(raw):
    """Decode complete JSON string characters only; output remains provisional."""
    match = re.search(r'"answer_text"\s*:\s*"', raw)
    if not match:
        return ""
    chars, pos = [], match.end()
    while pos < len(raw):
        char = raw[pos]
        if char == '"':
            break
        if char == "\\":
            count = 6 if raw[pos:pos + 2] == "\\u" else 2
            if pos + count > len(raw):
                break
            chars.append(raw[pos:pos + count])
            pos += count
        else:
            chars.append(char)
            pos += 1
    try:
        decoded = json.loads('"' + "".join(chars) + '"')
        if decoded and 0xD800 <= ord(decoded[-1]) <= 0xDBFF:
            decoded = decoded[:-1]  # Wait for the second half of an escaped emoji.
        decoded.encode("utf-8")
        return decoded
    except (ValueError, UnicodeError):
        return ""


RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "answer_text": {"type": "STRING"},
        "status": {"type": "STRING", "enum": ["answered", "insufficient_evidence", "clarification_needed"]},
        "citation_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["answer_text", "status", "citation_ids"],
    "propertyOrdering": ["answer_text", "status", "citation_ids"],
}


class GeminiClient:
    def __init__(self, settings, opener=urlopen):
        self.settings, self.opener = settings, opener

    def generate(self, system, prompt, on_delta, cancel):
        cfg = self.settings
        if not cfg.api_key:
            raise APIError("Chưa cấu hình GEMINI_API_KEY.")
        generation = {
            "temperature": 0.2, "maxOutputTokens": cfg.max_output_tokens,
            "responseMimeType": "application/json", "responseSchema": RESPONSE_SCHEMA,
        }
        if cfg.thinking_level != "auto":
            if cfg.model.startswith("gemini-2.5-"):
                generation["thinkingConfig"] = {"thinkingBudget": 0}
            else:
                generation["thinkingConfig"] = {"thinkingLevel": cfg.thinking_level}
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation,
        }
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{cfg.model}:streamGenerateContent?alt=sse",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "text/event-stream",
                     "x-goog-api-key": cfg.api_key}, method="POST")
        started = time.monotonic()

        def check():
            if cancel.is_set():
                raise Cancelled()
            if time.monotonic() - started > cfg.total_timeout:
                raise APIError("API quá thời gian chờ.")

        raw, emitted, finish, usage = "", "", None, {}
        try:
            check()
            with self.opener(request, timeout=min(cfg.timeout, cfg.total_timeout)) as response:
                for event in sse_events(response, check):
                    if event == "[DONE]":
                        continue
                    packet = json.loads(event)
                    if not isinstance(packet, dict):
                        raise APIError("API trả lỗi trong luồng dữ liệu.")
                    if packet.get("error"):
                        status = int(packet["error"].get("code", 0))
                        raise APIError("API trả lỗi trong luồng dữ liệu.", status,
                                       retry_seconds({}, packet) if status in {429, 503} else 0)
                    if packet.get("promptFeedback", {}).get("blockReason"):
                        raise APIError("API không trả lời yêu cầu này.")
                    candidates = packet.get("candidates", [])
                    if candidates:
                        candidate = candidates[0]
                        for part in candidate.get("content", {}).get("parts", []):
                            if not part.get("thought"):
                                raw += part.get("text", "")
                        finish = candidate.get("finishReason", finish)
                    if len(raw) > 16000:
                        raise APIError("Câu trả lời vượt giới hạn.")
                    preview = partial_answer(raw)
                    if preview.startswith(emitted) and len(preview) > len(emitted):
                        on_delta(preview[len(emitted):])
                        emitted = preview
                    usage.update(packet.get("usageMetadata", {}))
            check()
            if finish != "STOP":
                raise APIError("Câu trả lời bị cắt hoặc chưa hoàn tất.")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise APIError("Định dạng câu trả lời không hợp lệ.")
            if isinstance(result.get("answer_text"), str):
                result["answer_text"].encode("utf-8")
            return result, usage
        except HTTPError as error:
            try:
                body = json.loads(error.read(65536))
                if not isinstance(body, dict):
                    body = {}
            except (ValueError, OSError):
                body = {}
            finally:
                error.close()
            status = error.code
            labels = {400: "Chưa thể trả lời với cấu hình hiện tại.",
                      401: "Khóa kết nối không hợp lệ.", 403: "Khóa kết nối chưa có quyền hoặc khu vực chưa hỗ trợ.",
                      404: "Dịch vụ trả lời chưa khả dụng; nhờ thầy cô kiểm tra cấu hình.",
                      429: "Dịch vụ trả lời đã chạm hạn mức; tạm dùng đoạn tư liệu.",
                      503: "Dịch vụ trả lời đang bận; tạm dùng đoạn tư liệu."}
            raise APIError(labels.get(status, f"Dịch vụ trả lời gặp lỗi ({status})."), status,
                           retry_seconds(error.headers, body) if status in {429, 503} else 0) from None
        except (URLError, TimeoutError, socket.timeout, OSError):
            if cancel.is_set():
                raise Cancelled() from None
            raise APIError("Không kết nối được dịch vụ trả lời hoặc đã hết thời gian chờ.") from None
        except (ValueError, UnicodeError, KeyError, TypeError, AttributeError, IndexError):
            raise APIError("Dữ liệu API không hợp lệ; tạm dùng đoạn tư liệu.") from None
