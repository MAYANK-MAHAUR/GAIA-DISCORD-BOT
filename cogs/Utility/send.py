import discord
from discord.ext import commands
from discord import app_commands, Interaction, TextChannel, AllowedMentions, Attachment, Webhook
import datetime
import uuid

import Data.database as database
from cogs.Utility.embedmsg import ALLOWED_ROLES

class EphemeralLanguageToggle(discord.ui.View):
    def __init__(self, english_message: str, hindi_message: str, showing_english: bool):
        super().__init__(timeout=180)
        self.english_message = english_message
        self.hindi_message = hindi_message
        self.showing_english = showing_english

        button_label = "See in Hindi" if self.showing_english else "See in English"
        toggle_button = discord.ui.Button(label=button_label, style=discord.ButtonStyle.secondary, custom_id="ephemeral_text_lang_toggle_button")
        toggle_button.callback = self.toggle_language
        self.add_item(toggle_button)

    async def toggle_language(self, interaction: Interaction):
        if interaction.message and interaction.message.interaction_metadata and interaction.user.id != interaction.message.interaction_metadata.user.id:
            await interaction.response.send_message("This ephemeral message is not for you.", ephemeral=True)
            return

        self.showing_english = not self.showing_english
        content = self.english_message if self.showing_english else self.hindi_message
        new_view = EphemeralLanguageToggle(self.english_message, self.hindi_message, self.showing_english)
        await interaction.response.edit_message(content=content, view=new_view)

