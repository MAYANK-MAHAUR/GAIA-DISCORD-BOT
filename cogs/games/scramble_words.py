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

class Scramble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_scramble = {}
        self.scramble_words = self.load_words()
        self.user_wins = {}
        self.used_words = set()
        self.leaderboard_cog = None

    @commands.Cog.listener()
    async def on_ready(self):
        print("Scramble cog is ready.")
        await self.bot.wait_until_ready()
        self.leaderboard_cog = self.bot.get_cog('Leaderboard')
        if self.leaderboard_cog:
            print("Leaderboard cog found and linked to Scramble cog.")
        else:
            print("WARNING: Leaderboard cog not found. Leaderboard functions will not work for Scramble.")


    def load_words(self):
        try:
            with open("Data/scramble_words.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("Error: Data/scramble_words.json not found!")
            return []
        except json.JSONDecodeError:
            print("Error: Data/scramble_words.json is corrupted or empty.")
            return []

    def get_random_word(self):
        if len(self.used_words) >= len(self.scramble_words) or not self.scramble_words:
            self.used_words.clear()
            if not self.scramble_words:
                return None, None

        available = [w for w in self.scramble_words if w not in self.used_words]
        if not available:
            self.used_words.clear()
            available = self.scramble_words[:]

        word = random.choice(available)
        scrambled = ''.join(random.sample(word, len(word)))
        while scrambled == word:
            scrambled = ''.join(random.sample(word, len(word)))
        return word, scrambled

    @app_commands.command(name="scramble", description="Start a scramble word game")
    async def scramble(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don't have permission to start scramble.", ephemeral=True)

        if interaction.channel.id in self.active_scramble:
            return await interaction.response.send_message("❗ Scramble is already running in this channel.", ephemeral=True)
        
        if not self.scramble_words:
            return await interaction.response.send_message("❌ No scramble words loaded. Please check `Data/scramble_words.json`.", ephemeral=True)


        self.active_scramble[interaction.channel.id] = {"running": True, "stop_event": asyncio.Event()}
        await interaction.response.send_message("🔤 Starting Scramble...")
        
        self.bot.loop.create_task(self.ask_word(interaction.channel, interaction.user))

    async def ask_word(self, channel, host):
        if not self.active_scramble.get(channel.id, {}).get("running", False):
            return

        word, scrambled = self.get_random_word()
        if not word:
            await channel.send("❌ No more unique scramble words available!")
            del self.active_scramble[channel.id]
            return

        embed = discord.Embed(
            title="🔤 Unscramble This Word!",
            description=f"`{scrambled}`\n\n⏱️ You have 30 seconds to answer!",
            color=discord.Color.orange()
        )
        await channel.send(embed=embed)

        stop_event = self.active_scramble[channel.id]["stop_event"]
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
                    check=lambda m: m.channel == channel and not m.author.bot and m.content.strip().lower() == word.lower()
                )

                user_id = str(msg.author.id)
                current_wins = self.user_wins.get(user_id, 0)

                if current_wins >= 5:
                    await msg.add_reaction("✋")
                    await channel.send(
                        f"{msg.author.mention}, you've already achieved **5 wins**! "
                        f"Please let others have a chance to play this round. The word is still open."
                    )
                    continue
                
                valid_winner_found = True
                self.user_wins[user_id] = current_wins + 1
                win_count = self.user_wins[user_id]

                await msg.add_reaction("🎉")

                await channel.send(embed=discord.Embed(
                    title="🏆 Correct!",
                    description=(
                        f"{msg.author.mention} unscrambled it! The word was **{word}**.\n"
                        f"🎯 Total Wins: `{win_count}/5`"
                    ),
                    color=discord.Color.green()
                ))

                if win_count == 5:
                    if self.leaderboard_cog:
                        added = self.leaderboard_cog.add_recent_winner(
                            user_id=user_id, username=msg.author.name,
                            game_name="Scramble", host_id=host.id, host_name=host.name
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
                                await channel.send(f"⚠️ Dedicated leaderboard channel (ID: {LEADERBOARD_CHANNEL_ID}) not found for automatic update.")

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

        if not valid_winner_found and self.active_scramble.get(channel.id, {}).get("running", False):
            await channel.send(embed=discord.Embed(
                title="⌛ Time's Up!",
                description=f"No one guessed it. The correct word was **{word}**.",
                color=discord.Color.red()
            ))
        
        if self.active_scramble.get(channel.id, {}).get("running", False):
            await self.ask_word(channel, host)

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
        self.active_scramble.pop(channel.id, None)
        self.user_wins.clear()

    @app_commands.command(name="stopscramble", description="Stop the ongoing scramble game")
    async def stopscramble(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don’t have permission to stop scramble.", ephemeral=True)

        if interaction.channel.id in self.active_scramble:
            self.active_scramble[interaction.channel.id]["stop_event"].set()
            self.active_scramble.pop(interaction.channel.id, None)
            self.user_wins.clear()

            await interaction.response.send_message("🛑 Scramble game stopped.")
            await interaction.channel.send("⚠️ Scramble game forcefully stopped in this channel.")
        else:
            await interaction.response.send_message("❗ No scramble running in this channel.", ephemeral=True)

    @app_commands.command(name="resetscramblesec", description="Resets all users' scramble 5-win counts.")
    async def resetscramblesec(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don't have permission to reset win counts.", ephemeral=True)

        if self.user_wins:
            self.user_wins.clear()
            await interaction.response.send_message(
                "✅ All users' scramble 5-win counts have been reset to `0`.",
                ephemeral=False
            )
        else:
            await interaction.response.send_message(
                "ℹ️ No active 5-win counts for scramble to reset.",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Scramble(bot))