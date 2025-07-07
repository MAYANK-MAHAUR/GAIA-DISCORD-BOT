#NOT UPDATED  IGNORE 
import discord
import asyncio
import random
import json
from discord.ext import commands
from discord import app_commands
from Utilities import Leaderboard

ALLOWED_ROLES = ["Game Master", "Moderator"]
LEADERBOARD_CHANNEL_ID = 1379347453462970519

class EmojiDecode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_emoji = {}

    def load_clues(self):
        with open("Data/emoji_clues.json", "r", encoding="utf-8") as f:
            return json.load(f)

    @app_commands.command(name="emoji", description="Guess the word based on emoji clues!")
    async def emoji(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id in self.active_emoji:
            await interaction.response.send_message("❗ An emoji game is already running in this channel.", ephemeral=True)
            return

        clues = self.load_clues()
        self.active_emoji[interaction.channel.id] = clues
        await interaction.response.send_message("🔤 Starting Emoji Decode game!")
        await self.next_round(interaction.channel, interaction.user)

    async def next_round(self, channel, host):
        if channel.id not in self.active_emoji:
            return

        clues = self.active_emoji[channel.id]
        clue = random.choice(clues)
        emoji, answer = clue["emoji"], clue["answer"].strip().lower()

        embed = discord.Embed(
            title="🧩 Emoji Decode!",
            description=f"**Emoji Clue:**\n{emoji}\n\nYou have 60 seconds to guess!",
            color=discord.Color.orange()
        )
        await channel.send(embed=embed)

        start_time = asyncio.get_event_loop().time()
        hint_sent = False
        winner_found = False

        def check(m):
            return (
                m.channel == channel and
                not m.author.bot and
                m.content.strip().lower() == answer and
                not any(str(w["user_id"]) == str(m.author.id) for w in Leaderboard.get_recent_winners())
            )

        while (
            not winner_found and
            (asyncio.get_event_loop().time() - start_time) < 60 and
            channel.id in self.active_emoji
        ):
            try:
                remaining = 60 - (asyncio.get_event_loop().time() - start_time)
                msg = await self.bot.wait_for("message", timeout=remaining, check=check)

                if channel.id not in self.active_emoji:
                    return

                await msg.add_reaction("🎉")
                winner_found = True

                Leaderboard.add_recent_winner(
                    user_id=msg.author.id,
                    username=msg.author.name,
                    game_name="Emoji Decode",
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
                        description="10 winners recorded. Emoji game is now ending.",
                        color=discord.Color.gold()
                    )
                    await channel.send(embed=full_embed)
                    leaderboard_channel = self.bot.get_channel(LEADERBOARD_CHANNEL_ID)
                    if leaderboard_channel:
                        await leaderboard_channel.send(embed=lb_embed)
                    Leaderboard.reset_leaderboard()
                    del self.active_emoji[channel.id]
                    return

                break

            except asyncio.TimeoutError:
                break

            if not hint_sent and (asyncio.get_event_loop().time() - start_time) >= 20:
                if channel.id not in self.active_emoji:
                    return
                hint = f"The answer starts with: **{answer[:2]}...**"
                hint_embed = discord.Embed(
                    title="💡 Hint Time!",
                    description=hint,
                    color=discord.Color.yellow()
                )
                await channel.send(embed=hint_embed)
                hint_sent = True

        if not winner_found and channel.id in self.active_emoji:
            timeout_embed = discord.Embed(
                title="⌛ Time's Up!",
                description=f"No one guessed it. The correct answer was **{answer.title()}**.",
                color=discord.Color.red()
            )
            await channel.send(embed=timeout_embed)

        if channel.id in self.active_emoji:
            await asyncio.sleep(3)
            await self.next_round(channel, host)

    @app_commands.command(name="stopemoji", description="Stop the ongoing Emoji Decode game.")
    async def stopemoji(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id in self.active_emoji:
            del self.active_emoji[interaction.channel.id]
            await interaction.response.send_message("🛑 Emoji Decode game stopped.")
            await interaction.channel.send("⚠️ Emoji Decode has been forcefully stopped.")
        else:
            await interaction.response.send_message("❗ No Emoji Decode game running.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmojiDecode(bot))
