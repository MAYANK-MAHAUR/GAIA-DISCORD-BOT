import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="📚 Show all bot commands by category.")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 GAIA Bot Help Menu",
            description="Here's a list of commands grouped by category:",
            color=discord.Color.purple()
        )

        # 🎮 Games
        embed.add_field(
            name="🎮 Games",
            value=(
                "**/starttrivia** – Start trivia, answer questions and climb the leaderboard.\n"
                "**/stoptrivia** – Stop the trivia game manually.\n"
                "🔁 Use `/resetsecleaderboard` and `/resetfinalleaderboard` before and after each trivia or scramble game.\n\n"

                "**/startguess** – Start a number guessing game.\n"
                "**/stopguess** – Stop the guessing game manually.\n"
                "🔁 Use `/resetsecleaderboard` and `/resetfinalleaderboard`\n\n"

                "**/scramble** – Unscramble the word. First to solve wins.\n"
                "**/stop_scramble** – Stop the scramble game manually.\n"
                "🔁 Use `/resetsecleaderboard` and `/resetfinalleaderboard`\n\n"

                "**/rps [choice]** – Rock Paper Scissors. First to counter wins.\n"
                "🔁 Use `/resetsecleaderboard` and `/resetfinalleaderboard`\n\n"
            ),
            inline=False
        )

        # 🛡️ Moderation
        embed.add_field(
            name="🛡️ Moderation",
            value=(
                "**!kick @user [reason]** – Kick a member.\n"
                "**!ban @user [reason]** – Ban a member.\n"
                "**!warn @user [reason]** – Warn a member (3 = auto-ban).\n"
                "**!checkwarn @user** – Show user warnings.\n"
                "**!mute @user [reason]** – Mute a user.\n"
                "**!unmute @user** – Unmute a user.\n"
                "**!purge [number]** – Delete messages.\n"
                "**!unban [user#1234 or ID]** – Unban a user.\n"
                "**!slowmode [seconds]** – Set message cooldown.\n"
                "**!lock** – Lock current channel.\n"
                "**!unlock** – Unlock channel.\n"
                "**!changenick @user [nickname]** – Change/reset nickname.\n"
                "**!role @user @role** – Add or remove a role.\n\n"
            ),
            inline=False
        )

        # ⚙️ Utility
        embed.add_field(
            name="⚙️ Utility",
            value=(
                "**/help** – Show this help message.\n"
                "**!hello** – Test if the bot is online.\n\n"
            ),
            inline=False
        )

        embed.set_footer(text="Use `/` for slash commands and `!` for moderation commands.")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Help(bot))
