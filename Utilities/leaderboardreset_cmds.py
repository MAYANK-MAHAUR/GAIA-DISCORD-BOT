import discord
import Utilities
from discord.ext import commands
from discord import app_commands
from Utilities import Leaderboard, Sec_Leaderboard  

ALLOWED_ROLES = ["Game Master", "Moderator"]

class LeaderboardresetCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_allowed_role(self, interaction: discord.Interaction) -> bool:
        return any(role.name in ALLOWED_ROLES for role in interaction.user.roles)

    @app_commands.command(name="resetleaderboards", description="Reset both the final and secondary leaderboards.")
    async def reset_both_leaderboards(self, interaction: discord.Interaction):
        if not self.has_allowed_role(interaction):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        Leaderboard.reset_leaderboard()
        Sec_Leaderboard.reset_second_leaderboard()
        await interaction.response.send_message("✅ Both leaderboards (final and secondary) have been reset.", ephemeral=True)

    @app_commands.command(name="resetfinalleaderboard", description="Reset the final (main) leaderboard.")
    async def reset_final_leaderboard(self, interaction: discord.Interaction):
        if not self.has_allowed_role(interaction):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        Leaderboard.reset_leaderboard()
        await interaction.response.send_message("✅ Final leaderboard has been reset.", ephemeral=True)

    @app_commands.command(name="resetsecleaderboard", description="Reset the current secondary leaderboard.")
    async def reset_second_leaderboard(self, interaction: discord.Interaction):
        if not self.has_allowed_role(interaction):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        Sec_Leaderboard.reset_second_leaderboard()
        await interaction.response.send_message("✅ Secondary leaderboard has been reset.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(LeaderboardresetCommands(bot))
