import discord
import asyncio
import json
from discord.ext import commands
from discord import app_commands
from Utilities.Leaderboard import (
    add_recent_winner, is_leaderboard_full, reset_leaderboard,
    get_recent_winners, winners_role, giverole
)

ALLOWED_ROLES = ["Game Master", "Moderator"]
LEADERBOARD_CHANNEL_ID = 1379347453462970519
PRIVATE_CHANNEL_ID = 1391437573683019866

CHOICES = [
    app_commands.Choice(name="🪨 Rock", value="rock"),
    app_commands.Choice(name="📄 Paper", value="paper"),
    app_commands.Choice(name="✂️ Scissors", value="scissors")
]

BEATS = {
    "rock": "paper",
    "paper": "scissors",
    "scissors": "rock"
}

class RPS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_rps = {}
        self.rps_wins = {}

    @app_commands.command(name="startrps", description="Start Rock Paper Scissors with a chosen answer")
    @app_commands.describe(correct_choice="Pick your secret choice (players will try to guess the counter)")
    @app_commands.choices(correct_choice=CHOICES)
    async def startrps(
        self,
        interaction: discord.Interaction,
        correct_choice: app_commands.Choice[str]
    ):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

        if interaction.channel.id in self.active_rps:
            return await interaction.response.send_message("❗ RPS is already running in this channel.", ephemeral=True)

        host_choice = correct_choice.value.lower()
        if host_choice == "scissor":
            host_choice = "scissors"

        correct_answer = BEATS[host_choice] 
        self.active_rps[interaction.channel.id] = {
            "running": True,
            "stop_event": asyncio.Event(),
            "answer": correct_answer,
            "host": interaction.user
        }

        await interaction.response.send_message(embed=discord.Embed(
            title="🎮 Rock Paper Scissors Started!",
            description=f"Host has picked a choice. Guess what **beats** it! (rock, paper, or scissors)",
            color=discord.Color.blurple()
        ))

        await self.wait_for_guess(interaction.channel)

    async def wait_for_guess(self, channel):
        data = self.active_rps[channel.id]
        correct = data["answer"]
        stop_event = data["stop_event"]
        host = data["host"]

        while not stop_event.is_set():
            try:
                msg = await self.bot.wait_for("message", timeout=300.0, check=lambda m: m.channel == channel and not m.author.bot)
                guess = msg.content.lower().strip()
                if guess == "scissor":
                    guess = "scissors"

                if guess == correct:
                    user_id = str(msg.author.id)
                    self.rps_wins[user_id] = self.rps_wins.get(user_id, 0) + 1

                    await msg.add_reaction("🎉")
                    await channel.send(embed=discord.Embed(
                        title="🏆 Correct Guess!",
                        description=f"{msg.author.mention} guessed **{correct}** and won!",
                        color=discord.Color.green()
                    ))

                    add_recent_winner(
                        user_id=user_id,
                        username=msg.author.name,
                        game_name="RPS",
                        host_id=host.id,
                        host_name=host.name
                    )

                    await self.send_leaderboard(channel)

                    if is_leaderboard_full():
                        await self.end_game(channel, host)
                    else:
                        self.active_rps.pop(channel.id, None)
                    return

            except asyncio.TimeoutError:
                break

        if self.active_rps.get(channel.id, {}).get("running"):
            await channel.send(embed=discord.Embed(
                title="⌛ Game Timed Out",
                description=f"No one guessed correctly. The answer was **{correct}**.",
                color=discord.Color.red()
            ))
            self.active_rps.pop(channel.id, None)

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
        self.active_rps.pop(channel.id, None)

    @app_commands.command(name="stoprps", description="Force stop the Rock Paper Scissors game")
    async def stoprps(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

        if interaction.channel.id in self.active_rps:
            self.active_rps[interaction.channel.id]["stop_event"].set()
            self.active_rps.pop(interaction.channel.id, None)
            await interaction.response.send_message("🛑 RPS game stopped.")
            await interaction.channel.send("⚠️ RPS game forcefully stopped.")
        else:
            await interaction.response.send_message("❗ No RPS game is currently running.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RPS(bot))
