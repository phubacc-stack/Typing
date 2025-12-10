import os
import asyncio
import random
import discord
from discord.ext import commands
from flask import Flask
import threading

# ------------- ENV VARIABLES -------------
user_token = os.environ["user_token"]
spam_id = os.environ["spam_id"]

# ------------- DISCORD CLIENT -------------
prefix = "<>"
client = commands.Bot(command_prefix=prefix)

# Global state
spamming = False
spam_task = None
spam_lock = asyncio.Lock()

# Friend-style safe intervals
intervals = [2.8, 3.0, 3.2, 3.4, 3.6]

# ------------- ROLE CHECK -------------
def is_admin():
    async def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name="Admin")
        return bool(role)
    return commands.check(predicate)

# ------------- GLOBAL BLOCK: ONLY ADMIN CAN USE COMMANDS -------------
@client.check
async def global_admin_check(ctx):
    if ctx.command.name == "cmd":
        return True
    role = discord.utils.get(ctx.author.roles, name="Admin")
    return bool(role)

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

# ------------- SAFE SEND (friend style—simple, no retries) -------------
async def send_safe(channel, content):
    async with spam_lock:
        try:
            await channel.send(content)
        except Exception as e:
            print(f"⚠ Send error: {e}")
            await asyncio.sleep(5)

# ------------- SPAM LOOP (FRIEND STYLE) -------------
async def spam_loop():
    await client.wait_until_ready()

    channel = client.get_channel(int(spam_id))
    if channel is None:
        print(f"❌ Invalid spam channel ID: {spam_id}")
        return

    print("Friend-style spam loop started.")

    while True:
        if spamming:
            # Same style random number spam your friend uses
            msg = "".join(random.sample("0123456789", 7) * 5)

            await send_safe(channel, msg)

            # Friend-style random delay per message
            delay = random.choice(intervals)
            await asyncio.sleep(delay)

        else:
            await asyncio.sleep(1)

# ------------- READY EVENT -------------
@client.event
async def on_ready():
    global spam_task
    print("*" * 30)
    print(f"Logged in as {client.user}")
    print("*" * 30)

    if spam_task is None:
        spam_task = client.loop.create_task(spam_loop())

# ------------- COMMANDS -------------
@client.command()
@is_admin()
async def start(ctx):
    global spamming
    spamming = True
    await ctx.send("✅ Spammer started (friend-style).")

@client.command()
@is_admin()
async def stop(ctx):
    global spamming
    spamming = False
    await ctx.send("🛑 Spammer stopped.")

@client.command()
@is_admin()
async def say(ctx, *, msg):
    await ctx.send(msg)
    await ctx.message.delete()

@client.command()
@is_admin()
async def delete(ctx):
    await ctx.channel.delete()

@client.command()
async def cmd(ctx):
    await ctx.send(
        "**Commands (Admin only):**\n"
        "`<>say <msg>` — Make bot send a message\n"
        "`<>start` — Start spammer\n"
        "`<>stop` — Stop spammer\n"
        "`<>delete` — Delete channel\n"
    )

# ------------- START EVERYTHING -------------
keep_alive()
client.run(user_token)
