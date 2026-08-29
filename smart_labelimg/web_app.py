from __future__ import annotations

import argparse
from pathlib import Path
from threading import Timer
import webbrowser

import uvicorn

from smart_labelimg.web_service import create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Smart Label as a local web application")
    parser.add_argument("--dataset", type=Path, help="Image dataset directory to open at startup")
    parser.add_argument("--port", type=int, default=7860, help="Local HTTP port (default: 7860)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    url = f"http://127.0.0.1:{args.port}"
    if not args.no_browser:
        Timer(0.8, lambda: webbrowser.open(url)).start()
    uvicorn.run(
        create_app(initial_dataset=args.dataset),
        host="127.0.0.1",
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
