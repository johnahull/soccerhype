#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Entry point for `python -m soccerhype serve`."""

import sys


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "serve":
        print("Usage: python -m soccerhype serve [--port PORT] [--no-browser]")
        print()
        print("Commands:")
        print("  serve    Start the web UI server")
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser(prog="soccerhype serve")
    parser.add_argument("command")  # "serve"
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    import uvicorn
    from web.app import app

    if not args.no_browser:
        import webbrowser
        import threading
        threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{args.port}")).start()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
