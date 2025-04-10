import discord
from discord.ext import tasks
from discord import Bot
import wavelink
import os
import aiohttp
import requests
import asyncio
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from threading import Thread
from discord.ui import View, Button

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
bot = Bot(intents=intents)

now_playing = {
    "title": "Kein Song aktiv",
    "artist": "–",
    "cover": "https://via.placeholder.com/300x300.png?text=Kein+Cover"
}

# === WEB API ===
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

# === DISCORD EVENTS ===
@bot.event
async def on_ready():
    print(f"LachsGPT ist online als {bot.user}")
    
    await wavelink.NodePool.create_node(
        bot=bot,
        host=LAVALINK_HOST,
        port=LAVALINK_PORT,
        password=LAVALINK_PASSWORD,
        spotify_client_id=SPOTIFY_CLIENT_ID,
        spotify_client_secret=SPOTIFY_CLIENT_SECRET,
        region="eu"
    )

    check_stream.start()
    await setup_game_roles()

@bot.event
async def on_wavelink_track_start(player: wavelink.Player, track):
    now_playing["title"] = track.title
    now_playing["artist"] = track.author
    now_playing["cover"] = getattr(track, "thumb", now_playing["cover"])

# === TWITCH LIVE CHECK ===
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
@bot.slash_command(name="lachs", description="Frag den LachsGPT etwas")
async def lachs(ctx, frage: str = None):
    if frage is None:
        await ctx.respond("Gib mir was zum Brutzeln, Lachs!")
        return

    await ctx.respond("LachsGPT denkt nach... 🧠")

    prompt = f"[INST] <<SYS>>\nAntworte immer in der Sprache, in der der Benutzer spricht. Verwende keine andere Sprache.\n<</SYS>>\n{frage}[/INST]"
    await ctx.send(f"Frage: {frage}\n\nAntwort: LachsGPT antwortet bald...")

@bot.slash_command(name="bild", description="Erzeuge ein KI-Bild mit DeepAI")
async def bild(ctx, prompt: str):
    await ctx.respond("Ich male für dich... 🎨")
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.deepai.org/api/text2img",
            headers={"api-key": DEEPAI_API_KEY},
            data={"text": prompt}) as response:
            data = await response.json()
    await ctx.send(data.get("output_url", "Kein Bild erzeugt."))

@bot.slash_command(name="watch", description="Erstelle einen Watch2Gether-Raum")
async def watch(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.post("https://w2g.tv/rooms/create.json", json={
            "w2g_api_key": "default",
            "share": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }) as resp:
            data = await resp.json()
    if "streamkey" in data:
        link = f"https://w2g.tv/rooms/{data['streamkey']}"
        await ctx.respond(f"Hier ist dein Watch2Gether Raum, Lachs:\n{link}")
    else:
        await ctx.respond("Konnte keinen Raum erstellen.")

# === SPIELROLLEN-SYSTEM ===
GAMEROLE_CHANNEL_ID = 123456789012345678  # ⬅️ ERSETZEN mit deiner echten Channel-ID

GAMEROLES = {
    "🎮 League of Legends": "League of Legends",
    "💣 Valorant": "Valorant",
    "🐍 Apex Legends": "Apex Legends",
    "🎤 Fortnite": "Fortnite"
}

class RoleView(View):
    def __init__(self):
        super().__init__(timeout=None)
        for emoji_label, role_name in GAMEROLES.items():
            self.add_item(RoleButton(emoji_label, role_name))

class RoleButton(Button):
    def __init__(self, label, role_name):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.role_name = role_name

    async def callback(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name=self.role_name)
        if not role:
            await interaction.response.send_message("Rolle nicht gefunden.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"Rolle **{role.name}** entfernt 🧼", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Rolle **{role.name}** zugewiesen 🧂", ephemeral=True)

async def setup_game_roles():
    await bot.wait_until_ready()
    channel = bot.get_channel(GAMEROLE_CHANNEL_ID)
    if channel:
        messages = [m async for m in channel.history(limit=10) if m.author == bot.user]
        if not any("🎮 **Wähle deine Spiele-Rollen:**" in m.content for m in messages):
            await channel.send("🎮 **Wähle deine Spiele-Rollen:**", view=RoleView())

# === START ===
Thread(target=start_web).start()
bot.run(TOKEN)
