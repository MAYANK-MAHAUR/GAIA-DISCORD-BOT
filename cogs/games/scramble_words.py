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

class Scramble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_scramble = {}
        self.scramble_words = self.load_words()

    def load_words(self):
        with open("Data/scramble_words.json", "r") as f:
            return json.load(f)

    def scramble_word(self, word):
        scrambled = list(word)
        while True:
            random.shuffle(scrambled)
            if ''.join(scrambled) != word:
                break
        return ''.join(scrambled)

    @app_commands.command(name="scramble", description="Start a word scramble game")
    async def scramble(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id in self.active_scramble:
            await interaction.response.send_message("❗ A scramble game is already running in this channel.", ephemeral=True)
            return

        self.active_scramble[interaction.channel.id] = True
        await interaction.response.send_message("🧩 Starting scramble game...")
        await self.next_question(interaction.channel, interaction.user)

    async def next_question(self, channel, host):
        word = random.choice(self.scramble_words)
        scrambled = self.scramble_word(word)

        embed = discord.Embed(
            title="🔤 Unscramble the Word!",
            description=f"**{scrambled}**\n\nFirst to guess the correct word wins! You have 30 seconds.",
            color=discord.Color.orange()
        )
        await channel.send(embed=embed)

        start_time = asyncio.get_event_loop().time()
        winner_found = False

        while (
            not winner_found and 
            (asyncio.get_event_loop().time() - start_time) < 30 and 
            channel.id in self.active_scramble
        ):
            try:
                remaining_time = 30 - (asyncio.get_event_loop().time() - start_time)
                msg = await self.bot.wait_for(
                    "message",
                    timeout=remaining_time,
                    check=lambda m: m.channel == channel and not m.author.bot and m.content.strip().lower() == word.lower()
                )

                # If the game was stopped while waiting for input
                if channel.id not in self.active_scramble:
                    return

                current_leaderboard = Sec_Leaderboard.load_leaderboard()
                user_id = str(msg.author.id)

                if user_id in current_leaderboard and current_leaderboard[user_id]["wins"] >= 5:
                    continue  # Skip if already reached 5 wins

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
                    description=f"{msg.author.mention} guessed it right! The word was **{word}**.",
                    color=discord.Color.green()
                )
                await channel.send(embed=win_embed)

                await self.send_leaderboard(channel)

                winner_found = True

                # Stop game if leaderboard is full
                top = Sec_Leaderboard.get_top_second()
                if len(top) >= MAX_LEADERBOARD_ENTRIES:
                    stop_embed = discord.Embed(
                        title="📋 Leaderboard Full!",
                        description="We've got 10 winners! The game is now ending.",
                        color=discord.Color.gold()
                    )
                    await channel.send(embed=stop_embed)
                    del self.active_scramble[channel.id]
                    return

                if channel.id in self.active_scramble:
                    await self.next_question(channel, host)

            except asyncio.TimeoutError:
                break

        if not winner_found and channel.id in self.active_scramble:
            timeout_embed = discord.Embed(
                title="⌛ Time's Up!",
                description=f"No one guessed the word. It was **{word}**.",
                color=discord.Color.red()
            )
            await channel.send(embed=timeout_embed)
            del self.active_scramble[channel.id]

    async def send_leaderboard(self, channel):
        leaderboard = Sec_Leaderboard.get_top_second()
        if not leaderboard:
            return

        embed = discord.Embed(title="🏆 Scramble Leaderboard", color=discord.Color.gold())
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

    @app_commands.command(name="stopscramble", description="Stop the ongoing scramble game")
    async def stopscramble(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id in self.active_scramble:
            del self.active_scramble[interaction.channel.id]
            await interaction.response.send_message("🛑 Scramble game stopped in this channel.")
            await interaction.channel.send("⚠️ The scramble game has been forcefully stopped.")
        else:
            await interaction.response.send_message("❗ No scramble game running in this channel.", ephemeral=True)

    @app_commands.command(name="resetscrambleleaderboard", description="Reset the current scramble leaderboard.")
    async def resetscrambleleaderboard(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        Sec_Leaderboard.reset_second_leaderboard()
        await interaction.response.send_message("✅ Scramble leaderboard has been reset.")

async def setup(bot):
    await bot.add_cog(Scramble(bot))
