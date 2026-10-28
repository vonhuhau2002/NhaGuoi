"""Read-only lookup of validated answers, loaded once when the app opens."""

import logging
from pathlib import Path

from cotu_app.core.files import resolve_path
from cotu_app.core.text import question_key
from .questions import load_document_questions, load_questions

log = logging.getLogger(__name__)


class CuratedCatalog:
    def __init__(self, banks):
        self._index = {}
        for cid, questions in banks.items():
            index = self._index[cid] = {}
            for item in questions:
                for wording in [item["question"], *item.get("aliases", [])]:
                    key = question_key(wording)
                    if not key:
                        continue
                    if key in index and index[key] != item:
                        # Ambiguous wording must fall through to the normal
                        # chat flow, never choose an arbitrary approved answer.
                        index[key] = None
                    else:
                        index[key] = item

    def find(self, question, character_id):
        return self._index.get(character_id, {}).get(question_key(question))

    @classmethod
    def load(cls, config_path, config):
        from cotu_app.features.video.content import video_digest

        documents = []
        for value in dict.fromkeys(config.get("document_questions", [])):
            path = resolve_path(config_path, value)
            try:
                documents.extend(load_document_questions(path))
            except (OSError, ValueError) as error:
                log.warning("Không nạp bộ hỏi đáp %s: %s", path.name, error)

        banks, videos = {}, {}
        for cid, story in config.get("stories", {}).items():
            questions = []
            path = resolve_path(config_path, story.get("questions"))
            video = resolve_path(config_path, story.get("video"))
            if path is not None:
                pair = (path, video)
                if pair not in videos:
                    try:
                        digest = video_digest(video) if video is not None else None
                        if digest is None:
                            raise ValueError("Bộ hỏi đáp thiếu video nguồn.")
                        videos[pair] = load_questions(path, digest)
                    except (OSError, ValueError) as error:
                        log.warning("Không nạp bộ hỏi đáp %s: %s", path.name, error)
                        videos[pair] = []
                questions = [{**item, "character_id": item.get("character_id", cid),
                              "source_label": f"{Path(video).name} — {path.name}"}
                             for item in videos[pair]]
            banks[cid] = [*questions, *documents]
        return cls(banks)
