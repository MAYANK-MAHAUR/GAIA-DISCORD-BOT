import discord
import asyncio
import json
import random
from discord.ext import commands
from discord import app_commands
from Utilities.Leaderboard import (
    add_recent_winner, is_leaderboard_full, reset_leaderboard,
    get_recent_winners, winners_role, giverole
)

ALLOWED_ROLES = ["Game Master", "Moderator"]
LEADERBOARD_CHANNEL_ID = 1379347453462970519
PRIVATE_CHANNEL_ID = 1391437573683019866
CATEGORY_FILES = {
    "india": "Data/lyrics_India.json",
    "pakistan": "Data/lyrics_Pakistan.json",
    "nigeria": "Data/lyrics_Nigeria.json",
    "global": "Data/lyrics_global.json"
}

def normalize(text):
    return ''.join(filter(str.isalnum, text.lower()))

class Lyrics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_lyrics = {}
        self.stopped_channels = set()

    @app_commands.command(name="lyrics", description="Start a looping lyrics game (guess the song from lyric)")
    @app_commands.describe(category="Pick a lyric category")
    @app_commands.choices(category=[
        app_commands.Choice(name="India", value="india"),
        app_commands.Choice(name="Pakistan", value="pakistan"),
        app_commands.Choice(name="Nigeria", value="nigeria"),
        app_commands.Choice(name="Global", value="global")
    ])
    async def lyrics(self, interaction: discord.Interaction, category: app_commands.Choice[str]):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

        if interaction.channel.id in self.active_lyrics:
            return await interaction.response.send_message("❗ Lyrics game is already running in this channel.", ephemeral=True)

        self.active_lyrics[interaction.channel.id] = True
        self.stopped_channels.discard(interaction.channel.id)

        await interaction.response.send_message(f"🎵 Starting Lyrics game in category: **{category.name}**")
        await self.run_lyrics_game(interaction.channel, interaction.user, CATEGORY_FILES[category.value])

    async def run_lyrics_game(self, channel, host, file_path):
        try:
            with open(file_path, "r") as f:
                lyrics_data = json.load(f)
        except Exception as e:
            await channel.send("⚠️ Failed to load lyrics. Please check the file format or try again later.")
            self.active_lyrics.pop(channel.id, None)
            return

        used_lines = set()

        while not is_leaderboard_full() and channel.id not in self.stopped_channels:
            if len(used_lines) == len(lyrics_data):
                await channel.send("🎉 All lyric lines have been used!")
                break

            line_obj = random.choice(lyrics_data)
            while line_obj["line"] in used_lines:
                line_obj = random.choice(lyrics_data)
            used_lines.add(line_obj["line"])

            answer = line_obj["answer"].lower()
            lyric_line = line_obj["line"]

            embed = discord.Embed(
                title="🎶 Guess the Song!",
                description=f"*{lyric_line}*\n\n⏱️ You have 30 seconds to guess the song name!",
                color=discord.Color.purple()
            )
            await channel.send(embed=embed)

            def check(m):
                return m.channel == channel and not m.author.bot and normalize(m.content) == normalize(answer)

            try:
                msg = await self.bot.wait_for("message", timeout=30.0, check=check)

                if str(msg.author.id) in [entry["user_id"] for entry in get_recent_winners()]:
                    continue

                await msg.add_reaction("🎉")
                await channel.send(embed=discord.Embed(
                    title="✅ Correct!",
                    description=f"{msg.author.mention} guessed it! The song was **{answer.title()}**.",
                    color=discord.Color.green()
                ))

                add_recent_winner(
                    user_id=str(msg.author.id),
                    username=msg.author.name,
                    game_name="Lyrics",
                    host_id=host.id,
                    host_name=host.name
                )

                await channel.send(embed=discord.Embed(
                    title="🌟 Added to Leaderboard!",
                    description=f"{msg.author.mention} is now on the leaderboard!",
                    color=discord.Color.blue()
                ))

                await self.send_leaderboard(channel)

                if is_leaderboard_full():
                    await self.end_game(channel, host)
                    return

                await asyncio.sleep(2)

            except asyncio.TimeoutError:
                if channel.id not in self.stopped_channels:
                    await channel.send(embed=discord.Embed(
                        title="⌛ Time's Up!",
                        description=f"Nobody guessed it. The answer was **{answer.title()}**.",
                        color=discord.Color.red()
                    ))

        if channel.id not in self.stopped_channels:
            await self.end_game(channel, host)

    async def send_leaderboard(self, channel):
        leaderboard = get_recent_winners()
        if not leaderboard:
            return

        embed = discord.Embed(title="🏆 Current Leaderboard", color=discord.Color.gold())
        for idx, entry in enumerate(leaderboard, start=1):
            embed.add_field(
                name=f"{idx}. {entry['username']} ({entry['game_name']})",
                value=f"🏅 Hosted by: {entry['host_name']} • {entry['timestamp']}",
                inline=False
            )
        await channel.send(embed=embed)

    async def end_game(self, channel, host):
        await channel.send(embed=discord.Embed(
            title="📋 Leaderboard Full!",
            description="We’ve got 10 winners! Ending the game now.",
            color=discord.Color.gold()
        ))
        await self.send_leaderboard(channel)
        await self.send_leaderboard(self.bot.get_channel(LEADERBOARD_CHANNEL_ID))

        private_channel = self.bot.get_channel(PRIVATE_CHANNEL_ID)
        role_name = await winners_role(private_channel, self.bot, lambda m: m.author == host)
        await giverole(private_channel, role_name)

        reset_leaderboard()
        self.active_lyrics.pop(channel.id, None)

    @app_commands.command(name="stoplyrics", description="Stop the ongoing lyrics game")
    async def stoplyrics(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don’t have permission.", ephemeral=True)

        if interaction.channel.id in self.active_lyrics:
            self.stopped_channels.add(interaction.channel.id)
            self.active_lyrics.pop(interaction.channel.id, None)
            await interaction.response.send_message("🛑 Lyrics game stopped.")
            await interaction.channel.send("⚠️ Lyrics game forcefully stopped.")
        else:
            await interaction.response.send_message("❗ No lyrics game running in this channel.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Lyrics(bot))
