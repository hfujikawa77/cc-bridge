from mcp.server.fastmcp import FastMCP
import os
import json
import urllib.request

mcp = FastMCP("Stack-chan Speaker")

DEFAULT_IP = os.environ.get("STACKCHAN_IP", "192.168.3.3")


@mcp.tool()
def speak(text: str, ip: str = "") -> str:
    """スタックちゃんに指定テキストを喋らせる。ip を省略すると STACKCHAN_IP 環境変数の値を使う。"""
    target_ip = ip.strip() or DEFAULT_IP
    url = f"http://{target_ip}/speak"
    payload = json.dumps({"text": text}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            return f"送信しました ({target_ip}): {text}\nレスポンス: {body}"
    except Exception as e:
        return f"エラー ({target_ip}): {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
