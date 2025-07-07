from discord import app_commands, Interaction, TextChannel, AllowedMentions, Attachment
from discord.ext import commands
import discord

ALLOWED_ROLE_NAMES = ["Admin", "Moderator"]

class MessageInputModal(discord.ui.Modal, title="Sends Message as Bot"):
    def __init__(self, bot, channel: TextChannel, file: Attachment = None):
        super().__init__(timeout=300)
        self.bot = bot
        self.channel = channel
        self.file = file

        self.message_input = discord.ui.TextInput(
            label="Message content (supports mentions etc.)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

        file = await self.file.to_file() if self.file else discord.utils.MISSING

        await self.channel.send(
            content=self.message_input.value,
            file=file,
            allowed_mentions=AllowedMentions.all()
        )

        await interaction.followup.send(f"✅ Message sent to {self.channel.mention}", ephemeral=True)

class SendAsBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="send", description="Send a message into selected channel as bot(with modal for formatting)")
    @app_commands.describe(
        channel="The channel to send the message to",
        file="Optional file to include (image, PDF, etc.)"
    )
    async def send(
        self,
        interaction: Interaction,
        channel: TextChannel,
        file: Attachment = None
    ):
        if not any(role.name in ALLOWED_ROLE_NAMES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        modal = MessageInputModal(self.bot, channel=channel, file=file)
        await interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(SendAsBot(bot))
