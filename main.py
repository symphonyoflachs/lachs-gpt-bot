# -*- coding: utf-8 -*-
from dotenv import load_dotenv
load_dotenv()
import discord
import openai
import os
import aiohttp
import asyncio
from flask import Flask
from threading import Thread

# ⛓️ Keys und IDs aus .env
openai.api_key = os.getenv("OPENAI_API_KEY")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_USERNAME = os.getenv("TWITCH_USERNAME")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# 🌊 Intents & Client
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# 🌐 Flask Webserver für Render (damit online bleibt)
app = Flask('')

@app.route('/')
def home():
    return "LachsGPT is swimming 🐟"

def run():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 🎮 Twitch-Live-Check
is_live = False

async def check_stream():
    await client.wait_until_ready()
    global is_live

    async with aiohttp.ClientSession() as session:
        # Token holen
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

            await asyncio.sleep(60)  # jede Minute checken

# 🤖 Bot bereit
@client.event
async def on_ready():
    print(f"LachsGPT ist online! Eingeloggt als {client.user}")

# 💬 Chatfunktion
@client.event
async def on_message(message):
    print(f"Nachricht erhalten: {message.content}")

    if message.author.bot:
        return

    if message.content.startswith("!lachs"):
        prompt = message.content.replace("!lachs", "").strip()
        if not prompt:
            await message.channel.send("Gib mir was zum Brutzeln, Lachs!")
            return

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            reply = response["choices"][0]["message"]["content"]
            await message.channel.send(reply)
        except Exception as e:
            await message.channel.send(f"Upsi, Lachs hatte ein Problem: {e}")

# 🚀 Start
keep_alive()
@client.event
async def setup_hook():
    client.loop.create_task(check_stream())

client.run(TOKEN)
