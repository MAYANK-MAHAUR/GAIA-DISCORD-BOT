import discord
import random
import json
import asyncio
import os
from discord.ext import commands
from discord import app_commands


from dotenv import load_dotenv

load_dotenv()
LEADERBOARD_CHANNEL_ID = int(os.getenv('LEADERBOARD_CHANNEL_ID'))
PRIVATE_CHANNEL_ID = int(os.getenv('PRIVATE_CHANNEL_ID'))

ALLOWED_ROLES = ["Game Master", "Moderator"]
MAX_LEADERBOARD_ENTRIES = 10

class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_trivia = {}
        self.trivia_questions = self.load_questions()
        self.user_wins = {}
        self.used_questions = set()
        self.leaderboard_cog = None

    @commands.Cog.listener()
    async def on_ready(self):
        print("Trivia cog is ready.")
        await self.bot.wait_until_ready()
        self.leaderboard_cog = self.bot.get_cog('Leaderboard')
        if self.leaderboard_cog:
            print("Leaderboard cog found and linked to Trivia cog.")
        else:
            print("WARNING: Leaderboard cog not found. Leaderboard functions will not work.")

    def load_questions(self):
        try:
            with open("Data/trivia_questions.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("Error: Data/trivia_questions.json not found!")
            return []
        except json.JSONDecodeError:
            print("Error: Data/trivia_questions.json is corrupted or empty.")
            return []

    def get_random_question(self):
        if len(self.used_questions) >= len(self.trivia_questions) or not self.trivia_questions:
            self.used_questions.clear()
            if not self.trivia_questions:
                return None

        available = [q for q in self.trivia_questions if q["question"] not in self.used_questions]
        if not available:
            self.used_questions.clear()
            available = self.trivia_questions[:]
        
        question = random.choice(available)
        self.used_questions.add(question["question"])
        return question

    @app_commands.command(name="trivia", description="Start a trivia game")
    async def trivia(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don't have permission to start trivia.", ephemeral=True)

        if interaction.channel.id in self.active_trivia:
            return await interaction.response.send_message("❗ Trivia is already running in this channel.", ephemeral=True)
        
        if not self.trivia_questions:
            return await interaction.response.send_message("❌ No trivia questions loaded. Please check `Data/trivia_questions.json`.", ephemeral=True)


        self.active_trivia[interaction.channel.id] = {"running": True, "stop_event": asyncio.Event()}
        await interaction.response.send_message("🧠 Starting Trivia...")
        
        self.bot.loop.create_task(self.ask_question(interaction.channel, interaction.user))


    async def ask_question(self, channel, host):
        if not self.active_trivia.get(channel.id, {}).get("running", False):
            return

        question_data = self.get_random_question()
        if not question_data:
            await channel.send("❌ No more unique trivia questions available!")
            del self.active_trivia[channel.id]
            return

        correct_answer = question_data["answer"].strip().lower()

        embed = discord.Embed(
            title="🧠 Trivia Time!",
            description=f"**{question_data['question']}**\n\n⏱️ You have 30 seconds to answer!",
            color=discord.Color.blurple()
        )
        await channel.send(embed=embed)

        stop_event = self.active_trivia[channel.id]["stop_event"]
        start_time = asyncio.get_event_loop().time()

        valid_winner_found = False
        
        while not stop_event.is_set():
            remaining_time = 30 - (asyncio.get_event_loop().time() - start_time)
            if remaining_time <= 0:
                break

            try:
                msg = await self.bot.wait_for(
                    "message",
                    timeout=remaining_time,
                    check=lambda m: m.channel == channel and not m.author.bot and m.content.strip().lower() == correct_answer
                )

                user_id = str(msg.author.id)
                current_wins = self.user_wins.get(user_id, 0)

                if current_wins >= 5:
                    await msg.add_reaction("✋")
                    await channel.send(
                        f"{msg.author.mention}, you've already achieved **5 wins**! "
                        f"Please let others have a chance to play this round. The question is still open."
                    )
                    continue
                
                valid_winner_found = True
                self.user_wins[user_id] = current_wins + 1
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
                    if self.leaderboard_cog:
                        added = self.leaderboard_cog.add_recent_winner(
                            user_id=user_id, username=msg.author.name,
                            game_name="Trivia", host_id=host.id, host_name=host.name
                        )
                        if added:
                            await channel.send(embed=discord.Embed(
                                title="🌟 Milestone!",
                                description=f"{msg.author.mention} reached **5 wins** and is now on the leaderboard!",
                                color=discord.Color.blue()
                            ))
                            # --- NEW: Display leaderboard in the current channel ---
                            await self.leaderboard_cog.display_leaderboard_command(channel)
                            # --- END NEW ---

                            lb_channel = self.bot.get_channel(LEADERBOARD_CHANNEL_ID)
                            if lb_channel:
                                await self.leaderboard_cog.update_leaderboard_display(lb_channel)
                            else:
                                await channel.send(f"⚠️ Leaderboard channel (ID: {LEADERBOARD_CHANNEL_ID}) not found for automatic update.")

                            if self.leaderboard_cog.is_leaderboard_full():
                                await self.end_game(channel, host)
                                return

                        else:
                            await channel.send(f"ℹ️ {msg.author.mention} is already on the leaderboard!")
                    else:
                        await channel.send("⚠️ Leaderboard system is not available.")
                
                break

            except asyncio.TimeoutError:
                break

        if not valid_winner_found and self.active_trivia.get(channel.id, {}).get("running", False):
            await channel.send(embed=discord.Embed(
                title="⌛ Time's Up!",
                description=f"No one guessed it. The correct answer was **{correct_answer}**.",
                color=discord.Color.red()
            ))
        
        if self.active_trivia.get(channel.id, {}).get("running", False):
            await self.ask_question(channel, host)

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
        self.active_trivia.pop(channel.id, None)
        self.user_wins.clear()

    @app_commands.command(name="stoptrivia", description="Stop the ongoing trivia game")
    async def stoptrivia(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don’t have permission to stop trivia.", ephemeral=True)

        if interaction.channel.id in self.active_trivia:
            self.active_trivia[interaction.channel.id]["stop_event"].set()
            self.active_trivia.pop(interaction.channel.id, None)
            self.user_wins.clear()

            await interaction.response.send_message("🛑 Trivia game stopped.")
            await interaction.channel.send("⚠️ Trivia game forcefully stopped in this channel.")
        else:
            await interaction.response.send_message("❗ No trivia running in this channel.", ephemeral=True)

    @app_commands.command(name="resettriviawins", description="Resets all users' trivia 5-win counts.")
    async def resettriviawins(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don't have permission to reset win counts.", ephemeral=True)

        if self.user_wins:
            self.user_wins.clear()
            await interaction.response.send_message(
                "✅ All users' trivia 5-win counts have been reset to `0`.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "ℹ️ No active 5-win counts for trivia to reset.",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Trivia(bot))