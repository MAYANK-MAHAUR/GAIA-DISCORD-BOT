import json
import os
import discord
from datetime import datetime

FILE_PATH = "Data/Sec_Leaderboard.json"

# === Load & Save ===
def load_leaderboard():
    if not os.path.exists(FILE_PATH):
        return {}
    with open(FILE_PATH, "r") as f:
        return json.load(f)

def save_leaderboard(data):
    with open(FILE_PATH, "w") as f:
        json.dump(data, f, indent=4)

# === Win Handling ===
def add_second_win(user_id: int, username: str):
    data = load_leaderboard()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {"username": username, "wins": 0, "timestamps": []}

    data[uid]["username"] = username  # update name if changed
    data[uid]["wins"] += 1
    data[uid]["timestamps"].append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    save_leaderboard(data)

def get_top_second(limit=10):
    data = load_leaderboard()
    sorted_users = sorted(data.items(), key=lambda item: item[1]["wins"], reverse=True)
    return sorted_users[:limit]

def reset_second_leaderboard():
    save_leaderboard({})

# === UI / Display ===
def build_scramble_leaderboard_embed():
    leaderboard = get_top_second()
    if not leaderboard:
        return discord.Embed(
            title="🥇 Scramble Leaderboard",
            description="No winners yet. Be the first one!",
            color=discord.Color.orange()
        )

    embed = discord.Embed(
        title="🥇 Scramble Leaderboard",
        description="Top players:",
        color=discord.Color.orange()
    )

    for i, (uid, info) in enumerate(leaderboard, 1):
        name = info["username"]
        wins = info["wins"]
        last_time = info["timestamps"][-1] if info.get("timestamps") else "N/A"
        embed.add_field(
            name=f"#{i} - {name}",
            value=f"🏆 Wins: {wins}\n🕒 Last win: {last_time}",
            inline=False
        )

    embed.set_footer(text="Leaderboard tracks all-time wins.")
    return embed
