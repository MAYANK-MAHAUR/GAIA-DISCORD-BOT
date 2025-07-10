import discord
from discord.ext import commands
from discord import app_commands, Interaction, TextChannel, AllowedMentions, Embed, Colour
import datetime
import Data.database as database
import uuid


COLOR_MAP_STATIC = {
    "cyan": discord.Colour.teal(), # Here's where Colour is used
    "blue": discord.Colour.blue(),
    "red": discord.Colour.red(),
    "green": discord.Colour.green(),
    "purple": discord.Colour.purple(),
    "yellow": discord.Colour.gold()
}

ALLOWED_ROLES = ["Admin", "Moderator"]

def create_styled_embed(
    title: str,
    description: str,
    color: Colour,
    image_url: str = None,
    thumbnail_url: str = None,
    footer_text: str = None,
) -> Embed:
    embed = Embed(title=title, color=color)
    if description:
        embed.description = description
    if image_url:
        embed.set_image(url=image_url)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if footer_text:
        embed.set_footer(text=footer_text)
    return embed

class EphemeralLanguageToggle(discord.ui.View):
    def __init__(self, english_embed: Embed, hindi_embed: Embed, showing_english: bool):
        super().__init__(timeout=180)
        self.english_embed = english_embed
        self.hindi_embed = hindi_embed
        self.showing_english = showing_english

        button_label = "See in Hindi" if self.showing_english else "See in English"
        toggle_button = discord.ui.Button(label=button_label, style=discord.ButtonStyle.secondary, custom_id="ephemeral_lang_toggle_button")
        toggle_button.callback = self.toggle_language
        self.add_item(toggle_button)

    async def toggle_language(self, interaction: Interaction):
        if interaction.message and interaction.message.interaction_metadata and interaction.user.id != interaction.message.interaction_metadata.user.id:
            await interaction.response.send_message("This ephemeral message is not for you.", ephemeral=True)
            return

        self.showing_english = not self.showing_english
        embed = self.english_embed if self.showing_english else self.hindi_embed

        new_view = EphemeralLanguageToggle(
            self.english_embed, self.hindi_embed, self.showing_english
        )

        await interaction.response.edit_message(embed=embed, view=new_view)

class LanguageToggleButton(discord.ui.View):
    def __init__(self, english_embed: Embed, hindi_embed: Embed, message_id: int = None):
        super().__init__(timeout=None)
        self.english_embed = english_embed
        self.hindi_embed = hindi_embed
        self.message_id = message_id

        self.hindi_available = (hindi_embed is not None and \
                                (hindi_embed.title or hindi_embed.description))

        custom_id_base = "multi_lang_toggle"
        if message_id:
            actual_custom_id = f"{custom_id_base}_{message_id}"
        else:
            actual_custom_id = f"{custom_id_base}_{uuid.uuid4()}"

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
        msg_id_from_interaction = interaction.message.id if interaction.message else self.message_id

        embed_data = None
        if msg_id_from_interaction:
            embed_data = await database.get_embed_data(msg_id_from_interaction)

        if not embed_data:
            await interaction.response.send_message(
                "❌ Error: Could not retrieve message data for translation. "
                "The original message might have been deleted or bot restarted without proper data reload. "
                "Please notify an admin.",
                ephemeral=True
            )
            return

        embed_color = COLOR_MAP_STATIC.get(embed_data['base_color'].lower(), discord.Color.teal())

        sent_at_dt = None
        if embed_data.get('sent_at'):
            try:
                sent_at_dt = datetime.datetime.fromisoformat(embed_data['sent_at'])
            except ValueError:
                pass

        footer_timestamp = discord.utils.utcnow() if sent_at_dt is None else sent_at_dt

        english_footer_text = f"Sent by <@{embed_data['sent_by_user_id']}> | {discord.utils.format_dt(footer_timestamp, 'F')}"
        hindi_footer_text = f"द्वारा प्रेषित <@{embed_data['sent_by_user_id']}> | {discord.utils.format_dt(footer_timestamp, 'F')}"

        retrieved_english_embed = create_styled_embed(
            title=embed_data['title_en'],
            description=embed_data['description_en'],
            color=embed_color,
            image_url=embed_data['image_url'],
            thumbnail_url=embed_data['thumbnail_url'],
            footer_text=english_footer_text
        )

        retrieved_hindi_embed = None
        if embed_data['title_hi'] or embed_data['description_hi']:
            retrieved_hindi_embed = create_styled_embed(
                title=embed_data['title_hi'] if embed_data['title_hi'] else embed_data['title_en'],
                description=embed_data['description_hi'] if embed_data['description_hi'] else "अधिक जानकारी के लिए देखें।",
                color=embed_color,
                image_url=embed_data['image_url'],
                thumbnail_url=embed_data['thumbnail_url'],
                footer_text=hindi_footer_text
            )
        else:
            await interaction.response.send_message("There is no Hindi translation available for this message.", ephemeral=True)
            return

        ephemeral_view = EphemeralLanguageToggle(
            english_embed=retrieved_english_embed,
            hindi_embed=retrieved_hindi_embed,
            showing_english=False
        )
        await interaction.response.send_message(
            embed=ephemeral_view.hindi_embed,
            view=ephemeral_view,
            ephemeral=True
        )

