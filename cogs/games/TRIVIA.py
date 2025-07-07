import discord
import random
import json
import asyncio
from discord.ext import commands
from discord import app_commands
from Utilities.Leaderboard import (
    add_recent_winner, is_leaderboard_full, reset_leaderboard,
    get_recent_winners, winners_role, giverole
)

ALLOWED_ROLES = ["Game Master", "Moderator"]
LEADERBOARD_CHANNEL_ID = 1379347453462970519
PRIVATE_CHANNEL_ID = 1391437573683019866
MAX_LEADERBOARD_ENTRIES = 10

class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_trivia = {}  
        self.trivia_questions = self.load_questions()
        self.user_wins = {}  
        self.used_questions = set()

    def load_questions(self):
        with open("Data/trivia_questions.json", "r") as f:
            return json.load(f)

    def get_random_question(self):
        if len(self.used_questions) >= len(self.trivia_questions):
            self.used_questions.clear()  

        available = [q for q in self.trivia_questions if q["question"] not in self.used_questions]
        question = random.choice(available)
        self.used_questions.add(question["question"])
        return question

    @app_commands.command(name="trivia", description="Start a trivia game")
    async def trivia(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

        if interaction.channel.id in self.active_trivia:
            return await interaction.response.send_message("❗ Trivia is already running.", ephemeral=True)

        self.active_trivia[interaction.channel.id] = {"running": True, "stop_event": asyncio.Event()}
        await interaction.response.send_message("🧠 Starting Trivia...")
        await self.ask_question(interaction.channel, interaction.user)

    async def ask_question(self, channel, host):
        question = self.get_random_question()
        correct_answer = question["answer"].strip().lower()

        embed = discord.Embed(
            title="🧠 Trivia Time!",
            description=f"{question['question']}\n\n⏱️ You have 30 seconds to answer!",
            color=discord.Color.blurple()
        )
        await channel.send(embed=embed)

        stop_event = self.active_trivia[channel.id]["stop_event"]
        start_time = asyncio.get_event_loop().time()

        while True:
            remaining_time = 30 - (asyncio.get_event_loop().time() - start_time)
            if remaining_time <= 0 or stop_event.is_set():
                break

            try:
                msg = await self.bot.wait_for(
                    "message",
                    timeout=remaining_time,
                    check=lambda m: m.channel == channel and not m.author.bot and m.content.strip().lower() == correct_answer
                )

                user_id = str(msg.author.id)
                self.user_wins[user_id] = self.user_wins.get(user_id, 0) + 1

                
                if self.user_wins[user_id] > 5:
                    continue

                win_count = self.user_wins[user_id]

                await msg.add_reaction("🎉")

                await channel.send(embed=discord.Embed(
                    title="🏆 Correct!",
                    description=(
                        f"{msg.author.mention} got it! The answer was **{correct_answer}**.\n"
                        f"🎯 Total Wins: `{win_count}/5`"
                    ),
                    color=discord.Color.green()
                ))

               
                if win_count == 5:
                    if is_leaderboard_full():
                        await self.end_game(channel, host)
                        return

                    add_recent_winner(
                    user_id=user_id, username=msg.author.name,
                    game_name="Trivia", host_id=host.id, host_name=host.name
                    )

                await channel.send(embed=discord.Embed(
                title="🌟 Milestone!",
                description=f"{msg.author.mention} reached **5 wins** and is now on the leaderboard!",
                color=discord.Color.blue()
                ))

                await self.send_leaderboard(channel)

                if is_leaderboard_full():
                    await self.end_game(channel, host)
                    return

               
                await self.ask_question(channel, host)
                return

            except asyncio.TimeoutError:
                break

        
        if self.active_trivia.get(channel.id, {}).get("running", False):
            await channel.send(embed=discord.Embed(
                title="⌛ Time's Up!",
                description=f"No one guessed it. The correct answer was **{correct_answer}**.",
                color=discord.Color.red()
            ))
            await self.ask_question(channel, host)

    async def send_leaderboard(self, channel):
        leaderboard = get_recent_winners()
        if not leaderboard:
            return

        embed = discord.Embed(title="🏆 Final Leaderboard", color=discord.Color.gold())
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
        self.active_trivia.pop(channel.id, None)

    @app_commands.command(name="stoptrivia", description="Stop the ongoing trivia game")
    async def stoptrivia(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don’t have permission.", ephemeral=True)

        if interaction.channel.id in self.active_trivia:
            self.active_trivia[interaction.channel.id]["stop_event"].set()
            self.active_trivia.pop(interaction.channel.id, None)

            await interaction.response.send_message("🛑 Trivia game stopped.")
            await interaction.channel.send("⚠️ Trivia game forcefully stopped.")
        else:
            await interaction.response.send_message("❗ No trivia running in this channel.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Trivia(bot))
