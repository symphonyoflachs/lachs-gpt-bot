# -*- coding: utf-8 -*-
from dotenv import load_dotenv
load_dotenv()
import discord
import os
import aiohttp
import asyncio
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

# 💬 HuggingFace Antwort mit XLM-Roberta
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

            if len(prompt) < 3:
                await message.channel.send("Gib mir was zum Brutzeln, Lachs!")
                return

            await message.channel.send("LachsGPT denkt nach... 🧠")

            # Verwenden von XLM-Roberta zur Verarbeitung
            inputs = tokenizer(prompt, return_tensors="pt")
            outputs = model(**inputs)

            # Hier könntest du die logits auswerten und entsprechend antworten
            reply = "Ich bin mir noch nicht sicher, was ich dazu sagen soll..."  # Hier kannst du basierend auf der Modellantwort anpassen
            await message.channel.send(reply)

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
