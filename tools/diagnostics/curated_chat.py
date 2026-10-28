"""Audit curated chat routing/cache; --play measures a cached answer on the speaker.

Run with the selected release's Python, PYTHONPATH and NHARONG_DATA_DIR.
No API request or TTS model load is permitted by this diagnostic.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time
from unittest.mock import Mock, patch

from cotu_app.core.files import resolve_path
from cotu_app.core.settings import CONFIG, load_config
from cotu_app.features.chatbot.config import Settings
from cotu_app.features.chatbot.service import ChatService
from cotu_app.features.stories.catalog import CuratedCatalog
from cotu_app.features.stories.questions import load_story_questions
from cotu_app.features.tts.voices import voice_for
from cotu_app.features.tts.worker import AudioEngine, AudioWorker, play_cached
from cotu_app.features.video.content import video_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--play', action='store_true')
    parser.add_argument('--question', default='Nhà Gươl là gì?')
    parser.add_argument('--output', type=Path, default=Path('reports/tts/curated-chat.json'))
    args = parser.parse_args()
    config = load_config(CONFIG)
    started = time.monotonic()
    catalog = CuratedCatalog.load(CONFIG, config)
    report = {'measured_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'Curated chat with existing WAV; excludes arbitrary new AI answers',
              'catalog_load_ms': round((time.monotonic() - started) * 1000, 3)}
    retriever, client = Mock(mode='research'), Mock()
    retriever.search.side_effect = AssertionError('Curated path must not retrieve AI evidence')
    client.generate.side_effect = AssertionError('Curated path must not call API')
    service = ChatService(retriever, Settings(), client, curated=catalog)
    engine = AudioEngine()
    engine.get_model = Mock(side_effect=AssertionError('Cached answers must not load a model'))
    items, digests, timings, wordings = {}, {}, [], set()
    for cid, story in config['stories'].items():
        video = resolve_path(CONFIG, story.get('video'))
        if video not in digests:
            digests[video] = video_digest(video)
        for item in load_story_questions(CONFIG, config, cid, digests[video]):
            for wording in [item['question'], *item.get('aliases', [])]:
                start = time.monotonic()
                result = service.ask(wording, character_id=cid, offline=True)
                timings.append((time.monotonic() - start) * 1000)
                assert result.metrics.get('route') == 'curated', wording
                assert result.audio_text == item['answer'], wording
                assert result.character_id == item.get('character_id', cid), wording
                assert not result.metrics['api_called']
                wordings.add(wording)
            voice, rate = voice_for(result.character_id)
            audio_item = {'text': result.audio_text, 'voice': voice, 'rate': rate}
            items[engine.path_for(audio_item)] = audio_item
    report.update(unique_question_wordings=len(wordings), routing_checks=len(timings),
                  routing_max_ms=round(max(timings), 3),
                  unique_audio_answers=len(items), cached_wavs=sum(bool(engine.cached(i)) for i in items.values()),
                  api_calls=client.generate.call_count, evidence_searches=retriever.search.call_count)

    if args.play:
        import sounddevice as sd
        import tkinter as tk
        from cotu_app.features.chatbot.desktop import ChatPanel

        root = tk.Tk()
        root.withdraw()
        first_write, writes, underflows, events = [], [], [], []
        completed = threading.Event()
        original = sd.OutputStream

        class MeasuredOutput:
            def __init__(self, *a, **kw):
                self.stream = original(*a, **kw)
            def __enter__(self):
                self.stream.__enter__()
                return self
            def __exit__(self, *a):
                return self.stream.__exit__(*a)
            def abort(self):
                self.stream.abort()
            def write(self, data):
                now = time.monotonic()
                writes.append(now)
                if not first_write:
                    first_write.append(now)
                outcome = self.stream.write(data)
                if outcome:
                    underflows.append(len(writes))
                return outcome

        def emit(event):
            events.append(event)
            if 'code' in event:
                completed.set()

        worker = AudioWorker(engine, emit, play_cached)

        def read(text, cid):
            voice, rate = voice_for(cid)
            item = {'text': text, 'voice': voice, 'rate': rate}
            assert engine.cached(item), 'Missing WAV; refusing synthesis during cache benchmark'
            worker.submit({'id': 1, 'kind': 'speak', **item})

        panel = ChatPanel(root, service, offline=True, read_answer=read)
        worker.start()
        try:
            with patch.object(sd, 'OutputStream', MeasuredOutput):
                started = time.monotonic()
                assert panel.submit_question(args.question)
                deadline = started + 90
                while not completed.is_set() and time.monotonic() < deadline:
                    root.update()
                    time.sleep(.005)
                assert completed.is_set() and events[-1].get('code') == 0, events
                assert first_write, 'No samples sent to speaker'
            report.update(question=args.question,
                          submit_to_first_usb_write_seconds=round(first_write[0] - started, 3),
                          playback_completed=True, usb_underflows=len(underflows),
                          max_usb_write_interval_seconds=round(max(
                              (b-a for a, b in zip(writes, writes[1:])), default=0), 4))
        finally:
            panel.dispose()
            root.destroy()
            worker.close()
    report['model_load_calls'] = engine.get_model.call_count
    assert report['api_calls'] == report['evidence_searches'] == report['model_load_calls'] == 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
