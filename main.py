# -*- coding: utf-8 -*-
from dotenv import load_dotenv
load_dotenv()
import discord
import os
import aiohttp
import asyncio
from flask import Flask
from threading import Thread

# ⛓️ .env Variablen
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_USERNAME = os.getenv("TWITCH_USERNAME")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# 🌊 Discord Bot & Intents
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# 🧠 Merkt sich verarbeitete Nachrichten (Anti-Doppel)
recent_messages = set()

# 🌐 Flask Webserver für Render „Keep Alive“
app = Flask('')

@app.route('/')
def home():
    return "LachsGPT is swimming 🐟"

def run():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 🎮 Twitch-Live-Checker
is_live = False

async def check_stream():
    await client.wait_until_ready()
    global is_live

    async with aiohttp.ClientSession() as session:
        auth_url = "https://id.twitch.tv/oauth2/token"
        auth_params = {
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }

        async with session.post(auth_url, params=auth_params) as auth_resp:
            auth_data = await auth_resp.json()
            access_token = auth_data["access_token"]

        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {access_token}"
        }

        while not client.is_closed():
            url = f"https://api.twitch.tv/helix/streams?user_login={TWITCH_USERNAME}"
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                streams = data.get("data", [])

                if streams:
                    stream = streams[0]
                    title = stream["title"]
                    if not is_live:
                        is_live = True
                        msg = f"🎥 **{TWITCH_USERNAME} ist jetzt live!**\n**{title}**\n👉 https://twitch.tv/{TWITCH_USERNAME}"
                        channel = client.get_channel(DISCORD_CHANNEL_ID)
                        if channel:
                            await channel.send(msg)
                else:
                    is_live = False

            await asyncio.sleep(60)

# ✅ Bot ist bereit
@client.event
async def on_ready():
    print(f"LachsGPT ist online! Eingeloggt als {client.user}")

# 💬 GPT via Hugging Face mit Sprachlogik + Anti-Doppel
@client.event
async def on_message(message):
    if message.author == client.user or message.author.bot:
        return

    # 🛡️ Doppelcheck
    if message.id in recent_messages:
        return
    recent_messages.add(message.id)

    # Nach 60 Sek. vergessen
    async def forget_message(mid):
        await asyncio.sleep(60)
        recent_messages.discard(mid)

    client.loop.create_task(forget_message(message.id))

    # Lachs-Prompt checken
    content = message.content.strip()
    if content.lower().startswith("!lachs"):
        prompt = content[6:].strip()

        if len(prompt) < 3:
            await message.channel.send("Gib mir was zum Brutzeln, Lachs!")
            return

        await message.channel.send("LachsGPT denkt nach... 🧠")

        system_instruction = (
            "Antworte immer in der Sprache, in der der Benutzer spricht. "
            "Wenn die Frage auf Deutsch ist, antworte auf Deutsch. "
            "Wenn sie auf Englisch ist, dann auf Englisch. "
            "Verwende keine andere Sprache."
        )

        payload = {
            "inputs": f"[INST] <<SYS>>\n{system_instruction}\n<</SYS>>\n{prompt} [/INST]",
            "parameters": {"max_new_tokens": 200},
        }

        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1",
                headers=headers,
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    full = data[0].get("generated_text", "")
                    reply = full.replace(prompt, "").strip() if full else "LachsGPT war sprachlos... 🐟"
                    await message.channel.send(reply)
                else:
                    await message.channel.send(f"LachsGPT hat sich verschluckt... ({resp.status})")

# 🧠 Hintergrund-Tasks starten
@client.event
async def setup_hook():
    client.loop.create_task(check_stream())

# 🚀 Let’s gooo
keep_alive()
client.run(TOKEN)

