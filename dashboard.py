from flask import Flask, render_template, request, redirect, session
import os
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("DASHBOARD_SECRET")
dashboard_pass = os.getenv("DASHBOARD_PASS")

@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("dashboard.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == dashboard_pass:
            session["logged_in"] = True
            return redirect("/")
        else:
            return render_template("login.html", error="Falsches Passwort!")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/musik")
def musik():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("musik.html")

@app.route("/twitch")
def twitch():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("twitch.html", stream_status="Noch nicht verbunden")

@app.route("/admin")
def admin():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("admin.html")

@app.route("/watch")
def watch():
    if not session.get("logged_in"):
        return redirect("/login")

    response = requests.post("https://w2g.tv/rooms/create.json", json={
        "w2g_api_key": "default",
        "share": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    })

    if response.status_code == 200:
        data = response.json()
        if "streamkey" in data:
            link = f"https://w2g.tv/rooms/{data['streamkey']}"
            return render_template("watch.html", watch_url=link)
    return render_template("watch.html", error="Fehler beim Erstellen des Raums.")
