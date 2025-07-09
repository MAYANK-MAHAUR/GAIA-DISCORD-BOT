import discord
from discord.ext import commands
from discord import app_commands

ALLOWED_ROLES = ["Game Master", "Moderator"]

class LeaderboardresetCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leaderboard_cog = None

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.leaderboard_cog = self.bot.get_cog('Leaderboard')
        if self.leaderboard_cog:
            print("Leaderboard cog found and linked to LeaderboardresetCommands cog.")
        else:
            print("WARNING: Leaderboard cog not found. Reset commands will not work.")

    def has_allowed_role(self, interaction: discord.Interaction) -> bool:
        return any(role.name in ALLOWED_ROLES for role in interaction.user.roles)

    @app_commands.command(name="resetleaderboard", description="Reset both the final and secondary leaderboards.")
    async def reset_both_leaderboards(self, interaction: discord.Interaction):
        if not self.has_allowed_role(interaction):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if not self.leaderboard_cog:
            await interaction.response.send_message("❌ Leaderboard system is not available. Cannot reset.", ephemeral=True)
            return

        self.leaderboard_cog.reset_leaderboard()
        
        await interaction.response.send_message("✅ Both leaderboards (recent winners and final, if applicable) have been reset.", ephemeral=True)

        lb_channel = self.bot.get_channel(self.leaderboard_cog.LEADERBOARD_CHANNEL_ID)
        if lb_channel:
            await self.leaderboard_cog.update_leaderboard_display(lb_channel)
        else:
            print(f"WARNING: Leaderboard channel (ID: {self.leaderboard_cog.LEADERBOARD_CHANNEL_ID}) not found for display update after reset.")


async def setup(bot):
    await bot.add_cog(LeaderboardresetCommands(bot))