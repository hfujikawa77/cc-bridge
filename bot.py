import asyncio
import json
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import weather as weather_mod

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
REPO_ROOT = os.path.expanduser(os.environ.get("REPO_ROOT", "~/GitHub/claw-io-hub"))
ALLOWED_USER_IDS = set(
    int(x) for x in os.environ.get("ALLOWED_USER_IDS", "").split(",") if x.strip()
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# thread_id → claude session_id (--resume で会話を継続)
conversations: dict[int, str] = {}

SCRIPTS = {
    "tweets":   "~/GitHub/claw-io-hub/scripts/collect-tweets/run.sh",
    "briefing": "~/GitHub/claw-io-hub/scripts/generate/briefing.sh",
    "journal":  "~/GitHub/claw-io-hub/scripts/generate/daily_journal.sh",
    "weather":  "~/GitHub/claw-io-hub/scripts/weather/post_tokyo_weather.sh",
}


def is_allowed_id(user_id: int) -> bool:
    return not ALLOWED_USER_IDS or user_id in ALLOWED_USER_IDS


def is_allowed(ctx: commands.Context) -> bool:
    return is_allowed_id(ctx.author.id)


def bot_is_mentioned(message: discord.Message) -> bool:
    if bot.user in message.mentions:
        return True
    if message.guild:
        member = message.guild.get_member(bot.user.id)
        if member:
            bot_role_ids = {r.id for r in member.roles}
            return any(r.id in bot_role_ids for r in message.role_mentions)
    return False


def extract_prompt(message: discord.Message) -> str:
    text = message.clean_content
    if message.guild:
        for role in message.guild.me.roles:
            text = text.replace(f"@{role.name}", "")
    return text.replace(f"@{bot.user.display_name}", "").strip()


async def send_chunked(target, text: str) -> None:
    text = text or "(no output)"
    for i in range(0, len(text), 1990):
        await target.send(text[i : i + 1990])


async def run_subprocess(
    args: list[str], cwd: str, timeout: int = 300
) -> tuple[str, int]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return f"Timeout after {timeout}s", -1
    return stdout.decode().strip(), proc.returncode


async def call_claude(prompt: str, session_id: str | None = None) -> tuple[str, str]:
    """claude CLI を呼び出し (reply, new_session_id) を返す。OAuth を自動使用。"""
    args = [
        "claude", "--dangerously-skip-permissions",
        "-p", prompt,
        "--output-format", "json",
    ]
    if session_id:
        args += ["--resume", session_id]

    raw, code = await run_subprocess(args, cwd=REPO_ROOT, timeout=120)
    try:
        data = json.loads(raw)
        return data["result"], data["session_id"]
    except (json.JSONDecodeError, KeyError):
        return raw or "(no response)", ""


async def start_thread(message: discord.Message) -> None:
    prompt = extract_prompt(message)
    if not prompt:
        await message.reply("何か質問してください。")
        return

    if isinstance(message.channel, discord.TextChannel):
        thread = await message.create_thread(
            name=prompt[:80], auto_archive_duration=60
        )
        async with thread.typing():
            reply, session_id = await call_claude(prompt)
        conversations[thread.id] = session_id
        await send_chunked(thread, reply)
    else:
        # DM など、スレッド非対応チャンネルは直接返信
        async with message.channel.typing():
            reply, session_id = await call_claude(prompt)
        conversations[message.channel.id] = session_id
        await send_chunked(message.channel, reply)


async def continue_thread(message: discord.Message) -> None:
    session_id = conversations.get(message.channel.id)

    async with message.channel.typing():
        reply, new_session_id = await call_claude(message.content, session_id)

    # コンテキスト圧縮などで session_id が変わる場合があるので更新
    if new_session_id:
        conversations[message.channel.id] = new_session_id

    await send_chunked(message.channel, reply)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if not is_allowed_id(message.author.id):
        return

    # 管理中のスレッド内 → 会話継続（メンション不要）
    if (
        isinstance(message.channel, discord.Thread)
        and message.channel.id in conversations
    ):
        await continue_thread(message)
        return

    # メンション → 新規スレッド開始
    if bot_is_mentioned(message):
        await start_thread(message)
        return

    await bot.process_commands(message)


@bot.command(name="run")
async def run_script(ctx: commands.Context, script_name: str, *args: str):
    """リポジトリのスクリプトを実行する。"""
    if not is_allowed(ctx):
        return
    if script_name not in SCRIPTS:
        await ctx.send(f"Unknown script `{script_name}`. Try `!scripts`.")
        return
    script_path = os.path.join(REPO_ROOT, SCRIPTS[script_name])
    await ctx.send(f"▶ `{script_name} {' '.join(args)}`")
    async with ctx.typing():
        output, code = await run_subprocess(
            ["bash", script_path, *args], cwd=REPO_ROOT
        )
    await ctx.send("✅" if code == 0 else f"❌ (exit {code})")
    await send_chunked(ctx, output)


@bot.command(name="scripts")
async def list_scripts(ctx: commands.Context):
    """利用可能なスクリプト一覧を表示する。"""
    if not is_allowed(ctx):
        return
    lines = [f"`{k}` → `{v}`" for k, v in SCRIPTS.items()]
    await ctx.send("**Available scripts:**\n" + "\n".join(lines))


@bot.command(name="weather")
async def get_weather(ctx: commands.Context, date: str | None = None):
    """東京の天気を表示する。  !weather [YYYY-MM-DD]"""
    if not is_allowed(ctx):
        return
    async with ctx.typing():
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, weather_mod.fetch, date)
    await send_chunked(ctx, result)


@bot.command(name="clear")
async def clear_conversation(ctx: commands.Context):
    """このスレッドの会話セッションをリセットする。"""
    if not is_allowed(ctx):
        return
    if ctx.channel.id in conversations:
        conversations.pop(ctx.channel.id)
        await ctx.send("会話をリセットしました。")
    else:
        await ctx.send("このスレッドに会話はありません。")


bot.run(DISCORD_TOKEN)
