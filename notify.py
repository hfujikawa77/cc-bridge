#!/usr/bin/env python3
"""
WSL → Discord へメッセージをプッシュする CLI ツール。
bot.py と同じBotトークンでチャンネルへ直接送信する。

使い方:
  python notify.py "メッセージ"
  echo "完了" | python notify.py
"""

import os
import sys
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

BOT_TOKEN = os.environ.get("DISCORD_TOKEN", "")
CHANNEL_ID = os.environ.get("NOTIFY_CHANNEL_ID", "")


def send(content: str) -> None:
    if not BOT_TOKEN:
        print("[notify] DISCORD_TOKEN が未設定です", file=sys.stderr)
        sys.exit(1)
    if not CHANNEL_ID:
        print("[notify] NOTIFY_CHANNEL_ID が未設定です", file=sys.stderr)
        sys.exit(1)

    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
    chunks = [content[i : i + 1990] for i in range(0, len(content), 1990)]
    for chunk in chunks:
        payload = json.dumps({"content": chunk}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bot {BOT_TOKEN}",
                "User-Agent": "DiscordBot (cc-bridge, 1.0)",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            print(f"[notify] HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
            sys.exit(1)


def main() -> None:
    if not sys.stdin.isatty():
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
