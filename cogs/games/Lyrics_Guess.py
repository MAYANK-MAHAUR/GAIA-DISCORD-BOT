import discord
import asyncio
import random
import json
from discord.ext import commands
from discord import app_commands
from Utilities import Leaderboard

ALLOWED_ROLES = ["Game Master", "Moderator"]
LEADERBOARD_CHANNEL_ID = 1379347453462970519

CATEGORY_FILES = {
    "india": "Data/lyrics_India.json",
    "pakistan": "Data/lyrics_Pakistan.json",
    "nigeria": "Data/lyrics_Nigeria.json",
    "global": "Data/lyrics_global.json"
}

class Lyrics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_lyrics = {}

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
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id in self.active_lyrics:
            await interaction.response.send_message("❗ A lyrics game is already running in this channel.", ephemeral=True)
            return

        file_path = CATEGORY_FILES.get(category.value)
        if not file_path:
            await interaction.response.send_message("❌ Invalid category selected.", ephemeral=True)
            return

        with open(file_path, "r", encoding="utf-8") as f:
            lyrics_data = json.load(f)

        self.active_lyrics[interaction.channel.id] = {
            "category": category.value,
            "data": lyrics_data
        }

        await interaction.response.send_message("🎶 Starting lyrics game loop...")
        await self.next_round(interaction.channel, interaction.user)

    async def next_round(self, channel, host):
        if channel.id not in self.active_lyrics:
            return

        lyrics_data = self.active_lyrics[channel.id]["data"]
        lyric = random.choice(lyrics_data)
        answer = lyric["answer"].strip().lower()

        embed = discord.Embed(
            title="🎶 Guess the Song!",
            description=f"**Lyric:**\n> {lyric['line']}\n\nYou have 60 seconds to guess the song name!",
            color=discord.Color.orange()
        )
        await channel.send(embed=embed)

        start_time = asyncio.get_event_loop().time()
        winner_found = False
        hint_sent = False

        def check(m):
            return (
                m.channel == channel and
                not m.author.bot and
                m.content.strip().lower() == answer and
                not any(str(w["user_id"]) == str(m.author.id) for w in Leaderboard.get_recent_winners())
            )

        while (
            not winner_found
            and (asyncio.get_event_loop().time() - start_time) < 60
            and channel.id in self.active_lyrics
        ):
            try:
                remaining = 60 - (asyncio.get_event_loop().time() - start_time)
                msg = await self.bot.wait_for("message", timeout=remaining, check=check)

                if channel.id not in self.active_lyrics:
                    return

                await msg.add_reaction("🎉")
                winner_found = True

                Leaderboard.add_recent_winner(
                    user_id=msg.author.id,
                    username=msg.author.name,
                    game_name="Lyrics",
                    host_id=host.id,
                    host_name=host.name
                )

                win_embed = discord.Embed(
                    title="🎉 Correct!",
                    description=f"{msg.author.mention} guessed it right! The answer was **{answer.title()}**.",
                    color=discord.Color.green()
                )
                await channel.send(embed=win_embed)

                leaderboard = Leaderboard.get_recent_winners()
                lb_text = ""
                for i, entry in enumerate(leaderboard, start=1):
                    lb_text += f"**{i}.** {entry['username']} | `{entry['game_name']}` | Host: {entry['host_name']} | *{entry['timestamp']}*\n"

                lb_embed = discord.Embed(
                    title="🏆 Leaderboard",
                    description=lb_text or "No winners yet.",
                    color=discord.Color.blue()
                )

                last_id = Leaderboard.get_last_leaderboard(channel.id)
                if last_id:
                    try:
                        prev_msg = await channel.fetch_message(last_id)
                        await prev_msg.delete()
                    except discord.NotFound:
                        pass

                leaderboard_msg = await channel.send(embed=lb_embed)
                Leaderboard.set_last_leaderboard(channel.id, leaderboard_msg.id)

                if Leaderboard.is_leaderboard_full():
                    full_embed = discord.Embed(
                        title="🎉 Leaderboard Full!",
                        description="10 winners recorded. Lyrics game is now ending.",
                        color=discord.Color.gold()
                    )
                    await channel.send(embed=full_embed)
                    leaderboard_channel = self.bot.get_channel(LEADERBOARD_CHANNEL_ID)
                    if leaderboard_channel:
                        await leaderboard_channel.send(embed=lb_embed)
                    Leaderboard.reset_leaderboard()
                    del self.active_lyrics[channel.id]
                    return

                break

            except asyncio.TimeoutError:
                break

            # Hint after 20 seconds if still active
            if not hint_sent and (asyncio.get_event_loop().time() - start_time) >= 20:
                if channel.id not in self.active_lyrics:
                    return
                hint_embed = discord.Embed(
                    title="💡 Hint Time!",
                    description=f"The song starts with: **{answer[:3]}...**",
                    color=discord.Color.yellow()
                )
                await channel.send(embed=hint_embed)
                hint_sent = True

        if not winner_found and channel.id in self.active_lyrics:
            timeout_embed = discord.Embed(
                title="⌛ Time's Up!",
                description=f"No one guessed it. The correct answer was **{answer.title()}**.",
                color=discord.Color.red()
            )
            await channel.send(embed=timeout_embed)

        if channel.id in self.active_lyrics:
            await asyncio.sleep(3)
            await self.next_round(channel, host)

    @app_commands.command(name="stoplyrics", description="Stop the ongoing lyrics game in this channel.")
    async def stoplyrics(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id in self.active_lyrics:
            del self.active_lyrics[interaction.channel.id]
            await interaction.response.send_message("🛑 Lyrics game stopped in this channel.")
            await interaction.channel.send("⚠️ The lyrics game has been forcefully stopped.")
        else:
            await interaction.response.send_message("❗ No lyrics game running in this channel.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Lyrics(bot))
