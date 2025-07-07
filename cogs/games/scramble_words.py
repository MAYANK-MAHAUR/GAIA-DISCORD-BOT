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

class Scramble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_scramble = {}
        self.scramble_words = self.load_words()
        self.user_wins = {}
        self.used_words = set()

    def load_words(self):
        with open("Data/scramble_words.json", "r") as f:
            return json.load(f)

    def get_random_word(self):
        if len(self.used_words) >= len(self.scramble_words):
            self.used_words.clear()

        available = [w for w in self.scramble_words if w not in self.used_words]
        word = random.choice(available)
        self.used_words.add(word)
        scrambled = ''.join(random.sample(word, len(word)))
        return word, scrambled

    @app_commands.command(name="scramble", description="Start a scramble word game")
    async def scramble(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

        if interaction.channel.id in self.active_scramble:
            return await interaction.response.send_message("❗ Scramble is already running.", ephemeral=True)

        self.active_scramble[interaction.channel.id] = {"running": True, "stop_event": asyncio.Event()}
        await interaction.response.send_message("🔤 Starting Scramble...")
        await self.ask_word(interaction.channel, interaction.user)

    async def ask_word(self, channel, host):
        word, scrambled = self.get_random_word()
        embed = discord.Embed(
            title="🔤 Unscramble This Word!",
            description=f"`{scrambled}`\n\n⏱️ You have 30 seconds to answer!",
            color=discord.Color.orange()
        )
        await channel.send(embed=embed)

        stop_event = self.active_scramble[channel.id]["stop_event"]
        start_time = asyncio.get_event_loop().time()

        while True:
            remaining_time = 30 - (asyncio.get_event_loop().time() - start_time)
            if remaining_time <= 0 or stop_event.is_set():
                break

            try:
                msg = await self.bot.wait_for(
                    "message",
                    timeout=remaining_time,
                    check=lambda m: m.channel == channel and not m.author.bot and m.content.strip().lower() == word.lower()
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
                        f"{msg.author.mention} unscrambled it! The word was **{word}**.\n"
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
                        game_name="Scramble", host_id=host.id, host_name=host.name
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

                await self.ask_word(channel, host)
                return

            except asyncio.TimeoutError:
                break

        if self.active_scramble.get(channel.id, {}).get("running", False):
            await channel.send(embed=discord.Embed(
                title="⌛ Time's Up!",
                description=f"No one guessed it. The correct word was **{word}**.",
                color=discord.Color.red()
            ))
            await self.ask_word(channel, host)

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
        self.active_scramble.pop(channel.id, None)

    @app_commands.command(name="stopscramble", description="Stop the ongoing scramble game")
    async def stopscramble(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You don’t have permission.", ephemeral=True)

        if interaction.channel.id in self.active_scramble:
            self.active_scramble[interaction.channel.id]["stop_event"].set()
            self.active_scramble.pop(interaction.channel.id, None)

            await interaction.response.send_message("🛑 Scramble game stopped.")
            await interaction.channel.send("⚠️ Scramble game forcefully stopped.")
        else:
            await interaction.response.send_message("❗ No scramble running in this channel.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Scramble(bot))
