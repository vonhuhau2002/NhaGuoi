"""Embed the chatbot feature in either desktop application."""

import json
import sqlite3
from cotu_app.core.paths import CONFIG_DIR
from .config import chatbot_options
from cotu_app.core.branding import CHAT_NAME


def create_service(mode):
    from cotu_app.features.chatbot.config import ROOT, Settings
    from cotu_app.features.chatbot.retrieval import Retriever, build_index, index_path
    from cotu_app.features.chatbot.service import ChatService

    target = index_path(mode)
    # First-launch preparation only, never rebuild while answering a question.
    if not target.is_file():
        build_index(ROOT / "corpus/documents.jsonl", target, mode)
    return ChatService(Retriever(target, mode), Settings.from_env())


def prepare_chat(app):
    if getattr(app, "busy", False):
        return "Đang nạp nội dung hoặc nhận dạng mic. Chờ hoàn tất rồi gửi nhé."
    if hasattr(app, "pause"):
        app.pause()
    app.stop_speech()
    # Start model loading while the network is preparing the validated answer.
    from cotu_app.features.tts.service import warmup_speech
    try:
        warmup_speech()
    except (OSError, ValueError, RuntimeError):
        pass  # Text chat remains available when speech is unavailable.
    return None


def read_chat_answer(app, text, character_id):
    from cotu_app.features.tts.service import start_speech

    app.stop_speech()
    try:
        app.speech = start_speech(text, character_id)
        if hasattr(app, "speech_kind"):
            app.speech_kind = "chat"
        app.status.set("Đang chuẩn bị giọng đọc để đọc liền mạch...")
    except (OSError, ValueError, RuntimeError):
        app.status.set("Đã có câu trả lời trên màn hình; chưa phát được giọng đọc.")


def mount_chatbot(app, config=None):
    import tkinter as tk
    from tkinter import ttk
    from cotu_app.ui.keyboard import TouchKeyboard

    if config is None:
        config = json.loads((CONFIG_DIR / "video_stories.json").read_text(encoding="utf-8"))
    options = chatbot_options(config)
    app.chat_panel, app.chat_tab = None, None
    if not options["enabled"]:
        return
    tab = ttk.Frame(app.tabs)
    app.chat_tab = tab
    # Place chat beside the existing questions, ahead of teacher settings.
    before = getattr(app, "setup_tab", None)
    if before is not None:
        app.tabs.insert(before, tab, text=CHAT_NAME)
    else:
        app.tabs.add(tab, text=CHAT_NAME)
    if hasattr(app, "refresh_navigation"):
        app.refresh_navigation()
    try:
        service = create_service(options["mode"])
        from cotu_app.features.stories.catalog import CuratedCatalog
        service.curated = CuratedCatalog.load(
            getattr(app, "config_path", CONFIG_DIR / "video_stories.json"), config)
        from cotu_app.features.chatbot.desktop import ChatPanel
        app.chat_panel = ChatPanel(
            tab, service, before_send=lambda: prepare_chat(app),
            read_answer=lambda text, cid: read_chat_answer(app, text, cid),
            stop_audio=app.stop_speech, keyboard_factory=TouchKeyboard)
        app.chat_panel.pack(fill="both", expand=True)
        sync_character(app)
        # Loading the local model can take time on an SD card. Start it at
        # app launch; the worker loads asynchronously while visitors navigate.
        from cotu_app.features.tts.service import warmup_speech
        try:
            app.tts_warmup = warmup_speech()
        except (OSError, ValueError, RuntimeError):
            app.tts_warmup = None
    except (OSError, ValueError, RuntimeError, ImportError, sqlite3.Error):
        tk.Label(tab, text="Chưa mở được chatbot. Kiểm tra config/chatbot/.env và chạy\n"
                 "./run_chatbot.sh doctor rồi dựng lại chỉ mục.",
                 font=("DejaVu Sans", 12), wraplength=700).pack(padx=16, pady=20)


def sync_character(app, *, reset=False):
    from cotu_app.features.stories.characters import CHARACTERS

    panel = getattr(app, "chat_panel", None)
    if panel is not None:
        cid = app.cid if hasattr(app, "cid") else app.session.character_id
        panel.set_character(cid, CHARACTERS[cid]["name"], reset=reset)


def reload_curated(app):
    """Replace the lookup snapshot after changing a source in teacher settings."""
    panel = getattr(app, "chat_panel", None)
    if panel is not None:
        from cotu_app.features.stories.catalog import CuratedCatalog
        panel.service.curated = CuratedCatalog.load(app.config_path, app.config)


def open_chatbot(app, question=None):
    panel = getattr(app, "chat_panel", None)
    if panel is None:
        return False
    app.tabs.select(app.chat_tab)
    if question is not None:
        panel.submit_question(question)
    return True


def chatbot_tab_changed(app):
    panel = getattr(app, "chat_panel", None)
    if panel is not None:
        if app.tabs.select() != str(app.chat_tab):
            panel.hide_keyboard()
            panel.stop()
        else:
            if hasattr(app, "pause"):
                app.pause()
            app.stop_speech()


def close_chatbot(app):
    panel = getattr(app, "chat_panel", None)
    if panel is not None:
        panel.dispose()
