import discord
from discord.ext import commands
from discord import app_commands, Interaction, TextChannel, AllowedMentions, Embed, Colour
from discord.ui import Modal, TextInput, View, Button

from cogs.Utility.embedmsg import (
    ALLOWED_ROLES,
    create_styled_embed,
    EphemeralLanguageToggle,
    LanguageToggleButton
)

class EditPreviewButtons(discord.ui.View):
    def __init__(self, original_interaction: Interaction, public_embed: Embed, public_view: discord.ui.View, message_to_edit: discord.Message):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction
        self.public_embed = public_embed
        self.public_view = public_view
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
            await self.message_to_edit.edit(
                embed=self.public_embed,
                view=self.public_view,
                allowed_mentions=AllowedMentions.none()
            )
            await interaction.followup.send("✅ Embed successfully edited!", ephemeral=True)
            for item in self.children:
                item.disabled = True
            await self.original_interaction.edit_original_response(content="✅ Embed successfully edited!", embed=None, view=self)
        except Exception as e:
            await interaction.followup.send(f"❌ An unexpected error occurred while editing: `{e}`", ephemeral=True)
            await self.original_interaction.edit_original_response(content=f"❌ Failed to edit embed: `{e}`", embed=None, view=None)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_edit_embed")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Canceled editing the embed.", embed=None, view=None)
        await self.original_interaction.edit_original_response(content="❌ Canceled editing the embed.", embed=None, view=None)

class EditEmbedModal(discord.ui.Modal, title="Edit Existing Embed Message"):
    def __init__(self, message_to_edit: discord.Message, initial_data: dict):
        super().__init__(timeout=600)
        self.message_to_edit = message_to_edit
        self.initial_data = initial_data

        self.color_map = {
            "cyan": discord.Color.teal(), "blue": discord.Color.blue(),
            "red": discord.Color.red(), "green": discord.Color.green(),
            "purple": discord.Color.purple(), "yellow": discord.Color.gold()
        }

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
            embed_color = Colour(self.initial_data.get('base_color_value', discord.Color.teal().value))

            english_embed = create_styled_embed(
                title=self.title_en.value,
                description=self.description_en.value,
                color=embed_color,
                image_url=self.initial_data.get('image_url'),
                thumbnail_url=self.initial_data.get('thumbnail_url'),
                footer_text=self.initial_data.get('footer_text'),
            )

            hindi_embed = None
            hindi_is_actually_available = False
            if self.title_hi.value or self.description_hi.value:
                hindi_is_actually_available = True
                hindi_embed = create_styled_embed(
                    title=self.title_hi.value if self.title_hi.value else self.title_en.value,
                    description=self.description_hi.value if self.description_hi.value else "अधिक जानकारी के लिए देखें।",
                    color=embed_color,
                    image_url=self.initial_data.get('image_url'),
                    thumbnail_url=self.initial_data.get('thumbnail_url'),
                    footer_text=self.initial_data.get('footer_text'),
                )

            public_view = discord.ui.View()
            if hindi_is_actually_available:
                public_view.add_item(LanguageToggleButton(english_embed=english_embed, hindi_embed=hindi_embed).children[0])

            if self.initial_data.get('button1_label') and self.initial_data.get('button1_url'):
                public_view.add_item(discord.ui.Button(label=self.initial_data['button1_label'], url=self.initial_data['button1_url'], style=discord.ButtonStyle.link))
            if self.initial_data.get('button2_label') and self.initial_data.get('button2_url'):
                public_view.add_item(discord.ui.Button(label=self.initial_data['button2_label'], url=self.initial_data['button2_url'], style=discord.ButtonStyle.link))


            edit_preview_buttons_view = EditPreviewButtons(
                original_interaction=interaction,
                public_embed=english_embed,
                public_view=public_view,
                message_to_edit=self.message_to_edit
            )

            await interaction.followup.send(
                content="👀 Here is a preview of your **edited English** embed. Click 'Confirm & Edit' to update the message, or 'Cancel'.",
                embed=english_embed,
                view=edit_preview_buttons_view,
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(f"❌ An unexpected error occurred while processing your edit: `{e}`", ephemeral=True)


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
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send("❌ That message has no embeds to edit.", ephemeral=True)
                return

            existing_embed = msg.embeds[0]

            initial_data = {
                "title_en": existing_embed.title or "",
                "description_en": existing_embed.description or "",
                "base_color_value": existing_embed.color.value,
                "image_url": existing_embed.image.url if existing_embed.image else "",
                "thumbnail_url": existing_embed.thumbnail.url if existing_embed.thumbnail else "",
                "footer_text": existing_embed.footer.text if existing_embed.footer else "",
                "title_hi": "",
                "description_hi": "",
                "button1_label": None,
                "button1_url": None,
                "button2_label": None,
                "button2_url": None,
            }

            if msg.components:
                button_count = 0
                for component_row in msg.components:
                    for component in component_row.children:
                        if isinstance(component, Button) and component.style == discord.ButtonStyle.link:
                            button_count += 1
                            if button_count == 1:
                                initial_data["button1_label"] = component.label
                                initial_data["button1_url"] = component.url
                            elif button_count == 2:
                                initial_data["button2_label"] = component.label
                                initial_data["button2_url"] = component.url

            modal = EditEmbedModal(message_to_edit=msg, initial_data=initial_data)
            await interaction.response.send_modal(modal)

        except discord.NotFound:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("❌ Message not found. Make sure the ID and channel are correct.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("❌ I don't have permission to view that message.", ephemeral=True)
async def setup(bot):
    await bot.add_cog(EmbedEditorCog(bot))