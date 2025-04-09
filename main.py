# -*- coding: utf-8 -*-
from dotenv import load_dotenv
load_dotenv()
import discord
import os
import aiohttp
import asyncio
import requests
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from flask import Flask
from threading import Thread

# 🔐 Instanz-Checker
LOCKFILE = ".lachslock"

if os.path.exists(LOCKFILE):
    print("❌ LachsGPT ist bereits aktiv – Beende mich!")
    sys.exit(0)
else:
    with open(LOCKFILE, "w") as f:
        f.write("running")

import atexit

def remove_lock():
    if os.path.exists(LOCKFILE):
        os.remove(LOCKFILE)

atexit.register(remove_lock)

# ⛓️ .env Variablen
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_USERNAME = os.getenv("TWITCH_USERNAME")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY")

# 🌊 Discord Bot
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# 🧠 Anti-Doppel-Schutz
processing_messages = set()

# 🌐 Flask für Render
app = Flask('')

@app.route('/')
def home():
    return "LachsGPT is swimming 🐟"

def run():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 🔍 Integration von XLM-Roberta
model_name = "xlm-roberta-large"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

# ✅ Bot bereit
@client.event
async def on_ready():
    print(f"LachsGPT ist online! Eingeloggt als {client.user}")

# 💬 Bild generieren mit DeepAI
def generate_image(prompt):
    url = "https://api.deepai.org/api/text2img"
    headers = {"api-key": DEEPAI_API_KEY}
    data = {"text": prompt}
    response = requests.post(url, headers=headers, data=data)
    result = response.json()
    image_url = result.get("output_url")

    if image_url:
        # Lade das Bild herunter
        image_data = requests.get(image_url).content
        return image_data
    else:
        return None

# 💬 HuggingFace und Bildgenerierung
@client.event
async def on_message(message):
    if message.author == client.user or message.author.bot:
        return

    if message.id in processing_messages:
        return
    processing_messages.add(message.id)

    try:
        content = message.content.strip()
        if content.lower().startswith("!lachs"):
            prompt = content[6:].strip()

            if prompt.startswith("bild"):
                image_prompt = prompt[4:].strip()
                image_data = generate_image(image_prompt)

                if image_data:
                    # Speichere das Bild temporär, um es hochzuladen
                    temp_filename = "temp_image.png"
                    with open(temp_filename, "wb") as temp_file:
                        temp_file.write(image_data)

                    # Lade die Datei hoch
                    await message.channel.send(file=discord.File(temp_filename))
                else:
                    await message.channel.send("Ups, konnte kein Bild erstellen!")
            else:
                # Fallback für andere Eingaben
                await message.channel.send("Gib mir was zum Brutzeln, Lachs!")
    finally:
        await asyncio.sleep(1)
        processing_messages.discard(message.id)

# 🧠 Hintergrund-Tasks starten
@client.event
async def setup_hook():
    client.loop.create_task(check_stream())

# 🚀 Start
keep_alive()
client.run(TOKEN)
