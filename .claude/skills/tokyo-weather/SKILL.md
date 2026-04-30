---
name: tokyo-weather
description: 東京の天気を取得して表示する（wttr.in / Open-Meteo 使用、APIキー不要・無料）。日付を指定することも可能。
user-invocable: true
argument-hint: [YYYY-MM-DD]
allowed-tools:
  - Bash(python *)
  - Bash(curl *)
---

# Tokyo Weather

東京の天気情報を取得して表示する。

## 手順

1. `$ARGUMENTS` が指定されていれば日付として使う。省略時は今日。

2. 以下を実行する：

```bash
python .claude/skills/tokyo-weather/weather.py $ARGUMENTS
```

3. 出力をそのまま表示する。

## フォールバック

`weather.py` が存在しない場合は `curl` で直接取得する：

```bash
# 簡易表示
curl -s "https://wttr.in/Tokyo?format=3"

# 詳細（JSON）
curl -s "https://wttr.in/Tokyo?format=j1" | python3 -c "
import sys, json
d = json.load(sys.stdin)
t = d['weather'][0]
print(f\"最高 {t['maxtempC']}°C / 最低 {t['mintempC']}°C\")
for h in t['hourly']:
    tm = h['time'].zfill(4)
    print(f\"{tm[:2]}:{tm[2:]}  {h['tempC']}°C  {h['weatherDesc'][0]['value']}  降水{h['chanceofrain']}%\")
"
```
