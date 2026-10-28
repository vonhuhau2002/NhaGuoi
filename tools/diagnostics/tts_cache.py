"""Compare source/installed answer caches without loading a model or playing audio."""

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "src"))

from cotu_app.core.files import resolve_path
from cotu_app.core.settings import load_config
from cotu_app.features.stories.questions import load_story_questions
from cotu_app.features.tts.voices import voice_for
from cotu_app.features.tts.worker import AudioEngine
from cotu_app.features.video.content import video_digest


def probe(model, cache, items):
    engine = AudioEngine(model, cache)
    timings, ready = [], 0
    for item in items:
        start = time.perf_counter()
        ready += bool(engine.cached(item))
        timings.append((time.perf_counter() - start) * 1000)
    timings.sort()
    return {"ready": ready, "total": len(items), "fingerprint": engine.fingerprint,
            "lookup_median_ms": round(statistics.median(timings), 3),
            "lookup_p95_ms": round(timings[max(0, math.ceil(len(timings) * .95) - 1)], 3)}


def manifest(model):
    return {str(p.relative_to(model)): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in model.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-root", type=Path,
                        default=Path.home() / ".local/share/nharong-cotu")
    parser.add_argument("--output", type=Path, default=BASE / "reports/tts/cache-check.json")
    args = parser.parse_args()
    config_file = BASE / "config/video_stories.json"
    config = load_config(config_file)
    questions = []
    for cid, story in config["stories"].items():
        video = resolve_path(config_file, story.get("video"))
        if video and video.is_file():
            questions.extend(load_story_questions(config_file, config, cid, video_digest(video)))
    items = list({(q["answer"], *voice_for(q.get("character_id", "elder"))):
                  {"text": q["answer"], "voice": voice_for(q.get("character_id", "elder"))[0],
                   "rate": voice_for(q.get("character_id", "elder"))[1]} for q in questions}.values())
    if not items:
        raise ValueError("Chưa có câu hỏi để kiểm tra cache.")
    source_model = BASE / ".venv-video/models/zerotts"
    report = {"checked_at": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
              "measurement": "WAV cache lookup only; no model load, synthesis, or audio playback",
              "source": probe(source_model, BASE / "var/cache/tts", items)}
    current = args.installed_root / "current"
    if current.is_symlink():
        installed = current.resolve(strict=True)
        installed_model = installed / ".venv-video/models/zerotts"
        shared = args.installed_root / "shared"
        cache = shared / ".tts_cache" if (shared / ".tts_cache").is_dir() else shared / "cache/tts"
        report["installed"] = {"version": installed.name, **probe(installed_model, cache, items)}
        source_files, installed_files = manifest(source_model), manifest(installed_model)
        report["model_comparison"] = {
            "file_names_and_sizes_equal": {p: s[0] for p, s in source_files.items()} ==
                                         {p: s[0] for p, s in installed_files.items()},
            "mtime_differences": sum(installed_files.get(p, (None, None))[1] != stats[1]
                                     for p, stats in source_files.items()),
            "config_content_equal": hashlib.sha256((source_model / "config.json").read_bytes()).hexdigest() ==
                                    hashlib.sha256((installed_model / "config.json").read_bytes()).hexdigest(),
            "cache_keys_equal": report["source"]["fingerprint"] == report["installed"]["fingerprint"],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
