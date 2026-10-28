"""Measure full-answer preparation and playback continuity without a chat API call.

    PYTHONPATH=src .venv-video/bin/python tools/diagnostics/chat_latency.py \
        --baseline-release ~/.local/share/nharong-cotu/releases/1.1.1 --play

Close other TTS applications first. --play also tests the configured speaker.
"""

import argparse
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
import wave
from zoneinfo import ZoneInfo

from cotu_app.core.paths import MODEL_DIR
from cotu_app.features.tts.worker import AudioEngine, AudioWorker, play_cached


TEXT = ('Nhà Gươl là không gian sinh hoạt chung của cộng đồng Cơ Tu. '
        'Người dân gặp gỡ, tổ chức lễ hội và truyền dạy văn hóa tại đây.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-release', type=Path)
    parser.add_argument('--output', type=Path, default=Path('reports/tts/chat-latency.json'))
    parser.add_argument('--play', action='store_true')
    args = parser.parse_args()
    import numpy as np

    report = {'measured_at': datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(),
              'scope': 'Local TTS only; fixed text, one shared warmed model, empty per-run caches; excludes chat API latency',
              'text': TEXT, 'voice': 'huuduc', 'rate': .88}
    item = {'text': TEXT, 'voice': 'huuduc', 'rate': .88}
    with tempfile.TemporaryDirectory(prefix='nha-guoi-latency-') as folder:
        engine = AudioEngine(MODEL_DIR, Path(folder) / 'after')
        started = time.monotonic()
        model = engine.get_model(lambda message: print(message, flush=True))
        model.warmup()
        report['inference_threads'] = model.prefix_step_sess.get_session_options().intra_op_num_threads
        report['codec_threads'] = model.codec._decode_step_sess.get_session_options().intra_op_num_threads
        report['model_load_and_warmup_seconds'] = round(time.monotonic() - started, 3)
        print('Model ready:', report['model_load_and_warmup_seconds'], 's', flush=True)
        if args.baseline_release:
            spec = importlib.util.spec_from_file_location(
                'cotu_app.features.tts._baseline_worker',
                args.baseline_release / 'src/cotu_app/features/tts/worker.py')
            baseline = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(baseline)
            old = baseline.AudioEngine(MODEL_DIR, Path(folder) / 'before')
            old.model = model
            np.random.seed(7)
            started = time.monotonic()
            old.render(item)
            report['before_tts_wait_seconds'] = round(time.monotonic() - started, 3)
            print('Before first audio:', report['before_tts_wait_seconds'], 's', flush=True)

        path = engine.path_for(item)
        if not args.play:
            np.random.seed(7)
            started = time.monotonic()
            engine.render(item)
            report['full_answer_preparation_seconds'] = round(time.monotonic() - started, 3)
            print('Full answer prepared:', report['full_answer_preparation_seconds'], 's', flush=True)

        if args.play:
            import sounddevice as sd
            from unittest.mock import patch

            original = sd.OutputStream
            first_write, finished = [], threading.Event()
            write_times, underflows = [], []
            events = []
            class MeasuredOutput:
                def __init__(self, *a, **kw):
                    assert engine.cached(item) is not None, 'Speaker started before the answer was complete'
                    self.stream = original(*a, **kw)
                def __enter__(self):
                    self.stream.__enter__()
                    return self
                def __exit__(self, *a):
                    return self.stream.__exit__(*a)
                def abort(self):
                    self.stream.abort()
                def write(self, data):
                    write_times.append(time.monotonic())
                    if not first_write:
                        first_write.append(time.monotonic())
                    underflowed = self.stream.write(data)
                    if underflowed:
                        underflows.append(len(write_times))
                    return underflowed
            def emit(event):
                events.append(event)
                if 'code' in event:
                    finished.set()
            # Force an uncached answer through the normal worker and real speaker.
            np.random.seed(7)
            worker = AudioWorker(engine, emit, play_cached)
            with patch.object(sd, 'OutputStream', MeasuredOutput):
                worker.start()
                started = time.monotonic()
                try:
                    worker.submit({'id': 1, 'kind': 'speak', **item})
                    assert finished.wait(90), 'Buffered speech timed out'
                    assert events[-1].get('code') == 0, events[-1]
                    assert first_write, 'No audio reached the output stream'
                    report['uncached_request_to_usb_seconds'] = round(first_write[0] - started, 3)
                    report['usb_playback_wall_seconds'] = round(time.monotonic() - first_write[0], 3)
                    report['usb_output_underflows'] = len(underflows)
                    report['usb_max_write_interval_seconds'] = round(max(
                        (b - a for a, b in zip(write_times, write_times[1:])), default=0), 4)
                    report['usb_playback_completed'] = True
                    report['complete_wav_before_speaker_opened'] = True
                finally:
                    worker.close()
        with wave.open(str(path), 'rb') as audio:
            report['audio_seconds'] = round(audio.getnframes() / audio.getframerate(), 3)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
