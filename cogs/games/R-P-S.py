import discord
import asyncio
import json
import os
from discord.ext import commands
from discord import app_commands


from dotenv import load_dotenv
load_dotenv()
LEADERBOARD_CHANNEL_ID = int(os.getenv('LEADERBOARD_CHANNEL_ID'))
PRIVATE_CHANNEL_ID = int(os.getenv('PRIVATE_CHANNEL_ID'))


ALLOWED_ROLES = ["Game Master", "Moderator"]

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
        self.leaderboard_cog = None

    @commands.Cog.listener()
    async def on_ready(self):
        print("RPS cog is ready.")
        await self.bot.wait_until_ready()
        self.leaderboard_cog = self.bot.get_cog('Leaderboard')
        if self.leaderboard_cog:
            print("Leaderboard cog found and linked to RPS cog.")
        else:
            print("WARNING: Leaderboard cog not found. Leaderboard functions will not work for RPS.")

    @app_commands.command(name="startrps", description="Start Rock Paper Scissors with a chosen answer")
    @app_commands.describe(correct_choice="Pick your secret choice (players will try to guess the counter)")
    @app_commands.choices(correct_choice=CHOICES)
    async def startrps(
        self,
        interaction: discord.Interaction,
        correct_choice: app_commands.Choice[str]
    ):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don't have permission to start RPS.", ephemeral=True)

        if interaction.channel.id in self.active_rps:
            return await interaction.response.send_message("❗ RPS is already running in this channel.", ephemeral=True)

        host_choice = correct_choice.value.lower()
        if host_choice == "scissor":
            host_choice = "scissors"

        correct_answer_for_players = BEATS[host_choice] 
        self.active_rps[interaction.channel.id] = {
            "running": True,
            "stop_event": asyncio.Event(),
            "answer": correct_answer_for_players,
            "host": interaction.user
        }

        await interaction.response.send_message(embed=discord.Embed(
            title="🎮 Rock Paper Scissors Started!",
            description=f"Host has picked a choice. Guess what **beats** it! (rock, paper, or scissors)\n\n"
                        f"⏱️ You have 60 seconds to guess!",
            color=discord.Color.blurple()
        ))

        self.bot.loop.create_task(self.wait_for_guess(interaction.channel))

    async def wait_for_guess(self, channel):
        data = self.active_rps.get(channel.id)
        if not data or not data["running"]:
            return

        correct_guess = data["answer"]
        stop_event = data["stop_event"]
        host = data["host"]

        timeout_seconds = 60

        winner_found = False

        while not stop_event.is_set():
            try:
                msg = await self.bot.wait_for(
                    "message",
                    timeout=timeout_seconds,
                    check=lambda m: m.channel == channel and not m.author.bot and m.content.lower().strip() in ["rock", "paper", "scissors", "scissor"]
                )
                
                guess = msg.content.lower().strip()
                if guess == "scissor":
                    guess = "scissors"

                if guess == correct_guess:
                    winner_found = True
                    user_id = str(msg.author.id)

                    await msg.add_reaction("🎉")
                    await channel.send(embed=discord.Embed(
                        title="🏆 Correct Guess!",
                        description=(
                            f"{msg.author.mention} guessed **{correct_guess.capitalize()}** and won!"
                        ),
                        color=discord.Color.green()
                    ))

                    if self.leaderboard_cog:
                        added = self.leaderboard_cog.add_recent_winner(
                            user_id=user_id, username=msg.author.name,
                            game_name="RPS", host_id=host.id, host_name=host.name
                        )
                        if added:
                            await channel.send(embed=discord.Embed(
                                title="✅ Winner Added!",
                                description=f"{msg.author.mention} has been added to the recent winners leaderboard!",
                                color=discord.Color.blue()
                            ))
                            await self.leaderboard_cog.display_leaderboard_command(channel)

                            lb_channel = self.bot.get_channel(LEADERBOARD_CHANNEL_ID)
                            if lb_channel:
                                await self.leaderboard_cog.update_leaderboard_display(lb_channel)
                            else:
                                await channel.send(f"⚠️ Leaderboard channel (ID: {LEADERBOARD_CHANNEL_ID}) not found for automatic update.")

                            if self.leaderboard_cog.is_leaderboard_full():
                                await self.end_game(channel, host)
                            
                            self.active_rps.pop(channel.id, None)
                            stop_event.set()
                            return 
                        else:
                            await channel.send(f"ℹ️ {msg.author.mention} is already in the current leaderboard of 10 winners. The game continues.")
                    else:
                        await channel.send("⚠️ Leaderboard system is not available.")
                    
                    break
                
            except asyncio.TimeoutError:
                break

        if not winner_found and self.active_rps.get(channel.id, {}).get("running", False):
            await channel.send(embed=discord.Embed(
                title="⌛ Game Timed Out",
                description=f"No one guessed correctly. The correct answer was **{correct_guess.capitalize()}**.",
                color=discord.Color.red()
            ))
        
        self.active_rps.pop(channel.id, None)


    async def end_game(self, channel, host):
        if not self.leaderboard_cog:
            await channel.send("⚠️ Leaderboard system is not available, cannot finalize game.")
            return

        await channel.send(embed=discord.Embed(
            title="📋 Leaderboard Full!",
            description="We’ve got 10 winners! Ending the game now.",
            color=discord.Color.gold()
        ))

        await self.leaderboard_cog.display_leaderboard_command(channel)

        lb_channel = self.bot.get_channel(LEADERBOARD_CHANNEL_ID)
        if lb_channel:
            await self.leaderboard_cog.update_leaderboard_display(lb_channel)
        else:
            await channel.send(f"⚠️ Dedicated leaderboard channel (ID: {LEADERBOARD_CHANNEL_ID}) not found for final display.")

        private_channel = self.bot.get_channel(PRIVATE_CHANNEL_ID)
        if not private_channel:
            await channel.send(f"⚠️ Private channel for role management (ID: {PRIVATE_CHANNEL_ID}) not found. Skipping role assignment.")
        else:
            role_name = await self.leaderboard_cog._winners_role_logic(
                private_channel, self.bot, lambda m: m.author == host and m.channel == private_channel
            )
            if role_name:
                await self.leaderboard_cog._giverole_logic(private_channel, role_name)
            else:
                await private_channel.send("❌ Role assignment process cancelled or failed for winners.")

        self.leaderboard_cog.reset_leaderboard()
        self.active_rps.pop(channel.id, None)

    @app_commands.command(name="stoprps", description="Force stop the Rock Paper Scissors game")
    async def stoprps(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don't have permission to stop RPS.", ephemeral=True)

        if interaction.channel.id in self.active_rps:
            self.active_rps[interaction.channel.id]["stop_event"].set()
            self.active_rps.pop(interaction.channel.id, None)

            await interaction.response.send_message("🛑 RPS game stopped.")
            await interaction.channel.send("⚠️ RPS game forcefully stopped in this channel.")
        else:
            await interaction.response.send_message("❗ No RPS game is currently running in this channel.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RPS(bot))