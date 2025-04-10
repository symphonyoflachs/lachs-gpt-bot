import discord
from discord.ext import commands, tasks
from discord import app_commands
import wavelink
import os
import aiohttp
import requests
import asyncio
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from threading import Thread

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
TWITCH_USERNAME = os.getenv("TWITCH_USERNAME")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY")
LAVALINK_HOST = os.getenv("LAVALINK_HOST")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT"))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

tree = bot.tree

now_playing = {
    "title": "Kein Song aktiv",
    "artist": "–",
    "cover": "https://via.placeholder.com/300x300.png?text=Kein+Cover"
}

# === WEB ===
web = Flask(__name__)

@web.route("/")
def home():
    return "LachsGPT läuft."

@web.route("/api/nowplaying")
def api_nowplaying():
    return jsonify(now_playing)

@web.route("/music_control", methods=["POST"])
def api_music_control():
    action = request.json.get("action")
    print(f"Musiksteuerung: {action}")
    return jsonify({"status": "ok"})

def start_web():
    web.run(host="0.0.0.0", port=3000)

# === BOT EVENTS ===

@bot.event
async def on_ready():
    print(f"LachsGPT ist online als {bot.user}")

    await wavelink.Pool.connect(
        client=bot,
        nodes=[wavelink.Node(uri=f"http://{LAVALINK_HOST}:{LAVALINK_PORT}", password=LAVALINK_PASSWORD)],
        spotify_client_id=SPOTIFY_CLIENT_ID,
        spotify_client_secret=SPOTIFY_CLIENT_SECRET
    )

    try:
        synced = await tree.sync()
        print(f"Slash-Befehle synchronisiert: {len(synced)}")
    except Exception as e:
        print("Fehler beim Slash-Sync:", e)

    await setup_game_roles()
    check_stream.start()

@bot.event
async def on_wavelink_track_start(payload):
    track = payload.track
    now_playing["title"] = track.title
    now_playing["artist"] = track.author
    now_playing["cover"] = track.artwork or now_playing["cover"]

# === TWITCH CHECK ===

@tasks.loop(minutes=1)
async def check_stream():
    try:
        token = await get_twitch_token()
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.twitch.tv/helix/streams?user_login={TWITCH_USERNAME}", headers=headers) as resp:
                data = await resp.json()
                if data.get("data"):
                    print("Stream ist LIVE:", data["data"][0]["title"])
    except Exception as e:
        print("Twitch Fehler:", e)

async def get_twitch_token():
    async with aiohttp.ClientSession() as session:
        async with session.post("https://id.twitch.tv/oauth2/token", params={
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }) as resp:
            return (await resp.json()).get("access_token")

# === SLASH COMMANDS ===

@tree.command(name="lachs", description="Frag den LachsGPT etwas")
async def lachs(interaction: discord.Interaction, frage: str):
    await interaction.response.send_message("LachsGPT denkt nach... 🧠")

    prompt = f"[INST] <<SYS>>\nAntworte immer in der Sprache, in der der Benutzer spricht. Verwende keine andere Sprache.\n<</SYS>>\n{frage}[/INST]"

    # Dummy-Response (hier kommt dein HuggingFace-Call rein)
    antwort = f"Antwort auf: {frage} (hier HuggingFace einbauen)"
    await interaction.followup.send(antwort)

@tree.command(name="bild", description="Erzeuge ein KI-Bild mit DeepAI")
async def bild(interaction: discord.Interaction, prompt: str):
    await interaction.response.send_message("Ich male für dich...")
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.deepai.org/api/text2img",
            headers={"api-key": DEEPAI_API_KEY},
            data={"text": prompt}) as response:
            data = await response.json()
    await interaction.followup.send(data.get("output_url", "Kein Bild erzeugt."))

@tree.command(name="watch", description="Erstelle einen Watch2Gether-Raum")
async def watch(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with session.post("https://w2g.tv/rooms/create.json", json={
            "w2g_api_key": "default",
            "share": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }) as resp:
            data = await resp.json()
    if "streamkey" in data:
        link = f"https://w2g.tv/rooms/{data['streamkey']}"
        await interaction.response.send_message(f"Hier ist dein Watch2Gether Raum, Lachs:\n{link}")
    else:
        await interaction.response.send_message("Konnte keinen Raum erstellen.")

# === SPIELROLLEN ===

from discord.ui import View, Button

GAMEROLE_CHANNEL_ID = 123456789