class PreviewButtons(discord.ui.View):
    def __init__(self, original_interaction: Interaction, public_embed: Embed, embed_modal_data: dict, target_channel: TextChannel,
                 message_to_edit: discord.Message = None):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction
        self.public_embed = public_embed
        self.embed_modal_data = embed_modal_data
        self.target_channel = target_channel
        self.message_to_edit = message_to_edit

        if self.message_to_edit:
            self.confirm = discord.ui.Button(label="✅ Confirm & Update", style=discord.ButtonStyle.success, custom_id="confirm_update_embed")
        else:
            self.confirm = discord.ui.Button(label="✅ Confirm & Send", style=discord.ButtonStyle.success, custom_id="confirm_send_embed")
        self.confirm.callback = self.confirm_callback
        self.add_item(self.confirm)

        self.cancel_button = discord.ui.Button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_embed")
        self.cancel_button.callback = self.cancel_callback
        self.add_item(self.cancel_button)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.original_interaction.user:
            await interaction.response.send_message("⚠️ You can't interact with these buttons as you are not the original sender.", ephemeral=True)
            return False
        return True

    async def confirm_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            temp_public_view = discord.ui.View()
            temp_lang_button_available = False
            hindi_embed_for_public_view = None

            if self.embed_modal_data['title_hi'] or self.embed_modal_data['description_hi']:
                temp_lang_button_available = True
                embed_color = COLOR_MAP_STATIC.get(self.embed_modal_data['base_color'].lower(), discord.Color.teal())
                hindi_embed_for_public_view = create_styled_embed(
                    title=self.embed_modal_data['title_hi'] if self.embed_modal_data['title_hi'] else self.embed_modal_data['title_en'],
                    description=self.embed_modal_data['description_hi'] if self.embed_modal_data['description_hi'] else "अधिक जानकारी के लिए देखें।",
                    color=embed_color,
                    image_url=self.embed_modal_data['image_url'],
                    thumbnail_url=self.embed_modal_data['thumbnail_url'],
                    footer_text=f"द्वारा प्रेषित {self.original_interaction.user.display_name} | {discord.utils.format_dt(discord.utils.utcnow(), 'F')}"
                )
                temp_public_view.add_item(LanguageToggleButton(
                    english_embed=self.public_embed,
                    hindi_embed=hindi_embed_for_public_view
                ).children[0])

            if self.embed_modal_data['button1_label'] and self.embed_modal_data['button1_url']:
                temp_public_view.add_item(discord.ui.Button(label=self.embed_modal_data['button1_label'], url=self.embed_modal_data['button1_url'], style=discord.ButtonStyle.link))
            if self.embed_modal_data['button2_label'] and self.embed_modal_data['button2_url']:
                temp_public_view.add_item(discord.ui.Button(label=self.embed_modal_data['button2_label'], url=self.embed_modal_data['button2_url'], style=discord.ButtonStyle.link))

            if self.message_to_edit:
                message = self.message_to_edit
                await message.edit(
                    embed=self.public_embed,
                    view=temp_public_view,
                    allowed_mentions=AllowedMentions.none()
                )
            else:
                message = await self.target_channel.send(
                    embed=self.public_embed,
                    view=temp_public_view,
                    allowed_mentions=AllowedMentions.none()
                )

            final_public_view = discord.ui.View()

            if temp_lang_button_available:
                final_lang_toggle_view_instance = LanguageToggleButton(
                    english_embed=self.public_embed,
                    hindi_embed=hindi_embed_for_public_view,
                    message_id=message.id
                )
                final_public_view.add_item(final_lang_toggle_view_instance.children[0])

            if self.embed_modal_data['button1_label'] and self.embed_modal_data['button1_url']:
                final_public_view.add_item(discord.ui.Button(label=self.embed_modal_data['button1_label'], url=self.embed_modal_data['button1_url'], style=discord.ButtonStyle.link))
            if self.embed_modal_data['button2_label'] and self.embed_modal_data['button2_url']:
                final_public_view.add_item(discord.ui.Button(label=self.embed_modal_data['button2_label'], url=self.embed_modal_data['button2_url'], style=discord.ButtonStyle.link))

            await message.edit(view=final_public_view)

            button1_label, button1_url = None, None
            button2_label, button2_url = None, None
            for item in final_public_view.children:
                if isinstance(item, discord.ui.Button) and item.style == discord.ButtonStyle.link:
                    if not button1_label:
                        button1_label = item.label
                        button1_url = item.url
                    else:
                        button2_label = item.label
                        button2_url = item.url

            await database.save_embed_data(
                message_id=message.id,
                channel_id=self.target_channel.id,
                title_en=self.embed_modal_data['title_en'],
                description_en=self.embed_modal_data['description_en'],
                title_hi=self.embed_modal_data['title_hi'],
                description_hi=self.embed_modal_data['description_hi'],
                base_color=self.embed_modal_data['base_color'],
                image_url=self.embed_modal_data['image_url'],
                thumbnail_url=self.embed_modal_data['thumbnail_url'],
                button1_label=button1_label,
                button1_url=button1_url,
                button2_label=button2_label,
                button2_url=button2_url,
                sent_by_user_id=self.original_interaction.user.id,
                sent_at=discord.utils.utcnow().isoformat()
            )

            feedback_message = "✅ Embed successfully sent!" if not self.message_to_edit else "✅ Embed successfully updated!"
            # Use followup.send for a new ephemeral message
            await interaction.followup.send(feedback_message, ephemeral=True)
            
            # Disable buttons on the original ephemeral preview message
            for item in self.children:
                item.disabled = True
            try:
                # Attempt to edit the original interaction response to disable buttons,
                # but wrap it in a try-except to catch if it's already gone.
                await self.original_interaction.edit_original_response(content="Action completed.", view=self)
            except discord.NotFound:
                pass # Silently ignore if the original ephemeral message is already gone.
            except Exception as e:
                print(f"Warning: Could not edit original ephemeral response (likely disappeared): {e}")

        except Exception as e:
            print(f"Error in confirm: {e}")
            await interaction.followup.send(f"❌ Error while sending/updating: `{e}`", ephemeral=True)
            # Original interaction might be gone here too, but this is the primary error feedback
            try:
                await self.original_interaction.edit_original_response(content=f"❌ Failed to process embed: `{e}`", embed=None, view=None)
            except discord.NotFound:
                pass
            except Exception as edit_err:
                print(f"Error editing original interaction response after failure: {edit_err}")


    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="❌ Canceled sending the embed.", embed=None, view=None)
        # Attempt to edit the original interaction response to update its state
        try:
            await self.original_interaction.edit_original_response(content="❌ Canceled sending the embed.", embed=None, view=None)
        except discord.NotFound:
            pass # Silently ignore if the original ephemeral message is already gone.
        except Exception as e:
            print(f"Warning: Could not edit original ephemeral response (likely disappeared) during cancel: {e}")