class LanguageToggleButton(discord.ui.View):
    def __init__(self, english_message: str = None, hindi_message: str = None, associated_webhook_message_id: int = None):
        super().__init__(timeout=None)
        self._english_message_cache = english_message
        self._hindi_message_cache = hindi_message
        self.associated_webhook_message_id = associated_webhook_message_id

        self.hindi_available = (self._hindi_message_cache is not None and self._hindi_message_cache.strip() != "")

        custom_id_base = "multi_lang_text_toggle"
        if associated_webhook_message_id:
            actual_custom_id = f"{custom_id_base}_webhook_{associated_webhook_message_id}"
        else:
            actual_custom_id = f"{custom_id_base}_temp_{uuid.uuid4()}"

        start_toggle_button = discord.ui.Button(
            label="See in Hindi",
            style=discord.ButtonStyle.primary,
            custom_id=actual_custom_id
        )

        if not self.hindi_available:
            start_toggle_button.disabled = True
            start_toggle_button.label = "No Hindi Available"
            start_toggle_button.style = discord.ButtonStyle.gray
        
        start_toggle_button.callback = self.start_ephemeral_toggle
        self.add_item(start_toggle_button)

    async def start_ephemeral_toggle(self, interaction: Interaction):
        print(f"DEBUG: LanguageToggleButton clicked for custom_id: {interaction.data.get('custom_id')}")
        
        custom_id_parts = interaction.data.get('custom_id', '').split('_')
        if len(custom_id_parts) == 4 and custom_id_parts[2] == "webhook":
            associated_webhook_message_id = int(custom_id_parts[3])
            print(f"DEBUG: Extracted associated webhook message ID from custom_id: {associated_webhook_message_id}")
        else:
            associated_webhook_message_id = self.associated_webhook_message_id
            print(f"DEBUG: Falling back to cached associated webhook message ID: {associated_webhook_message_id}")

        if not associated_webhook_message_id:
            print("ERROR: No associated webhook message ID found for lookup.")
            await interaction.response.send_message(
                "❌ Error: Could not determine which message to translate. Please notify an admin.",
                ephemeral=True
            )
            return

        message_data = await database.get_text_message_data(associated_webhook_message_id)
        print(f"DEBUG: Database retrieval for associated_webhook_message_id {associated_webhook_message_id}: {message_data}")

        if not message_data:
            print(f"ERROR: No message data found in DB for plain text message ID: {associated_webhook_message_id}")
            await interaction.response.send_message(
                "❌ Error: Could not retrieve message data for translation. "
                "The original message might have been deleted or bot restarted without proper data reload. "
                "Please notify an admin.",
                ephemeral=True
            )
            return
        
        retrieved_english_message = message_data['english_content']
        retrieved_hindi_message = message_data['hindi_content']

        if not retrieved_hindi_message or retrieved_hindi_message.strip() == "":
            print(f"DEBUG: No Hindi content found for message ID: {associated_webhook_message_id}")
            await interaction.response.send_message("There is no Hindi translation available for this message.", ephemeral=True)
            return
            
        ephemeral_view = EphemeralLanguageToggle(
            english_message=retrieved_english_message,
            hindi_message=retrieved_hindi_message,
            showing_english=False
        )
        await interaction.response.send_message(
            content=ephemeral_view.hindi_message,
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
        hindi_text = self.hindi_input.value if self.hindi_input.value.strip() else None

        print(f"DEBUG: Modal submitted. English: '{english_text}', Hindi: '{hindi_text}'")

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
                if wh.user and wh.user.id == self.bot.user.id:
                    webhook = wh
                    print(f"DEBUG: Found existing bot-owned webhook: {webhook.id}")
                    break
            if not webhook:
                webhook = await self.target_channel.create_webhook(name=f"{self.bot.user.name}-Sender")
                print(f"DEBUG: Created new webhook: {webhook.id}")
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to manage webhooks (create/read) in this channel.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred while managing webhooks: `{e}`", ephemeral=True)
            print(f"ERROR: Webhook management error: {e}")
            return

        username = self.sender_info.get("name", "Unknown User")
        avatar_url = self.sender_info.get("avatar_url", None)
        
        webhook_message_object = None
        try:
            print(f"DEBUG: Attempting to send main message via webhook to channel {self.target_channel.id}...")
            await webhook.send(
                content=english_text,
                files=file_to_send,
                username=username,
                avatar_url=avatar_url,
                allowed_mentions=AllowedMentions.none()
            )
            print(f"DEBUG: Webhook send successful. Now trying to fetch webhook message ID.")

            await discord.utils.sleep_until(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=0.5))

            async for msg in self.target_channel.history(limit=5):
                if msg.webhook_id == webhook.id and msg.content == english_text: 
                    webhook_message_object = msg
                    print(f"DEBUG: Successfully retrieved webhook message with ID: {webhook_message_object.id}")
                    break
            
            if not webhook_message_object:
                print(f"WARNING: Could not find sent webhook message in channel history after send. Buttons will not work.")
                await interaction.followup.send(f"✅ Message sent to {self.target_channel.mention} as `{username}`, but could not confirm its ID. Translation buttons might not work.", ephemeral=True)
                return

            await database.save_text_message_data(
                message_id=webhook_message_object.id,
                channel_id=self.target_channel.id,
                english_content=english_text,
                hindi_content=hindi_text,
                sender_name=username,
                sender_avatar_url=avatar_url,
                sent_by_user_id=interaction.user.id,
                sent_at=discord.utils.utcnow().isoformat()
            )
            print(f"DEBUG: Webhook message data saved to DB for ID: {webhook_message_object.id}")

            button_holding_view = LanguageToggleButton(
                english_message=english_text,
                hindi_message=hindi_text,
                associated_webhook_message_id=webhook_message_object.id
            )
            
            print(f"DEBUG: Sending second message (button holder) as bot to channel {self.target_channel.id}...")
            bot_button_message = await self.target_channel.send(
                content=" ",
                view=button_holding_view,
                allowed_mentions=AllowedMentions.none()
            )
            print(f"DEBUG: Bot's button message sent with ID: {bot_button_message.id}")

            await interaction.followup.send(f"✅ Message sent to {self.target_channel.mention} as `{username}`. A separate button for translation has been added below it.", ephemeral=True)

        except Exception as e:
            print(f"ERROR: An unexpected error occurred during message sending or saving: {e}")
            await interaction.followup.send(f"❌ An unexpected error occurred while sending: `{e}`", ephemeral=True)

class SendMessageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Registering persistent views for plain messages from SendMessageCog...")
        await self.register_persistent_views()

    async def register_persistent_views(self):
        all_message_data = await database.get_all_text_message_data()
        if not all_message_data:
            print("No persistent plain messages found in database to register.")
            return

        for data in all_message_data:
            view = LanguageToggleButton(
                english_message=data['english_content'],
                hindi_message=data['hindi_content'],
                associated_webhook_message_id=data['message_id']
            )
            self.bot.add_view(view)
            print(f"Registered persistent view for webhook message ID: {data['message_id']}")

    @app_commands.command(name="send", description="Send a message with custom sender info and English/Hindi toggle.")
    @app_commands.describe(
        channel="The channel where the message will be sent.",
        file="An optional file to attach (image, PDF, etc.)."
    )
    @commands.has_any_role(*ALLOWED_ROLES)
    async def send_message_command(self, interaction: Interaction, channel: TextChannel, file: Attachment = None):
        sender_info = {"name": interaction.user.display_name, "avatar_url": interaction.user.display_avatar.url} 
        message_modal = MessageComposerModal(self.bot, target_channel=channel, attached_file=file, sender_info=sender_info)
        await interaction.response.send_modal(message_modal)

async def setup(bot):
    await database.initialize_text_message_db()
    await bot.add_cog(SendMessageCog(bot))