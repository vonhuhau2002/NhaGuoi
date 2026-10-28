import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys

from cotu_app.core.paths import BASE
from .config import ROOT, Settings
from .retrieval import Retriever, build_index, index_path
from .service import ChatService
from .presentation import visitor_answer


def parser():
    cli = argparse.ArgumentParser(description="Chatbot Cơ Tu nhẹ cho Raspberry Pi 5")
    sub = cli.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Kiểm tra môi trường, không gọi mạng")
    for name in ("build-index", "ask", "chat", "desktop", "evaluate"):
        item = sub.add_parser(name)
        item.add_argument("--mode", choices=("approved", "research"), default="approved")
        if name == "build-index":
            item.add_argument("--corpus", type=Path, default=ROOT / "corpus/documents.jsonl")
        elif name == "evaluate":
            item.add_argument("--questions", type=Path, default=ROOT / "evaluation/questions.seed.jsonl")
            item.add_argument("--rounds", type=int, default=100)
            item.add_argument("--output", type=Path)
        else:
            item.add_argument("--offline", action="store_true")
            if name == "ask":
                item.add_argument("question")
                item.add_argument("--json", action="store_true")
                item.add_argument("--stream", action="store_true", help="Bản nháp stream ra stderr")
    return cli


def display(result):
    print(visitor_answer(result))


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        settings = Settings.from_env()
        if args.command == "doctor":
            with sqlite3.connect(":memory:") as db:
                db.execute("CREATE VIRTUAL TABLE check_fts USING fts5(text)")
            print(json.dumps({"python": platform.python_version(), "machine": platform.machine(),
                              "sqlite": sqlite3.sqlite_version, "fts5": True,
                              "tkinter": importlib.util.find_spec("tkinter") is not None,
                              "display_available": bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY")),
                              "api_key_configured": bool(settings.api_key), "model": settings.model,
                              "indexes": {m: index_path(m).exists() for m in ("approved", "research")}}, indent=2))
            return 0
        if args.command == "build-index":
            print(json.dumps(build_index(args.corpus, index_path(args.mode), args.mode), indent=2))
            return 0
        retriever = Retriever(index_path(args.mode), args.mode)
        if args.command == "evaluate":
            from .evaluation import evaluate
            report = evaluate(retriever, args.questions, args.rounds)
            target = args.output or BASE / "reports/chatbot" / f"retrieval.{args.mode}.local.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False, indent=2))
            print(f"Báo cáo: {target}")
            return 0
        service = ChatService(retriever, settings)
        if args.command == "desktop":
            from .desktop import run_desktop
            run_desktop(service, args.offline)
        elif args.command == "ask":
            def delta(text):
                if args.stream and not args.json:
                    print(text, end="", flush=True, file=sys.stderr)
            result = service.ask(args.question, offline=args.offline, on_delta=delta)
            if args.stream and not args.json:
                print("\n--- Kết quả sau kiểm tra ---", file=sys.stderr)
            if args.json:
                print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            else:
                display(result)
        else:
            history = []
            print("/quit: thoát • /reset: phiên mới. Câu hỏi và đoạn chọn gửi Google khi dùng API.")
            while True:
                question = input("\nBạn: ").strip()
                if question == "/quit":
                    break
                if question == "/reset":
                    history.clear()
                    print("Đã xóa ngữ cảnh.")
                    continue
                result = service.ask(question, history, offline=args.offline)
                display(result)
                if result.status == "answered":
                    history.extend([{"role": "user", "content": question},
                                    {"role": "assistant", "content": result.answer_text}])
                    history = history[-4:]
        return 0
    except (ValueError, OSError, sqlite3.Error) as error:
        # Configuration/index errors are local, API errors are sanitized by client.
        print(f"Lỗi: {error}", file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("\nĐã thoát.", file=sys.stderr)
        return 0
    except Exception as error:
        if type(error).__name__ == "TclError":
            print("Không mở được Tkinter. Chạy trên desktop Pi hoặc dùng lệnh ask/chat.", file=sys.stderr)
            return 2
        raise
