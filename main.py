import discord
from discord.ext import commands
from flask import Flask, request
import threading
import json
import os
from datetime import datetime
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
# TOKEN via Railway
TOKEN = os.getenv("TOKEN")

# ---------------- CONFIG ----------------

POINTS = {
    "comment": 5,
    "like": 1,
    "follow": 50,
    "gift": 100
}

DATA_FILE = "data.json"

# ---------------- DISCORD ----------------

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- FLASK ----------------

app = Flask(__name__)

# ---------------- DATA ----------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "links": {}, "last_reset": str(datetime.now().month)}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------- RESET ----------------

def check_reset():
    data = load_data()
    current_month = str(datetime.now().month)

    if data["last_reset"] != current_month:
        data["users"] = {}
        data["last_reset"] = current_month
        save_data(data)

# ---------------- POINTS ----------------

def add_points(username, amount):
    check_reset()
    data = load_data()

    username = username.lower()

    data["users"][username] = data["users"].get(username, 0) + amount
    save_data(data)

    return data["users"][username]

# ---------------- ROLES ----------------

async def update_roles(guild, discord_id, points):
    member = guild.get_member(int(discord_id))
    if not member:
        return

    roles = {
        "👀 Viewer": 100,
        "💬 Actif": 500,
        "🔥 Fan": 2000,
        "👑 VIP": 10000
    }

    for role_name, req in roles.items():
        role = discord.utils.get(guild.roles, name=role_name)
        if role and points >= req and role not in member.roles:
            await member.add_roles(role)

# ---------------- WEBHOOK ----------------

@app.route('/tiktok', methods=['POST'])
def tiktok():
    data = request.json

    username = data.get("username", "").lower()
    event = data.get("event", "comment")

    pts = POINTS.get(event, 1)
    total = add_points(username, pts)

    db = load_data()
    discord_id = db["links"].get(username)

    if discord_id:
        for guild in bot.guilds:
            bot.loop.create_task(update_roles(guild, discord_id, total))

    return {"status": "ok"}

# ---------------- COMMANDES ----------------

@bot.command()
async def link(ctx, tiktok_name):
    data = load_data()
    data["links"][tiktok_name.lower()] = str(ctx.author.id)
    save_data(data)

    await ctx.send(f"✅ {ctx.author.name} lié à {tiktok_name}")

@bot.command()
async def points(ctx):
    data = load_data()
    user = str(ctx.author.id)

    for tiktok, discord_id in data["links"].items():
        if discord_id == user:
            pts = data["users"].get(tiktok, 0)
            await ctx.send(f"🔥 {ctx.author.name} : {pts} points")
            return

    await ctx.send("❌ Compte non lié")

@bot.command()
async def top(ctx):
    data = load_data()
    users = data["users"]

    top10 = sorted(users.items(), key=lambda x: x[1], reverse=True)[:10]

    msg = "🏆 TOP 10\n"
    for i, (user, pts) in enumerate(top10, 1):
        msg += f"{i}. {user} - {pts}\n"

    await ctx.send(msg)

# ---------------- RUN ----------------

def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask).start()

bot.run(TOKEN)
