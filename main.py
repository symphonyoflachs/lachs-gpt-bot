from dotenv import load_dotenv
@client.event
async def on_message(message):
    print(f"Nachricht erhalten: {message.content}")  # 👈 DAS ist die Debug-Zeile!

    if message.author == client.user:
        return

    if message.content.startswith("!lachs"):
        await message.channel.send("Ich bin ein lachsiger Lachs! 🐟")
load_dotenv()
import discord
import openai
import os
from flask import Flask
from threading import Thread

openai.api_key = os.getenv("OPENAI_API_KEY")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

app = Flask('')

@app.route('/')
def home():
    return "LachsGPT is swimming 🐟"

def run():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    t = Thread(target=run)
    t.start()

@client.event
async def on_ready():
    print(f"LachsGPT ist online! Eingeloggt als {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!lachs"):
        prompt = message.content.replace("!lachs", "").strip()
        if not prompt:
            await message.channel.send("Gib mir was zum Brutzeln, Lachs!")
            return

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response["choices"][0]["message"]["content"]
        await message.channel.send(reply)

keep_alive()
client.run(TOKEN)


