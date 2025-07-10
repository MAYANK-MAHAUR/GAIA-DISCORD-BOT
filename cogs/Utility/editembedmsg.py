import discord
from discord.ext import commands
from discord import app_commands, Interaction, TextChannel, AllowedMentions, Embed, Colour
from discord.ui import Modal, TextInput, View, Button
import datetime
import uuid
import traceback

from cogs.Utility.embedmsg import (
    ALLOWED_ROLES,
    create_styled_embed,
    EphemeralLanguageToggle,
    LanguageToggleButton,
    EmbedComposerModal,
    COLOR_MAP_STATIC
)
import Data.database as database

class EditPreviewButtons(discord.ui.View):
    def __init__(self, original_interaction: Interaction, embed_modal_data: dict, public_embed: Embed, message_to_edit: discord.Message):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction
        self.embed_modal_data = embed_modal_data
        self.public_embed = public_embed
        self.message_to_edit = message_to_edit

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.original_interaction.user:
            await interaction.response.send_message("⚠️ You can't interact with these buttons.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Confirm & Edit", style=discord.ButtonStyle.success, custom_id="confirm_edit_embed")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        try:
            edited_embed_data = self.embed_modal_data
            message_id = self.message_to_edit.id

            hindi_embed_for_public_view = None
            if edited_embed_data.get('title_hi') or edited_embed_data.get('description_hi'):
                embed_color = COLOR_MAP_STATIC.get(
                    edited_embed_data.get('base_color', 'teal').lower(), discord.Color.teal()
                )
                
                original_db_data = await database.get_embed_data(message_id)
                sent_by_user_id = original_db_data['sent_by_user_id'] if original_db_data else interaction.user.id
                sent_at_iso = original_db_data['sent_at'] if original_db_data else discord.utils.utcnow().isoformat()
                
                sent_at_dt = None
                try:
                    sent_at_dt = datetime.datetime.fromisoformat(sent_at_iso)
                except ValueError:
                    sent_at_dt = discord.utils.utcnow()

                hindi_footer_text = f"द्वारा प्रेषित <@{sent_by_user_id}> | {discord.utils.format_dt(sent_at_dt, 'F')}"

                hindi_embed_for_public_view = create_styled_embed(
                    title=edited_embed_data['title_hi'] if edited_embed_data['title_hi'] else edited_embed_data['title_en'],
                    description=edited_embed_data['description_hi'] if edited_embed_data['description_hi'] else "अधिक जानकारी के लिए देखें।",
                    color=embed_color,
                    image_url=edited_embed_data['image_url'],
                    thumbnail_url=edited_embed_data['thumbnail_url'],
                    footer_text=hindi_footer_text
                )

            new_public_view = discord.ui.View()

            if hindi_embed_for_public_view:
                final_lang_toggle_button_instance = LanguageToggleButton(
                    english_embed=self.public_embed,
                    hindi_embed=hindi_embed_for_public_view,
                    message_id=message_id
                )
                if final_lang_toggle_button_instance.children:
                    new_public_view.add_item(final_lang_toggle_button_instance.children[0])

            if edited_embed_data.get('button1_label') and edited_embed_data.get('button1_url'):
                new_public_view.add_item(discord.ui.Button(label=edited_embed_data['button1_label'], url=edited_embed_data['button1_url'], style=discord.ButtonStyle.link))
            if edited_embed_data.get('button2_label') and edited_embed_data.get('button2_url'):
                new_public_view.add_item(discord.ui.Button(label=edited_embed_data['button2_label'], url=edited_embed_data['button2_url'], style=discord.ButtonStyle.link))

            await self.message_to_edit.edit(
                embed=self.public_embed,
                view=new_public_view,
                allowed_mentions=AllowedMentions.none()
            )

            button1_label, button1_url = None, None
            button2_label, button2_url = None, None
            for item in new_public_view.children:
                if isinstance(item, discord.ui.Button) and item.style == discord.ButtonStyle.link:
                    if not button1_label:
                        button1_label = item.label
                        button1_url = item.url
                    else:
                        button2_label = item.label
                        button2_url = item.url
                        break

            original_db_data = await database.get_embed_data(message_id)
            sent_by_user_id = original_db_data['sent_by_user_id'] if original_db_data else interaction.user.id
            sent_at = original_db_data['sent_at'] if original_db_data else discord.utils.utcnow().isoformat()

            await database.save_embed_data(
                message_id=message_id,
                channel_id=self.message_to_edit.channel.id,
                title_en=edited_embed_data['title_en'],
                description_en=edited_embed_data['description_en'],
                title_hi=edited_embed_data['title_hi'],
                description_hi=edited_embed_data['description_hi'],
                base_color=edited_embed_data['base_color'],
                image_url=edited_embed_data['image_url'],
                thumbnail_url=edited_embed_data['thumbnail_url'],
                button1_label=button1_label,
                button1_url=button1_url,
                button2_label=button2_label,
                button2_url=button2_url,
                sent_by_user_id=sent_by_user_id,
                sent_at=sent_at
            )

            await interaction.followup.send("✅ Embed successfully edited!", ephemeral=True)
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(content="Action completed.", embed=None, view=self)

        except Exception as e:
            print(f"An unexpected error occurred in EditPreviewButtons.confirm: {e}")
            traceback.print_exc()
            await interaction.followup.send("❌ An unexpected error occurred while editing. Please try again. Check console for details.", ephemeral=True)
            try:
                for item in self.children:
                    item.disabled = True
                await interaction.edit_original_response(content="❌ Failed to edit embed due to an unexpected error.", embed=None, view=self)
            except Exception:
                pass

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_edit_embed")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Canceled editing the embed.", embed=None, view=None)

