import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from Utilities import Leaderboard

ALLOWED_ROLES = ["Game Master", "Moderator"]
RPS_CHOICES = ["rock", "paper", "scissor"]
LEADERBOARD_CHANNEL_ID = 1379347453462970519

class RPS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_rps = {}

    @app_commands.command(name="rps", description="Start a quick Rock Paper Scissors match")
    @app_commands.describe(choice="Choose Rock, Paper, or Scissors")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Rock", value="rock"),
        app_commands.Choice(name="Paper", value="paper"),
        app_commands.Choice(name="Scissors", value="scissor")
    ])
    async def rps(self, interaction: discord.Interaction, choice: app_commands.Choice[str]):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id in self.active_rps:
            await interaction.response.send_message("❗ An RPS game is already running in this channel.", ephemeral=True)
            return

        host_choice = choice.value
        counter_move = {
            "rock": "paper",
            "paper": "scissor",
            "scissor": "rock"
        }[host_choice]

        self.active_rps[interaction.channel.id] = True

        # Send embed that game has started
        start_embed = discord.Embed(
            title="🎮 Rock Paper Scissors Started!",
            description=(
                f"{interaction.user.mention} has picked their move!\n"
                f"🔒 Channel is locked for 10 seconds...\n\n"
                f"Be ready to type the **winning counter move** when it unlocks!"
            ),
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=start_embed)

        # Lock channel
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await asyncio.sleep(10)

        # Unlock channel
        overwrite.send_messages = True
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        unlock_embed = discord.Embed(
            title="🔓 Channel Unlocked!",
            description=f"First one to type the **winning counter move** wins!",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=unlock_embed)

        def check(m):
            msg_content = m.content.strip().lower()
            valid_inputs = [counter_move]
            if counter_move == "scissor":
                valid_inputs.append("scissors")

            return (
                m.channel == interaction.channel and
                not m.author.bot and
                msg_content in valid_inputs and
                not any(str(w["user_id"]) == str(m.author.id) for w in Leaderboard.get_recent_winners())
            )

        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            await msg.add_reaction("🎉")

            # Add to leaderboard
            Leaderboard.add_recent_winner(
                user_id=msg.author.id,
                username=msg.author.name,
                game_name="RPS",
                host_id=interaction.user.id,
                host_name=interaction.user.name
            )

            win_embed = discord.Embed(
                title="🏆 We Have a Winner!",
                description=f"{msg.author.mention} correctly typed **{counter_move.upper()}** first!",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=win_embed)

            # Show updated leaderboard
            leaderboard = Leaderboard.get_recent_winners()
            leaderboard_text = ""
            for i, entry in enumerate(leaderboard, start=1):
                leaderboard_text += (
                    f"**{i}.** {entry['username']} | `{entry['game_name']}` | "
                    f"Host: {entry['host_name']} | *{entry['timestamp']}*\n"
                )

            lb_embed = discord.Embed(
                title="📋 Leaderboard",
                description=leaderboard_text or "No winners yet.",
                color=discord.Color.blue()
            )

            last_id = Leaderboard.get_last_leaderboard(interaction.channel.id)
            if last_id:
                try:
                    prev_msg = await interaction.channel.fetch_message(last_id)
                    await prev_msg.delete()
                except discord.NotFound:
                    pass

            leaderboard_msg = await interaction.followup.send(embed=lb_embed)
            Leaderboard.set_last_leaderboard(interaction.channel.id, leaderboard_msg.id)

            # If full, send to leaderboard channel and reset
            if Leaderboard.is_leaderboard_full():
                leaderboard_channel = self.bot.get_channel(LEADERBOARD_CHANNEL_ID)
                if leaderboard_channel:
                    await leaderboard_channel.send(embed=lb_embed)
                    await interaction.channel.send(embed=lb_embed)
                Leaderboard.reset_leaderboard()

        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⌛ Time's Up!",
                description=f"No one responded in time. The winning move was **{counter_move.upper()}**.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=timeout_embed)

        finally:
            self.active_rps.pop(interaction.channel.id, None)

async def setup(bot):
    await bot.add_cog(RPS(bot))