class EmbedComposerModal(discord.ui.Modal, title="Compose Embed Message"):
    def __init__(self, target_channel: TextChannel, base_color: str, image_url: str = None, thumbnail_url: str = None,
                 button1_label: str = None, button1_url: str = None, button2_label: str = None, button2_url: str = None,
                 message_to_edit: discord.Message = None):
        super().__init__(timeout=600)
        self.target_channel = target_channel
        self.base_color_str = base_color
        self.image_url = image_url
        self.thumbnail_url = thumbnail_url
        self.button1_label = button1_label
        self.button1_url = button1_url
        self.button2_label = button2_label
        self.button2_url = button2_url
        self.message_to_edit = message_to_edit

        self.title_en = discord.ui.TextInput(
            label="Title (English)", style=discord.TextStyle.short, max_length=256, required=True
        )
        self.add_item(self.title_en)

        self.description_en = discord.ui.TextInput(
            label="Description (English)", style=discord.TextStyle.paragraph, max_length=4000, required=True
        )
        self.add_item(self.description_en)

        self.title_hi = discord.ui.TextInput(
            label="Title (Hindi - Optional)", style=discord.TextStyle.short, max_length=256, required=False
        )
        self.add_item(self.title_hi)

        self.description_hi = discord.ui.TextInput(
            label="Description (Hindi - Optional)", style=discord.TextStyle.paragraph, max_length=4000, required=False
        )
        self.add_item(self.description_hi)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        embed_color = COLOR_MAP_STATIC.get(self.base_color_str.lower(), discord.Color.teal())

        embed_modal_data = {
            'title_en': self.title_en.value,
            'description_en': self.description_en.value,
            'title_hi': self.title_hi.value,
            'description_hi': self.description_hi.value,
            'base_color': self.base_color_str,
            'image_url': self.image_url,
            'thumbnail_url': self.thumbnail_url,
            'button1_label': self.button1_label,
            'button1_url': self.button1_url,
            'button2_label': self.button2_label,
            'button2_url': self.button2_url,
        }

        english_embed = create_styled_embed(
            title=self.title_en.value,
            description=self.description_en.value,
            color=embed_color,
            image_url=self.image_url,
            thumbnail_url=self.thumbnail_url,
            footer_text=f"Sent by {interaction.user.display_name} | {discord.utils.format_dt(discord.utils.utcnow(), 'F')}"
        )

        hindi_embed_for_preview = None
        hindi_is_actually_available = False

        if self.title_hi.value or self.description_hi.value:
            hindi_is_actually_available = True
            hindi_embed_for_preview = create_styled_embed(
                title=self.title_hi.value if self.title_hi.value else self.title_en.value,
                description=self.description_hi.value if self.description_hi.value else "अधिक जानकारी के लिए देखें।",
                color=embed_color,
                image_url=self.image_url,
                thumbnail_url=self.thumbnail_url,
                footer_text=f"द्वारा प्रेषित {interaction.user.display_name} | {discord.utils.format_dt(discord.utils.utcnow(), 'F')}"
            )

        preview_buttons_view = PreviewButtons(
            original_interaction=interaction,
            public_embed=english_embed,
            embed_modal_data=embed_modal_data,
            target_channel=self.target_channel,
            message_to_edit=self.message_to_edit
        )

        content_message = "👀 Here is a preview of your **English** embed. Click 'Confirm & Send' to post it to the channel, or 'Cancel'."
        if self.message_to_edit:
            content_message = "👀 Here is a preview of your **edited English** embed. Click 'Confirm & Update' to apply changes, or 'Cancel'."

        await interaction.followup.send(
            content=content_message,
            embed=english_embed,
            view=preview_buttons_view,
            ephemeral=True
        )

class EmbedMsgCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Registering persistent views from EmbedMsgCog...")
        await self.register_persistent_views()

    async def register_persistent_views(self):
        all_embed_data = await database.get_all_embed_data()
        if not all_embed_data:
            print("No persistent embeds found in database to register.")
            return

        for data in all_embed_data:
            embed_color = COLOR_MAP_STATIC.get(data['base_color'].lower(), discord.Color.teal())

            sent_at_dt = None
            if data.get('sent_at'):
                try:
                    sent_at_dt = datetime.datetime.fromisoformat(data['sent_at'])
                except ValueError:
                    print(f"Warning: Could not parse sent_at for message {data['message_id']}: {data['sent_at']}")
                    pass

            footer_timestamp = discord.utils.utcnow() if sent_at_dt is None else sent_at_dt

            english_footer_text = f"Sent by <@{data['sent_by_user_id']}> | {discord.utils.format_dt(footer_timestamp, 'F')}"
            hindi_footer_text = f"द्वारा प्रेषित <@{data['sent_by_user_id']}> | {discord.utils.format_dt(footer_timestamp, 'F')}"

            english_embed = create_styled_embed(
                title=data['title_en'],
                description=data['description_en'],
                color=embed_color,
                image_url=data['image_url'],
                thumbnail_url=data['thumbnail_url'],
                footer_text=english_footer_text
            )

            hindi_embed = None
            if data['title_hi'] or data['description_hi']:
                hindi_embed = create_styled_embed(
                    title=data['title_hi'] if data['title_hi'] else data['title_en'],
                    description=data['description_hi'] if data['description_hi'] else "अधिक जानकारी के लिए देखें।",
                    color=embed_color,
                    image_url=data['image_url'],
                    thumbnail_url=data['thumbnail_url'],
                    footer_text=hindi_footer_text
                )
            else:
                continue

            view = LanguageToggleButton(english_embed=english_embed, hindi_embed=hindi_embed, message_id=data['message_id'])

            self.bot.add_view(view)
            print(f"Registered persistent view for message ID: {data['message_id']}")

    @app_commands.command(name="sendembed", description="Send a custom embed with multi-language support & preview")
    @app_commands.describe(
        channel="The channel where the embed will be sent.",
        color="The embed color (cyan, blue, red, green, purple, yellow).",
        image_url="Image URL (optional)",
        thumbnail_url="Thumbnail URL (optional)",
        button1_label="Button 1 label (optional)",
        button1_url="Button 1 URL (optional)",
        button2_label="Button 2 label (optional)",
        button2_url="Button 2 URL (optional)"
    )
    @commands.has_any_role(*ALLOWED_ROLES)
    async def sendembed(
        self,
        interaction: Interaction,
        channel: TextChannel,
        color: str,
        image_url: str = None,
        thumbnail_url: str = None,
        button1_label: str = None,
        button1_url: str = None,
        button2_label: str = None,
        button2_url: str = None
    ):
        modal = EmbedComposerModal(
            target_channel=channel,
            base_color=color,
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            button1_label=button1_label,
            button1_url=button1_url,
            button2_label=button2_label,
            button2_url=button2_url
        )
        await interaction.response.send_modal(modal)

async def setup(bot):
    await database.init_database_module()
    await bot.add_cog(EmbedMsgCog(bot))