#!/usr/bin/env python3
"""
WSL → Discord へメッセージをプッシュする CLI ツール。
Discord Webhook を使うため、bot.py が起動していなくても動作する。

使い方:
  python notify.py "メッセージ"
  echo "完了" | python notify.py
  python notify.py --code "git log --oneline -5" の実行結果
"""

import os
import sys
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


def send(content: str) -> None:
    if not WEBHOOK_URL:
        print("[notify] DISCORD_WEBHOOK_URL が未設定です", file=sys.stderr)
        sys.exit(1)

    # Discord の上限 2000 文字でチャンク分割
    chunks = [content[i : i + 1990] for i in range(0, len(content), 1990)]
    for chunk in chunks:
        payload = json.dumps({"content": chunk}).encode()
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            print(f"[notify] HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
            sys.exit(1)


def main() -> None:
    if not sys.stdin.isatty():
        # パイプ入力
        content = sys.stdin.read().strip()
    elif len(sys.argv) > 1:
        content = " ".join(sys.argv[1:])
    else:
        print("Usage: notify.py <message>  or  echo <msg> | notify.py", file=sys.stderr)
        sys.exit(1)

    send(content)
    print("[notify] sent.")


if __name__ == "__main__":
    main()
