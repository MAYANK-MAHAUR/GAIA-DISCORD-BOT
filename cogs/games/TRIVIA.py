import discord
import random
import json
import asyncio
from discord.ext import commands
from discord import app_commands
from Utilities import Sec_Leaderboard

ALLOWED_ROLES = ["Game Master", "Moderator"]
LEADERBOARD_CHANNEL_ID = 1379347453462970519
MAX_LEADERBOARD_ENTRIES = 10

class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_trivia = {}
        self.trivia_questions = self.load_questions()

    def load_questions(self):
        with open("Data/trivia_questions.json", "r") as f:
            return json.load(f)

    @app_commands.command(name="trivia", description="Start a trivia game")
    async def trivia(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id in self.active_trivia:
            await interaction.response.send_message("❗ A trivia game is already running in this channel.", ephemeral=True)
            return

        self.active_trivia[interaction.channel.id] = {"running": True, "stop_event": asyncio.Event()}
        await interaction.response.send_message("🧠 Starting trivia game...")
        await self.next_question(interaction.channel, interaction.user)

    async def next_question(self, channel, host):
        question = random.choice(self.trivia_questions)
        answer = question["answer"].strip().lower()

        embed = discord.Embed(
            title="🧠 Trivia Time!",
            description=f"{question['question']}\n\nYou have 30 seconds to answer!",
            color=discord.Color.blurple()
        )
        await channel.send(embed=embed)

        start_time = asyncio.get_event_loop().time()
        winner_found = False
        stop_event = self.active_trivia[channel.id]["stop_event"]

        while (
            not winner_found and
            (asyncio.get_event_loop().time() - start_time) < 30 and
            self.active_trivia.get(channel.id, {}).get("running", False)
        ):
            if stop_event.is_set():
                return

            try:
                remaining_time = 30 - (asyncio.get_event_loop().time() - start_time)
                msg = await self.bot.wait_for(
                    "message",
                    timeout=remaining_time,
                    check=lambda m: m.channel == channel and not m.author.bot and m.content.strip().lower() == answer
                )

                if not self.active_trivia.get(channel.id, {}).get("running", False):
                    return

                current_leaderboard = Sec_Leaderboard.load_leaderboard()
                user_id = str(msg.author.id)

                if user_id in current_leaderboard and current_leaderboard[user_id]["wins"] >= 5:
                    continue

                await msg.add_reaction("🎉")
                Sec_Leaderboard.add_second_win(user_id=msg.author.id, username=msg.author.name)

                updated_leaderboard = Sec_Leaderboard.load_leaderboard()
                if updated_leaderboard[user_id]["wins"] == 5:
                    milestone_embed = discord.Embed(
                        title="🌟 Milestone!",
                        description=f"{msg.author.mention} reached **5 wins** and is now on the **final leaderboard**!",
                        color=discord.Color.blue()
                    )
                    await channel.send(embed=milestone_embed)

                win_embed = discord.Embed(
                    title="🏆 Correct!",
                    description=f"{msg.author.mention} guessed it right! The answer was **{answer}**.",
                    color=discord.Color.green()
                )
                await channel.send(embed=win_embed)

                await self.send_leaderboard(channel)

                winner_found = True
                top = Sec_Leaderboard.get_top_second()
                if len(top) >= MAX_LEADERBOARD_ENTRIES:
                    stop_embed = discord.Embed(
                        title="📋 Leaderboard Full!",
                        description="We've got 10 winners! The game is now ending.",
                        color=discord.Color.gold()
                    )
                    await channel.send(embed=stop_embed)
                    del self.active_trivia[channel.id]
                    return

                if self.active_trivia.get(channel.id, {}).get("running", False):
                    await self.next_question(channel, host)

            except asyncio.TimeoutError:
                break

        if not winner_found and self.active_trivia.get(channel.id, {}).get("running", False):
            timeout_embed = discord.Embed(
                title="⌛ Time's Up!",
                description=f"No one guessed the answer. It was **{answer}**.",
                color=discord.Color.red()
            )
            await channel.send(embed=timeout_embed)
            del self.active_trivia[channel.id]

    async def send_leaderboard(self, channel):
        leaderboard = Sec_Leaderboard.get_top_second()
        if not leaderboard:
            return

        embed = discord.Embed(title="🏆 Trivia Leaderboard", color=discord.Color.gold())
        for idx, (user_id, entry) in enumerate(leaderboard, start=1):
            embed.add_field(
                name=f"{idx}. {entry['username']}",
                value=f"Wins: {entry['wins']}",
                inline=False
            )

        await channel.send(embed=embed)

        if len(leaderboard) >= MAX_LEADERBOARD_ENTRIES:
            leaderboard_channel = self.bot.get_channel(LEADERBOARD_CHANNEL_ID)
            if leaderboard_channel:
                await leaderboard_channel.send(embed=embed)
                Sec_Leaderboard.reset_second_leaderboard()

    @app_commands.command(name="stoptrivia", description="Stop the ongoing trivia game")
    async def stoptrivia(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id in self.active_trivia:
            self.active_trivia[interaction.channel.id]["stop_event"].set()
            del self.active_trivia[interaction.channel.id]
            await interaction.response.send_message("🛑 Trivia game stopped in this channel.")
            await interaction.channel.send("⚠️ The trivia game has been forcefully stopped.")
        else:
            await interaction.response.send_message("❗ No trivia game running in this channel.", ephemeral=True)

    @app_commands.command(name="resettrivialeaderboard", description="Reset the current trivia leaderboard.")
    async def resettrivialeaderboard(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        Sec_Leaderboard.reset_second_leaderboard()
        await interaction.response.send_message("✅ Trivia leaderboard has been reset.")

async def setup(bot):
    await bot.add_cog(Trivia(bot))
