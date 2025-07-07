import json
import os
import discord
from discord.ext import commands
from datetime import datetime
import asyncio  

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

    winners.append(new_entry)
    if len(winners) > 10:
        winners = winners[-10:]

    save_recent_winners(winners)


def is_leaderboard_full():
    return len(get_recent_winners()) >= 10


async def winners_role(channel, bot, check):
    winners = get_recent_winners()
    if not is_leaderboard_full():
        await channel.send("❌ The leaderboard is not yet full.")
        return None

    await channel.send("Please enter the name of the role you want to assign to the winners:")

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        await channel.send("⏱️ Timed out waiting for role name. No role will be given.")
        return None

    role_name = msg.content.strip()
    if not role_name:
        await channel.send("⚠️ No role name entered. Skipping role creation.")
        return None

    guild = channel.guild
    try:
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role:
            await channel.send(f"ℹ️ Role `{role_name}` already exists. It will be used.")
            return existing_role.name

        new_role = await guild.create_role(name=role_name)
        await channel.send(f"✅ Role `{new_role.name}` created successfully!")
        return new_role.name
    except discord.Forbidden:
        await channel.send("🚫 I don't have permission to create roles.")
    except Exception as e:
        await channel.send(f"⚠️ Failed to create role: {e}")

    return None


async def giverole(channel, role_name: str):
    role = discord.utils.get(channel.guild.roles, name=role_name)
    if not role:
        await channel.send(f"⚠️ Role `{role_name}` not found.")
        return

    winners = get_recent_winners()
    assigned = []

    for entry in winners:
        user_id = int(entry["user_id"])
        member = channel.guild.get_member(user_id)
        if member is None:
            try:
                member = await channel.guild.fetch_member(user_id)
            except discord.NotFound:
                await channel.send(f"⚠️ User with ID {user_id} not found in this server.")
                continue
            except Exception as e:
                await channel.send(f"⚠️ Failed to fetch user {user_id}: {e}")
                continue

        try:
            await member.add_roles(role, reason="Leaderboard winner")
            assigned.append(member.mention)
        except discord.Forbidden:
            await channel.send(f"🚫 Missing permissions to add role to {member.mention}.")
        except Exception as e:
            await channel.send(f"⚠️ Error adding role to {member.mention}: {e}")

    if assigned:
        await channel.send(f"✅ Role `{role.name}` added to: {', '.join(assigned)}.")
    else:
        await channel.send("⚠️ No valid winners found to assign the role.")


def reset_leaderboard():
    save_recent_winners([])


def set_last_leaderboard(channel_id, message_id):
    LAST_LEADERBOARD_MESSAGES[str(channel_id)] = message_id


def get_last_leaderboard(channel_id):
    return LAST_LEADERBOARD_MESSAGES.get(str(channel_id))
