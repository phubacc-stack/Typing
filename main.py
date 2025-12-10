import os
import asyncio
import random
import discord
from discord.ext import commands
from flask import Flask
import threading
import time

# ------------- ENV VARIABLES -------------
user_token = os.environ["user_token"]
spam_id = os.environ["spam_id"]

# ------------- DISCORD CLIENT -------------
prefix = "<>"
client = commands.Bot(command_prefix=prefix)

# ------------- ROLE CHECK -------------
def is_admin():
    async def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name="Admin")
        return bool(role)
    return commands.check(predicate)

# ------------- GLOBAL BLOCK: ONLY ADMIN CAN USE COMMANDS -------------
@client.check
async def global_admin_check(ctx):
    # Allow "<>cmd" for everyone
    if ctx.command.name == "cmd":
        return True

    role = discord.utils.get(ctx.author.roles, name="Admin")
    if role:
        return True

    await ctx.send("❌ You must have the **Admin** role to use bot commands.")
    return False

# ------------- FLASK KEEP-ALIVE SERVER -------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.start()

# ------------- RETRY SAFE SEND -------------
async def send_with_retry(channel, content, attempt=1):
    if attempt > 3:
        print("❌ Max retries reached. Skipping message.")
        return

    try:
        await channel.send(content)

    except discord.errors.HTTPException as e:
        if e.status == 429:
            retry_after = getattr(e, "retry_after", 5)
            print(f"⚠️ Ratelimited. Retrying in {retry_after} seconds...")
            await asyncio.sleep(retry_after)
            await send_with_retry(channel, content, attempt + 1)
        else:
            print("⚠️ HTTP Error. Waiting 10s & retrying...")
            await asyncio.sleep(10)
            await send_with_retry(channel, content, attempt + 1)

    except Exception as e:
        print(f"⚠️ General Error: {e}. Retrying in 10s...")
        await asyncio.sleep(10)
        await send_with_retry(channel, content, attempt + 1)

# ------------- SAFE SPAM LOOP (NO RATE LIMITS) -------------
spamming = False

async def spam_loop():
    await client.wait_until_ready()
    channel = client.get_channel(int(spam_id))

    if channel is None:
        print(f"❌ Invalid spam channel ID: {spam_id}")
        return

    while True:
        if not spamming:
            await asyncio.sleep(1)
            continue

        msg = "".join(random.choices("0123456789", k=30))

        await send_with_retry(channel, msg)

        delay = random.uniform(5.5, 8.5)  # safest range
        await asyncio.sleep(delay)

# ------------- BOT READY -------------
@client.event
async def on_ready():
    print("*" * 30)
    print(f"Logged in as {client.user}")
    print("*" * 30)
    client.loop.create_task(spam_loop())

# ------------- COMMANDS -------------

@client.command()
@is_admin()
async def say(ctx, *, msg):
    await ctx.send(msg)
    await ctx.message.delete()

@client.command()
@is_admin()
async def start(ctx):
    global spamming
    spamming = True
    await ctx.send("✅ Spammer Started!")

@client.command()
@is_admin()
async def stop(ctx):
    global spamming
    spamming = False
    await ctx.send("🛑 Spammer Stopped!")

@client.command()
@is_admin()
async def delete(ctx):
    await ctx.channel.delete()

@client.command()
async def cmd(ctx):
    await ctx.send(
        "**Commands (Admin only):**\n"
        "`<>say <msg>` — Make bot send message\n"
        "`<>start` — Start spammer\n"
        "`<>stop` — Stop spammer\n"
        "`<>delete` — Delete channel\n"
    )

# ------------- ERROR HANDLER -------------
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown command. Use `<>cmd`.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission.")
    else:
        await ctx.send(f"⚠️ Error: {error}")

# ------------- START EVERYTHING -------------
keep_alive()
client.run(user_token)
