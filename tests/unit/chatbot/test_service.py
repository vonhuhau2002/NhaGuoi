from dataclasses import replace
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from cotu_app.features.chatbot.config import ROOT, Settings, load_env
from cotu_app.features.chatbot.gemini import APIError, Cancelled, GeminiClient, partial_answer, sse_events
from cotu_app.features.chatbot.retrieval import Retriever, build_index, eligible, read_corpus
from cotu_app.features.chatbot.service import ChatService, ChatResult
from cotu_app.features.chatbot.presentation import UNAVAILABLE_ANSWER, compact_answer


class CorpusFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "research.sqlite3"
        self.source = ROOT / "corpus/documents.jsonl"
        build_index(self.source, self.path, "research")
        self.retriever = Retriever(self.path, "research")

    def ids(self, question, history=()):
        return [d["document_id"] for d in self.retriever.search(question, history)]


class CorpusCase(CorpusFixture):
    def test_research_excludes_other_ethnic_group_and_republication(self):
        self.assertEqual(int(self.retriever.meta["count"]), 8)
        docs = read_corpus(self.source)
        self.assertFalse(eligible(next(d for d in docs if d["source_id"] == "S10"), "research"))
        self.assertFalse(eligible(next(d for d in docs if d["source_id"] == "S11"), "research"))

    def test_approved_does_not_silently_use_research(self):
        target = Path(self.tmp.name) / "approved.sqlite3"
        self.assertEqual(build_index(self.source, target, "approved")["count"], "0")
        self.assertEqual(Retriever(target, "approved").search("Gươl"), [])
        with self.assertRaises(ValueError):
            Retriever(self.path, "approved")

    def test_flag_alone_is_not_approval(self):
        doc = read_corpus(self.source)[0]
        doc["production_approved"] = True
        self.assertFalse(eligible(doc, "approved"))
        doc["review_status"] = "approved"
        self.assertTrue(eligible(doc, "approved"))
        doc["usage"] = "quarantine"
        self.assertFalse(eligible(doc, "approved"))

    def test_diacritics_and_paraphrase(self):
        self.assertIn("S03:guol", self.ids("guol dung de lam gi vay"))
        self.assertIn("S03:guol", self.ids("Nhà sinh hoạt chung của làng có ý nghĩa gì?"))
        self.assertIn("S07:hat-ly", self.ids("noi li hat li la sao"))

    def test_followup_uses_last_user_topic(self):
        self.assertIn("S06:dance", self.ids("Còn phụ nữ thì sao?", [
            {"role": "user", "content": "Nam giới múa điệu gì?"},
            {"role": "assistant", "content": "Mua cổ phiếu."}]))

    def test_fts_syntax_is_data(self):
        self.assertEqual(self.ids('" OR * : NEAR( ) ; DROP TABLE documents; --'), [])
        self.assertIn("S03:guol", self.ids("Gươl"))

    def test_empty_and_outside_domain(self):
        self.assertEqual(self.ids(""), [])
        self.assertEqual(self.ids("Tỷ giá USD hôm nay?"), [])

    def test_changed_index_requires_restart(self):
        changed = Path(self.tmp.name) / "changed.jsonl"
        docs = read_corpus(self.source)
        docs[0]["text"] += " Nội dung mới."
        changed.write_text("\n".join(json.dumps(d) for d in docs), encoding="utf-8")
        build_index(changed, self.path, "research")
        with self.assertRaisesRegex(ValueError, "Index đã đổi"):
            self.retriever.search("Gươl")

    def test_invalid_import_does_not_destroy_index(self):
        invalid = Path(self.tmp.name) / "invalid.jsonl"
        doc = read_corpus(self.source)[0]
        doc["text"] *= 20
        invalid.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaises(ValueError):
            build_index(invalid, self.path, "research")
        self.assertIn("S03:guol", self.ids("Gươl"))

    def test_duplicate_ids_rejected(self):
        doc = read_corpus(self.source)[0]
        invalid = Path(self.tmp.name) / "duplicate.jsonl"
        invalid.write_text(json.dumps(doc) + "\n" + json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Trùng"):
            read_corpus(invalid)


class FakeClient:
    def __init__(self):
        self.calls, self.error, self.status = [], None, "answered"
        self.ids = ["S03:guol"]
        self.hook = None

    def generate(self, system, prompt, on_delta, cancel):
        self.calls.append(json.loads(prompt))
        if self.hook:
            self.hook(cancel)
        on_delta("Gươl là không gian chung.")
        if self.error:
            raise self.error
        return {"answer_text": "Gươl là không gian chung.", "status": self.status,
                "citation_ids": self.ids}, {"totalTokenCount": 100}


class ServiceCase(CorpusFixture):
    def setUp(self):
        super().setUp()
        self.fake = FakeClient()
        self.settings = Settings(api_key="FAKE_KEY", min_interval=0)
        self.service = ChatService(self.retriever, self.settings, self.fake)

    def test_curated_answer_bypasses_retrieval_history_api_cooldown_and_missing_key(self):
        from cotu_app.features.stories.catalog import CuratedCatalog
        text = "Ngôi nhà chung.\nNơi sinh hoạt."
        self.service.curated = CuratedCatalog({"elder": [{
            "question": "Nhà Gươl là gì?", "aliases": ["Gươl là gì?"],
            "answer": text, "character_id": "person_3"}]})
        self.service.settings = replace(self.settings, api_key="")
        self.service.next_request = float("inf")
        with patch.object(self.retriever, "search", side_effect=AssertionError("Must skip retrieval")):
            result = self.service.ask("Gươl là gì?", [{"role": "user", "content": "Chim Tring?"}],
                                      offline=True)
        self.assertEqual(result.status, "answered")
        self.assertEqual(result.mode, "approved")
        self.assertEqual(result.character_id, "person_3")
        self.assertEqual(result.audio_text, text)
        self.assertEqual(result.answer_text, "Ngôi nhà chung. Nơi sinh hoạt.")
        self.assertEqual(result.metrics["route"], "curated")
        self.assertFalse(result.metrics["api_called"])
        self.assertEqual(self.fake.calls, [])

    def test_curated_miss_still_uses_normal_ai_flow_and_cancel_wins(self):
        from cotu_app.features.stories.catalog import CuratedCatalog
        self.service.curated = CuratedCatalog({"elder": [{
            "question": "Gươl là gì?", "answer": "Ngôi nhà chung."}]})
        result = self.service.ask("Gươl có phải nhà riêng không?")
        self.assertTrue(result.metrics["api_called"])
        self.assertEqual(result.audio_text, "")
        cancel = threading.Event()
        cancel.set()
        self.assertEqual(self.service.ask("Gươl là gì?", cancel=cancel).status, "cancelled")
        self.assertEqual(len(self.fake.calls), 1)

    def test_paraphrased_definition_uses_curated_answer_without_ai(self):
        from cotu_app.features.stories.catalog import CuratedCatalog
        self.service.curated = CuratedCatalog({"elder": [{
            "question": "Nhà Gươl là gì?", "answer": "Ngôi nhà chung.",
            "character_id": "person_3"}]})
        with patch.object(self.retriever, "search", side_effect=AssertionError("No evidence search")):
            result = self.service.ask("nhà guol là cái gì")
        self.assertEqual(result.answer_text, "Ngôi nhà chung.")
        self.assertEqual(result.audio_text, "Ngôi nhà chung.")
        self.assertEqual(result.character_id, "person_3")
        self.assertEqual(result.metrics["route"], "curated")
        self.assertFalse(result.metrics["api_called"])
        self.assertFalse(self.fake.calls)

    def test_valid_answer_maps_sources_and_cache(self):
        result = self.service.ask("Gươl dùng làm gì?")
        self.assertEqual(result.status, "answered")
        self.assertIn("THỬ NGHIỆM", result.notice)
        self.assertTrue(result.metrics["api_called"])
        self.assertTrue(result.citations[0]["source_url"].startswith("https://"))
        cached = self.service.ask("Gươl dùng làm gì?")
        self.assertTrue(cached.cached)
        self.assertFalse(cached.metrics["api_called"])
        self.assertEqual(cached.metrics["usage"], {})
        self.assertEqual(len(self.fake.calls), 1)

    def test_cache_uses_history_and_character(self):
        self.service.ask("Gươl?")
        self.service.ask("Gươl?", [{"role": "user", "content": "Múa là gì?"}])
        self.service.ask("Gươl?", character_id="weaver")
        self.assertEqual(len(self.fake.calls), 3)

    def test_cache_ttl_and_size(self):
        self.service.settings = replace(self.settings, cache_size=1, cache_ttl=.01)
        self.service.ask("Gươl?")
        self.service.ask("Nhà gươl?")
        self.assertEqual(len(self.service.cache), 1)
        key, value = next(iter(self.service.cache.items()))
        self.service.cache[key] = (value[0] - 10, *value[1:])
        self.assertFalse(self.service.ask("Nhà gươl?").cached)

    def test_missing_key_and_offline_do_not_call_api(self):
        self.service.settings = replace(self.settings, api_key="")
        result = self.service.ask("Gươl?")
        self.assertEqual(result.status, "extractive_fallback")
        self.service.ask("Gươl?", offline=True)
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(len(self.service.cache), 0)

    def test_outside_domain_no_api_call(self):
        self.assertEqual(self.service.ask("Tỷ giá USD hôm nay?").status, "insufficient_evidence")
        self.assertEqual(self.fake.calls, [])

    def test_unapproved_empty_index_no_api(self):
        target = Path(self.tmp.name) / "approved.sqlite3"
        build_index(self.source, target, "approved")
        service = ChatService(Retriever(target, "approved"), self.settings, self.fake)
        self.assertIn("chưa có đủ thông tin", service.ask("Gươl?").answer_text)
        self.assertFalse(self.fake.calls)

    def test_invalid_source_is_rejected_and_not_cached(self):
        self.fake.ids = ["S10:comparison", "https://invented.example"]
        result = self.service.ask("Gươl?")
        self.assertEqual(result.status, "extractive_fallback")
        self.assertFalse(self.service.cache)
        self.assertNotIn("S10:comparison", [d["document_id"] for d in result.citations])

    def test_answer_requires_source(self):
        self.fake.ids = []
        self.assertEqual(self.service.ask("Gươl?").status, "extractive_fallback")

    def test_insufficient_evidence_is_accepted_without_citations(self):
        self.fake.status, self.fake.ids = "insufficient_evidence", []
        self.assertEqual(self.service.ask("Gươl làng tôi xây năm nào?").status, "insufficient_evidence")

    def test_429_cooldown_no_retries_or_fallback_cache(self):
        self.fake.error = APIError("Quota", 429, 60)
        self.assertEqual(self.service.ask("Gươl?").status, "extractive_fallback")
        self.assertIn("hạn mức", self.service.ask("Nhà gươl?").notice)
        self.assertEqual(len(self.fake.calls), 1)
        self.assertFalse(self.service.cache)

    def test_local_spacing_avoids_extra_call(self):
        self.service.settings = replace(self.settings, min_interval=6)
        self.service.ask("Gươl?")
        self.assertEqual(self.service.ask("Nhà gươl?").status, "extractive_fallback")
        self.assertEqual(len(self.fake.calls), 1)
        self.assertTrue(self.service.ask("Gươl?").cached)

    def test_cancel_before_and_during_stream(self):
        cancel = threading.Event()
        cancel.set()
        self.assertEqual(self.service.ask("Gươl?", cancel=cancel).status, "cancelled")
        self.assertFalse(self.fake.calls)
        self.fake.hook = lambda event: event.set()
        self.assertEqual(self.service.ask("Gươl?").status, "cancelled")
        self.assertFalse(self.service.cache)

    def test_only_one_inflight_request(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        self.fake.hook = lambda event: (entered.set(), release.wait(3))
        thread = threading.Thread(target=lambda: self.service.ask("Gươl?"))
        thread.start()
        self.assertTrue(entered.wait(2))
        self.assertEqual(self.service.ask("Nhà gươl?").status, "busy")
        release.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(self.fake.calls), 1)

    def test_history_and_prompt_are_bounded(self):
        history = [{"role": "user", "content": "gươl " * 1000}] * 20
        self.service.ask("Gươl?", history)
        prompt = self.fake.calls[0]
        self.assertEqual(len(prompt["history"]), 4)
        self.assertTrue(all(len(h["content"]) <= 1200 for h in prompt["history"]))
        self.assertLessEqual(sum(len(d["text"]) for d in prompt["evidence"]), 6000)

    def test_invalid_question_no_call(self):
        for question in ("", " " * 3, "x" * 1201, None):
            self.assertEqual(self.service.ask(question).status, "invalid_input")
        self.assertFalse(self.fake.calls)

    def test_fallback_keeps_evidence_internal_without_dumping_excerpts(self):
        self.fake.error = APIError("Quota", 429, 60)
        result = self.service.ask("Gươl?")
        self.assertEqual(result.answer_text, UNAVAILABLE_ANSWER)
        self.assertTrue(result.citations)
        self.assertNotIn("S03:guol", result.answer_text)
        self.assertNotIn("http", result.answer_text)
        self.assertNotIn("Đoạn tư liệu", result.answer_text)

    def test_answer_is_compacted_and_cached_without_losing_source_validation(self):
        def generate(*args):
            return {"status": "answered", "citation_ids": ["S03:guol"],
                    "answer_text": "**Gươl là nhà chung.** [S03:guol]\n\n- Đây là nơi sinh hoạt.\nNguồn: https://example.com"}, {}
        self.fake.generate = generate
        result = self.service.ask("Gươl?")
        self.assertEqual(result.answer_text, "Gươl là nhà chung. Đây là nơi sinh hoạt.")
        self.assertEqual(result.citations[0]["document_id"], "S03:guol")
        self.assertEqual(self.service.ask("Gươl?").answer_text, result.answer_text)


class AnswerPresentationTests(unittest.TestCase):
    def test_one_plain_paragraph_without_links_or_citation_markers(self):
        text = "1. Gươl là nhà chung [S03:guol, S04:tring].\n2. Có [sinh hoạt](https://example.com). [1]\nNguồn tham khảo: https://example.com"
        self.assertEqual(compact_answer(text), "Gươl là nhà chung. Có sinh hoạt.")

    def test_information_and_qualifications_are_preserved(self):
        text = "Tại làng A, lễ diễn ra năm 2024. Chưa đủ thông tin để áp dụng cho mọi làng."
        self.assertEqual(compact_answer(text), text)

    def test_plain_terminal_output_is_only_the_answer_and_json_keeps_metadata(self):
        from contextlib import redirect_stdout
        from cotu_app.features.chatbot.cli import display
        result = ChatResult("Gươl là nhà chung.", "answered", citations=[{
            "document_id": "S03:guol", "title": "Tư liệu", "source_url": "https://example.com"}])
        output = io.StringIO()
        with redirect_stdout(output):
            display(result)
        self.assertEqual(output.getvalue(), "Gươl là nhà chung.\n")
        self.assertTrue(result.to_dict()["citations"])


def event(packet):
    return ("data: " + json.dumps(packet, ensure_ascii=False) + "\r\n\r\n").encode()


class TransportCase(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(api_key="DO_NOT_LEAK")
        self.cancel = threading.Event()

    def test_streaming_json_split_unicode_and_hidden_thought(self):
        raw = json.dumps({"answer_text": "Gươl là nhà chung.", "status": "answered", "citation_ids": ["S03:guol"]}, ensure_ascii=True)
        chunks = [raw[:26], raw[26:31], raw[31:]]
        body = b": heartbeat\r\n\r\n" + event({"candidates": [{"content": {"parts": [{"thought": True, "text": "SECRET_THOUGHT"}]}}]})
        for i, chunk in enumerate(chunks):
            body += event({"candidates": [{"content": {"parts": [{"text": chunk}]},
                                           **({"finishReason": "STOP"} if i == 2 else {})}],
                           "usageMetadata": {"totalTokenCount": 50}})
        captured, deltas = [], []
        def opener(request, timeout):
            captured.append(request)
            return io.BytesIO(body)
        data, usage = GeminiClient(self.settings, opener).generate("rules", "question", deltas.append, self.cancel)
        self.assertEqual(data["answer_text"], "".join(deltas))
        self.assertNotIn("SECRET_THOUGHT", "".join(deltas))
        self.assertEqual(usage["totalTokenCount"], 50)
        request = captured[0]
        self.assertNotIn("DO_NOT_LEAK", request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), "DO_NOT_LEAK")
        payload = json.loads(request.data)
        self.assertNotIn("tools", payload)
        self.assertEqual(payload["generationConfig"]["thinkingConfig"], {"thinkingLevel": "minimal"})

    def test_multiline_sse_and_final_event(self):
        response = io.BytesIO(b': ignore\ndata: {"a":\ndata: 1}\n\ndata: {"b": 2}')
        self.assertEqual([json.loads(p) for p in sse_events(response, lambda: None)], [{"a": 1}, {"b": 2}])

    def test_partial_escaped_json(self):
        self.assertEqual(partial_answer('{"answer_text":"Chim \\u01'), "Chim ")
        self.assertEqual(partial_answer('{"answer_text":"a\\"b\\n'), 'a"b\n')
        self.assertEqual(partial_answer('{"answer_text":"Hi \\ud83d'), 'Hi ')
        self.assertEqual(partial_answer('{"answer_text":"Hi \\ud83d\\ude00'), 'Hi 😀')

    def test_truncated_response_rejected(self):
        for reason in (None, "MAX_TOKENS", "SAFETY"):
            body = event({"candidates": [{"content": {"parts": [{"text": '{"answer_text":"Gươl"}'}]}, "finishReason": reason}]})
            with self.subTest(reason=reason), self.assertRaises(APIError):
                GeminiClient(self.settings, lambda *a, **k: io.BytesIO(body)).generate("s", "p", lambda t: None, self.cancel)

    def test_429_sanitized_retry_and_single_call(self):
        calls = []
        def opener(*a, **k):
            calls.append(1)
            raise HTTPError("https://example", 429, "DO_NOT_LEAK", {"Retry-After": "45"}, io.BytesIO(b'{"error":{"message":"DO_NOT_LEAK"}}'))
        with self.assertRaises(APIError) as caught:
            GeminiClient(self.settings, opener).generate("s", "p", lambda t: None, self.cancel)
        self.assertEqual(caught.exception.retry_after, 45)
        self.assertNotIn("DO_NOT_LEAK", str(caught.exception))
        self.assertEqual(calls, [1])

    def test_api_retry_info(self):
        def opener(*a, **k):
            body = b'{"error":{"details":[{"retryDelay":"12.5s"}]}}'
            raise HTTPError("https://example", 429, "quota", {}, io.BytesIO(body))
        with self.assertRaises(APIError) as caught:
            GeminiClient(self.settings, opener).generate("s", "p", lambda t: None, self.cancel)
        self.assertEqual(caught.exception.retry_after, 12.5)

    def test_bad_key_model_and_network_errors_are_sanitized(self):
        for status in (400, 401, 403, 404, 500, 503):
            def opener(*a, **k):
                raise HTTPError("https://example", status, "DO_NOT_LEAK", {}, io.BytesIO(b"DO_NOT_LEAK"))
            with self.subTest(status=status), self.assertRaises(APIError) as caught:
                GeminiClient(self.settings, opener).generate("s", "p", lambda t: None, self.cancel)
            self.assertNotIn("DO_NOT_LEAK", str(caught.exception))
        def offline(*a, **k):
            raise URLError("DO_NOT_LEAK")
        with self.assertRaises(APIError) as caught:
            GeminiClient(self.settings, offline).generate("s", "p", lambda t: None, self.cancel)
        self.assertNotIn("DO_NOT_LEAK", str(caught.exception))

    def test_malformed_or_blocked_stream_rejected(self):
        for body in (b"data: nope\n\n", event({"promptFeedback": {"blockReason": "SAFETY"}}), event([]), b"data: " + b"x" * 65540):
            with self.subTest(body=body[:30]), self.assertRaises(APIError):
                GeminiClient(self.settings, lambda *a, **k: io.BytesIO(body)).generate("s", "p", lambda t: None, self.cancel)

    def test_cancel_during_read(self):
        cancel = self.cancel
        class SlowResponse(io.BytesIO):
            def readline(self, size=-1):
                cancel.set()
                return super().readline(size)
        with self.assertRaises(Cancelled):
            GeminiClient(self.settings, lambda *a, **k: SlowResponse(event({}))).generate("s", "p", lambda t: None, cancel)

    def test_stream_error_carries_cooldown(self):
        body = event({"error": {"code": 429, "details": [{"retryDelay": "20s"}]}})
        with self.assertRaises(APIError) as caught:
            GeminiClient(self.settings, lambda *a, **k: io.BytesIO(body)).generate("s", "p", lambda t: None, self.cancel)
        self.assertEqual(caught.exception.status, 429)
        self.assertEqual(caught.exception.retry_after, 20)

    def test_total_deadline_and_pre_cancel_do_not_open_network(self):
        calls = []
        def opener(*a, **k):
            calls.append(1)
            return io.BytesIO(event({}))
        self.cancel.set()
        with self.assertRaises(Cancelled):
            GeminiClient(self.settings, opener).generate("s", "p", lambda t: None, self.cancel)
        self.assertEqual(calls, [])
        self.cancel.clear()
        with patch("cotu_app.features.chatbot.gemini.time.monotonic", side_effect=[0, 36]), self.assertRaises(APIError):
            GeminiClient(self.settings, opener).generate("s", "p", lambda t: None, self.cancel)
        self.assertEqual(calls, [])


class ConfigCase(unittest.TestCase):
    def test_env_is_data_not_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("GEMINI_API_KEY=file_key\nGEMINI_MODEL='gemini-3.1-flash-lite'\nTEST_LITERAL=$(printf unsafe)\n")
            with patch.dict(os.environ, {"GEMINI_API_KEY": "environment_key"}, clear=True):
                load_env(env)
                self.assertEqual(os.environ["GEMINI_API_KEY"], "environment_key")
                self.assertEqual(os.environ["TEST_LITERAL"], "$(printf unsafe)")

    def test_settings_reject_url_model_and_invalid_timeouts(self):
        for values in ({"model": "https://untrusted"}, {"timeout": -1}, {"min_interval": float("nan")}, {"timeout": 1000}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                Settings(**values)
        self.assertNotIn("DO_NOT_LEAK", repr(Settings(api_key="DO_NOT_LEAK")))


if __name__ == "__main__":
    unittest.main()