class EditEmbedModal(discord.ui.Modal, title="Edit Existing Embed Message"):
    def __init__(self, message_to_edit: discord.Message, initial_data: dict):
        super().__init__(timeout=600)
        self.message_to_edit = message_to_edit
        self.initial_data = initial_data

        self.title_en = discord.ui.TextInput(
            label="Title (English)", style=discord.TextStyle.short, max_length=256, required=True,
            default=initial_data.get('title_en', '')
        )
        self.add_item(self.title_en)

        self.description_en = discord.ui.TextInput(
            label="Description (English)", style=discord.TextStyle.paragraph, max_length=4000, required=True,
            default=initial_data.get('description_en', '')
        )
        self.add_item(self.description_en)

        self.title_hi = discord.ui.TextInput(
            label="Title (Hindi - Optional)", style=discord.TextStyle.short, max_length=256, required=False,
            default=initial_data.get('title_hi', '')
        )
        self.add_item(self.title_hi)

        self.description_hi = discord.ui.TextInput(
            label="Description (Hindi - Optional)", style=discord.TextStyle.paragraph, max_length=4000, required=False,
            default=initial_data.get('description_hi', '')
        )
        self.add_item(self.description_hi)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            base_color_str = self.initial_data.get('base_color', 'teal')
            embed_color = COLOR_MAP_STATIC.get(base_color_str.lower(), discord.Color.teal())

            sent_by_user_id = self.initial_data.get('sent_by_user_id', interaction.user.id)
            sent_at_iso = self.initial_data.get('sent_at', discord.utils.utcnow().isoformat())

            sent_at_dt = None
            try:
                sent_at_dt = datetime.datetime.fromisoformat(sent_at_iso)
            except ValueError:
                sent_at_dt = discord.utils.utcnow()

            english_footer_text = f"Sent by <@{sent_by_user_id}> | {discord.utils.format_dt(sent_at_dt, 'F')}"

            english_embed = create_styled_embed(
                title=self.title_en.value,
                description=self.description_en.value,
                color=embed_color,
                image_url=self.initial_data.get('image_url'),
                thumbnail_url=self.initial_data.get('thumbnail_url'),
                footer_text=english_footer_text,
            )

            updated_embed_data = {
                'title_en': self.title_en.value,
                'description_en': self.description_en.value,
                'title_hi': self.title_hi.value,
                'description_hi': self.description_hi.value,
                'base_color': base_color_str,
                'image_url': self.initial_data.get('image_url'),
                'thumbnail_url': self.initial_data.get('thumbnail_url'),
                'button1_label': self.initial_data.get('button1_label'),
                'button1_url': self.initial_data.get('button1_url'),
                'button2_label': self.initial_data.get('button2_label'),
                'button2_url': self.initial_data.get('button2_url'),
                'footer_text': english_footer_text,
                'sent_by_user_id': sent_by_user_id,
                'sent_at': sent_at_iso
            }

            edit_preview_buttons_view = EditPreviewButtons(
                original_interaction=interaction,
                embed_modal_data=updated_embed_data,
                public_embed=english_embed,
                message_to_edit=self.message_to_edit
            )

            await interaction.followup.send(
                content="👀 Here is a preview of your **edited English** embed. Click 'Confirm & Edit' to update the message, or 'Cancel'.",
                embed=english_embed,
                view=edit_preview_buttons_view,
                ephemeral=True
            )

        except Exception as e:
            print(f"An unexpected error occurred in EditEmbedModal.on_submit: {e}")
            traceback.print_exc()
            await interaction.followup.send("❌ An unexpected error occurred while processing your edit. Please try again. Check console for details.", ephemeral=True)

class EmbedEditorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="edit_embed", description="Admin command to edit an existing multi-language embed message.")
    @app_commands.describe(
        message_id="The ID of the message containing the embed.",
        channel="The channel where the message is located."
    )
    @commands.has_any_role(*ALLOWED_ROLES)
    async def edit_embed(self, interaction: Interaction, message_id: str, channel: TextChannel):

        try:
            msg = await channel.fetch_message(int(message_id))
            
            if not msg.embeds:
                await interaction.response.send_message("❌ That message has no embeds to edit.", ephemeral=True)
                return

            db_data = await database.get_embed_data(msg.id)
            if not db_data:
                await interaction.response.send_message(
                    "❌ Could not find embed data in the database. This message might not have been sent by the `/sendembed` command or its data was deleted.",
                    ephemeral=True
                )
                return

            initial_data = {
                "title_en": db_data.get('title_en', ''),
                "description_en": db_data.get('description_en', ''),
                "title_hi": db_data.get('title_hi', ''),
                "description_hi": db_data.get('description_hi', ''),
                "base_color": db_data.get('base_color', 'teal'),
                "image_url": db_data.get('image_url', ''),
                "thumbnail_url": db_data.get('thumbnail_url', ''),
                "button1_label": db_data.get('button1_label'),
                "button1_url": db_data.get('button1_url'),
                "button2_label": db_data.get('button2_label'),
                "button2_url": db_data.get('button2_url'),
                "sent_by_user_id": db_data.get('sent_by_user_id'),
                "sent_at": db_data.get('sent_at')
            }

            modal = EditEmbedModal(message_to_edit=msg, initial_data=initial_data)
            await interaction.response.send_modal(modal)

        except discord.NotFound:
            await interaction.response.send_message("❌ Message not found. Make sure the ID and channel are correct.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to view that message.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid Message ID. Please provide a numeric ID.", ephemeral=True)
        except Exception as e:
            print(f"An unexpected error occurred in edit_embed command: {e}")
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An unexpected error occurred. Check console for details.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An unexpected error occurred. Check console for details.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmbedEditorCog(bot))