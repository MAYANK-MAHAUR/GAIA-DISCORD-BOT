import discord
from discord.ext import commands
from discord import app_commands, Interaction, TextChannel, AllowedMentions, Attachment, Webhook

ALLOWED_STAFF_ROLES = ["Admin", "Moderator"]

class EphemeralLanguageToggle(discord.ui.View):
    def __init__(self, english_message: str, hindi_message: str, showing_english: bool):
        super().__init__(timeout=180)
        self.english_message = english_message
        self.hindi_message = hindi_message
        self.showing_english = showing_english

        button_label = "See in Hindi" if self.showing_english else "See in English"
        toggle_button = discord.ui.Button(label=button_label, style=discord.ButtonStyle.secondary)
        toggle_button.callback = self.toggle_language
        self.add_item(toggle_button)

    async def toggle_language(self, interaction: Interaction):
        self.showing_english = not self.showing_english
        content = self.english_message if self.showing_english else self.hindi_message
        new_view = EphemeralLanguageToggle(self.english_message, self.hindi_message, self.showing_english)
        await interaction.response.edit_message(content=content, view=new_view)

class LanguageToggleButton(discord.ui.View):
    def __init__(self, english_message: str, hindi_message: str):
        super().__init__(timeout=None)
        self.english_message = english_message
        self.hindi_message = hindi_message if hindi_message.strip() else None

        start_toggle_button = discord.ui.Button(
            label="See in Hindi",
            style=discord.ButtonStyle.primary,
            custom_id="start_private_toggle"
        )
        if not self.hindi_message:
            start_toggle_button.disabled = True
            start_toggle_button.label = "No Hindi Available"
            start_toggle_button.style = discord.ButtonStyle.gray
        
        start_toggle_button.callback = self.start_ephemeral_toggle
        self.add_item(start_toggle_button)

    async def start_ephemeral_toggle(self, interaction: Interaction):
        if not self.hindi_message:
            await interaction.response.send_message("There is no Hindi translation available for this message.", ephemeral=True)
            return
            
        ephemeral_view = EphemeralLanguageToggle(
            english_message=self.english_message,
            hindi_message=self.hindi_message,
            showing_english=False
        )
        await interaction.response.send_message(
            content=self.hindi_message,
            view=ephemeral_view,
            ephemeral=True
        )

class MessageComposerModal(discord.ui.Modal, title="Send a Message as Bot"):
    def __init__(self, bot, target_channel: TextChannel, attached_file: Attachment = None, sender_info: dict = None):
        super().__init__(timeout=300)
        self.bot = bot
        self.target_channel = target_channel
        self.attached_file = attached_file
        self.sender_info = sender_info

        self.english_input = discord.ui.TextInput(
            label="Message (English)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True,
            placeholder="Type your message in English here..."
        )
        self.add_item(self.english_input)

        self.hindi_input = discord.ui.TextInput(
            label="Message (Hindi - Optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
            placeholder="Type the Hindi translation here (optional)..."
        )
        self.add_item(self.hindi_input)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        english_text = self.english_input.value
        hindi_text = self.hindi_input.value

        file_to_send = []
        if self.attached_file:
            try:
                discord_file_obj = await self.attached_file.to_file()
                file_to_send.append(discord_file_obj)
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to prepare file: {e}", ephemeral=True)
                return

        webhook = None
        try:
            webhooks = await self.target_channel.webhooks()
            for wh in webhooks:
                if wh.user == self.bot.user:
                    webhook = wh
                    break
            if not webhook:
                webhook = await self.target_channel.create_webhook(name="BotSenderWebhook")
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to manage webhooks in this channel.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred while managing webhooks: `{e}`", ephemeral=True)
            return

        username = self.sender_info.get("name", "Unknown User")
        avatar_url = self.sender_info.get("avatar_url", None)
        toggle_view = LanguageToggleButton(english_message=english_text, hindi_message=hindi_text)

        try:
            await webhook.send(
                content=english_text,
                files=file_to_send,
                username=username,
                avatar_url=avatar_url,
                allowed_mentions=AllowedMentions.none(),
                view=toggle_view
            )
            await interaction.followup.send(f"✅ Message sent to {self.target_channel.mention} as `{username}`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ An unexpected error occurred while sending: `{e}`", ephemeral=True)

class SendMessageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="send", description="Send a message as a user with an English/Hindi toggle.")
    @app_commands.describe(
        channel="The channel where the message will be sent.",
        file="An optional file to attach (image, PDF, etc.)."
    )
    async def send_message_command(self, interaction: Interaction, channel: TextChannel, file: Attachment = None):
        if not any(role.name in ALLOWED_STAFF_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        sender_info = {"name": interaction.user.display_name, "avatar_url": interaction.user.display_avatar.url}
        message_modal = MessageComposerModal(self.bot, target_channel=channel, attached_file=file, sender_info=sender_info)
        await interaction.response.send_modal(message_modal)

async def setup(bot):
    await bot.add_cog(SendMessageCog(bot))