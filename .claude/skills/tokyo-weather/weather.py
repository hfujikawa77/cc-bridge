#!/usr/bin/env python3
"""
Tokyo weather fetcher — no API key required.
Primary: wttr.in  /  Fallback: Open-Meteo
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

WMO = {
    0: "快晴", 1: "晴れ", 2: "一部曇り", 3: "曇り",
    45: "霧", 48: "霧",
    51: "霧雨(弱)", 53: "霧雨", 55: "霧雨(強)",
    61: "小雨", 63: "雨", 65: "大雨",
    71: "小雪", 73: "雪", 75: "大雪",
    80: "にわか雨", 81: "にわか雨", 82: "激しいにわか雨",
    95: "雷雨", 96: "雷雨", 99: "激しい雷雨",
}


def _get(url: str, timeout: int = 10) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def _wttr() -> str:
    d = _get("https://wttr.in/Tokyo?format=j1")
    today = d["weather"][0]
    max_c = today["maxtempC"]
    min_c = today["mintempC"]
    rise  = today["astronomy"][0]["sunrise"]
    sets  = today["astronomy"][0]["sunset"]

    lines = [f"最高 {max_c}°C / 最低 {min_c}°C  (日出 {rise} 日没 {sets})"]
    for slot in today["hourly"]:
        t    = slot["time"].zfill(4)
        hhmm = f"{t[:2]}:{t[2:]}"
        desc = slot["weatherDesc"][0]["value"]
        temp = slot["tempC"]
        rain = slot["chanceofrain"]
        lines.append(f"{hhmm}  {temp}°C  {desc}  降水{rain}%")
    return "\n".join(lines)


def _open_meteo() -> str:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=35.6895&longitude=139.6917"
        "&hourly=temperature_2m,precipitation_probability,weathercode"
        "&timezone=Asia%2FTokyo&forecast_days=1"
    )
    d = _get(url)
    h = d["hourly"]
    lines = []
    for i, t in enumerate(h["time"]):
        hhmm = t[11:16]
        temp = h["temperature_2m"][i]
        prob = h["precipitation_probability"][i]
        desc = WMO.get(h["weathercode"][i], f"コード{h['weathercode'][i]}")
        lines.append(f"{hhmm}  {temp}°C  {desc}  降水{prob}%")
    return "\n".join(lines)


def fetch(date: str | None = None) -> str:
    """東京の天気を文字列で返す。date は YYYY-MM-DD（省略時: 今日）。"""
    if date is None:
        date = datetime.now(JST).strftime("%Y-%m-%d")

    header = f"東京の天気 {date}"
    for fn, label in [(_wttr, "wttr.in"), (_open_meteo, "Open-Meteo")]:
        try:
            body = fn()
            return f"{header}（{label}）\n{body}"
        except Exception:
            continue
    return f"{header}\n取得失敗"


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    print(fetch(date))
