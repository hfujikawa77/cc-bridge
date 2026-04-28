import discord
import subprocess
import asyncio
import os
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
REPO_ROOT = os.path.expanduser(os.environ.get("REPO_ROOT", "~/GitHub/claw-io-hub"))
ALLOWED_USER_IDS = set(
    int(x) for x in os.environ.get("ALLOWED_USER_IDS", "").split(",") if x.strip()
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

SCRIPTS = {
    "tweets":   "scripts/collect-tweets/run.sh",
    "briefing": "scripts/generate/briefing.sh",
    "journal":  "scripts/generate/daily_journal.sh",
    "weather":  "scripts/weather/post_tokyo_weather.sh",
}


def is_allowed_id(user_id: int) -> bool:
    return not ALLOWED_USER_IDS or user_id in ALLOWED_USER_IDS


def is_allowed(ctx: commands.Context) -> bool:
    return is_allowed_id(ctx.author.id)


async def send_chunked(ctx: commands.Context, text: str, code_block: bool = True) -> None:
    if not text:
        text = "(no output)"
    wrap = ("```\n", "\n```") if code_block else ("", "")
    limit = 2000 - len(wrap[0]) - len(wrap[1])
    for i in range(0, len(text), limit):
        await ctx.send(wrap[0] + text[i : i + limit] + wrap[1])


async def run_subprocess(args: list[str], cwd: str, timeout: int = 300) -> tuple[str, int]:
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


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if not is_allowed_id(message.author.id):
        return
    # メンションされたときだけ応答
    if bot.user not in message.mentions:
        await bot.process_commands(message)
        return

    prompt = message.clean_content.replace(f"@{bot.user.display_name}", "").strip()
    if not prompt:
        await message.reply("何か質問してください。")
        return

    async with message.channel.typing():
        output, _ = await run_subprocess(
            ["claude", "--dangerously-skip-permissions", "-p", prompt],
            cwd=REPO_ROOT,
            timeout=120,
        )
    # reply で会話の流れを保つ
    limit = 1990
    chunks = [output[i : i + limit] for i in range(0, len(output), limit)]
    first = True
    for chunk in chunks:
        if first:
            await message.reply(f"```\n{chunk}\n```")
            first = False
        else:
            await message.channel.send(f"```\n{chunk}\n```")

    await bot.process_commands(message)


@bot.command(name="ask")
async def ask_claude(ctx: commands.Context, *, prompt: str):
    """Claude に質問する。リポジトリのコンテキストで動作。"""
    if not is_allowed(ctx):
        return
    async with ctx.typing():
        output, code = await run_subprocess(
            ["claude", "--dangerously-skip-permissions", "-p", prompt],
            cwd=REPO_ROOT,
            timeout=120,
        )
    await send_chunked(ctx, output)


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
            ["bash", script_path, *args],
            cwd=REPO_ROOT,
        )
    status = "✅" if code == 0 else f"❌ (exit {code})"
    await ctx.send(status)
    await send_chunked(ctx, output)


@bot.command(name="scripts")
async def list_scripts(ctx: commands.Context):
    """利用可能なスクリプト一覧を表示する。"""
    if not is_allowed(ctx):
        return
    lines = [f"`{k}` → `{v}`" for k, v in SCRIPTS.items()]
    await ctx.send("**Available scripts:**\n" + "\n".join(lines))


@bot.command(name="status")
async def git_status(ctx: commands.Context):
    """git status を表示する。"""
    if not is_allowed(ctx):
        return
    async with ctx.typing():
        output, _ = await run_subprocess(["git", "status", "--short"], cwd=REPO_ROOT)
    await send_chunked(ctx, output or "(clean)")


bot.run(DISCORD_TOKEN)
