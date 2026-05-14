#!/usr/bin/env python3
"""MCP server — Discord 通知ツールを Claude Code に公開する。"""

import json
import os
import sys
import urllib.error
import urllib.request

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

BOT_TOKEN = os.environ.get("DISCORD_TOKEN", "")
CHANNEL_ID = os.environ.get("NOTIFY_CHANNEL_ID", "")

mcp = FastMCP("cc-bridge")


@mcp.tool()
def notify(message: str) -> str:
    """Discord のチャンネルにメッセージを送信する。"""
    if not BOT_TOKEN:
        return "エラー: DISCORD_TOKEN が未設定です"
    if not CHANNEL_ID:
        return "エラー: NOTIFY_CHANNEL_ID が未設定です"

    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
    chunks = [message[i : i + 1990] for i in range(0, len(message), 1990)]
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
            return f"エラー: HTTP {e.code}: {e.read().decode()}"

    return "送信しました。"


if __name__ == "__main__":
    mcp.run()
