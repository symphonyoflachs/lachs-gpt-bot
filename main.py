# -*- coding: utf-8 -*-
from dotenv import load_dotenv
load_dotenv()
import discord
import openai
import os
from flask import Flask
from threading import Thread

# Lade API-Schlüssel aus Umgebungsvariablen
openai.api_key = os.getenv("OPENAI_API_KEY")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Setze Intents
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# Webserver für Render „always on“
app = Flask('')

@app.route('/')
def home():
    return "LachsGPT is swimming 🐟"

def run():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot ist bereit
@client.event
async def on_ready():
    print(f"LachsGPT ist online! Eingeloggt als {client.user}")

# Bot empfängt Nachrichten
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

# Starte alles
keep_alive()
client.run(TOKEN)
