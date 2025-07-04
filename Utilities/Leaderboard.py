import json
import os
from datetime import datetime

LAST_LEADERBOARD_MESSAGES = {}

LEADERBOARD_CHANNEL_ID = 1379347453462970519

LEADERBOARD_FILE = os.path.join("Data", "leaderboard.json")
os.makedirs("Data", exist_ok=True)

def get_recent_winners():
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    with open(LEADERBOARD_FILE, "r") as f:
        return json.load(f)

def save_recent_winners(winners):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(winners, f, indent=4)

def add_recent_winner(user_id, username, game_name, host_id, host_name):
    winners = get_recent_winners()

    # Prevent duplicates
    if any(str(w["user_id"]) == str(user_id) for w in winners):
        return

    new_entry = {
        "user_id": str(user_id),
        "username": username,
        "game_name": game_name,
        "host_id": str(host_id),
        "host_name": host_name,
        "timestamp": datetime.now().strftime("%b %d, %Y %I:%M %p")
    }

    # Append to maintain order, then trim oldest 10
    winners.append(new_entry)
    if len(winners) > 10:
        winners = winners[-10:]

    save_recent_winners(winners)

def reset_leaderboard():
    save_recent_winners([])

def is_leaderboard_full():
    return len(get_recent_winners()) >= 10

def set_last_leaderboard(channel_id, message_id):
    LAST_LEADERBOARD_MESSAGES[str(channel_id)] = message_id

def get_last_leaderboard(channel_id):
    return LAST_LEADERBOARD_MESSAGES.get(str(channel_id))
