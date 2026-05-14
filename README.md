# cc-bridge

Discord から Claude Code CLI を操作するボット。メンションで会話を開始し、スレッド内で Claude との対話を継続できます。

## 機能

- **Claude 対話**: メンションでスレッドを自動作成し、Claude CLI を呼び出して返答
- **会話継続**: スレッド内のメッセージは同一セッションで継続（`--resume` 使用）
- **ボット間しりとり**: 他ボットからのメンションにしりとり形式で応答
- **スクリプト実行**: `!run <script>` でリポジトリ内のシェルスクリプトを実行
- **天気表示**: `!weather [YYYY-MM-DD]` で東京の天気を表示（APIキー不要）
- **通知送信**: `notify.py` で bot なしに Webhook 経由で Discord へメッセージ送信

## セットアップ

```bash
pip install -r requirements.txt
```

`.env` を作成して以下を設定：

```env
DISCORD_TOKEN=your_bot_token
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...  # notify.py 用
REPO_ROOT=~/GitHub/claw-io-hub                            # スクリプト実行のベースディレクトリ（省略可）
ALLOWED_USER_IDS=123456789,987654321                      # 操作を許可するユーザーID（省略時: 全員許可）
```

## 起動

```bash
python3 bot.py
```

## コマンド

| コマンド | 説明 |
|----------|------|
| `@ボット名 <質問>` | Claude との会話を開始（スレッドを自動作成） |
| `!run <script>` | スクリプトを実行（`tweets` / `briefing` / `journal` / `weather`） |
| `!scripts` | 利用可能なスクリプト一覧を表示 |
| `!weather [YYYY-MM-DD]` | 東京の天気を表示（日付省略時: 今日） |
| `!clear` | このスレッドの会話セッションをリセット |

## notify.py（単体通知）

`bot.py` が起動していなくても Discord に通知を送れます。

```bash
python3 notify.py "デプロイ完了"
echo "エラーが発生しました" | python3 notify.py
```

## ファイル構成

```
bot.py          # Discord ボット本体
weather.py      # 天気取得モジュール（wttr.in / Open-Meteo）
notify.py       # Webhook 経由の単体通知 CLI
requirements.txt
.env            # 環境変数（git 管理外）
```
