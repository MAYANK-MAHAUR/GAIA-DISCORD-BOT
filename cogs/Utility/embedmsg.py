import discord
from discord.ext import commands
from discord import app_commands, Interaction, TextChannel, AllowedMentions, Embed, Colour

ALLOWED_ROLES = ["Admin", "Moderator"]

def create_styled_embed(
    title: str,
    description: str,
    color: Colour,
    image_url: str = None,
    thumbnail_url: str = None,
    footer_text: str = None,
    fields_data: list = None
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
    if fields_data:
        for name, value, inline in fields_data:
            if name and value:
                embed.add_field(name=name, value=value, inline=inline)
    return embed

class EphemeralLanguageToggle(discord.ui.View):
    def __init__(self, english_embed: Embed, hindi_embed: Embed, showing_english: bool):
        super().__init__(timeout=180)
        self.english_embed = english_embed
        self.hindi_embed = hindi_embed
        self.showing_english = showing_english

        button_label = "See in Hindi" if self.showing_english else "See in English"
        toggle_button = discord.ui.Button(label=button_label, style=discord.ButtonStyle.secondary)
        toggle_button.callback = self.toggle_language
        self.add_item(toggle_button)

    async def toggle_language(self, interaction: Interaction):
        self.showing_english = not self.showing_english
        embed = self.english_embed if self.showing_english else self.hindi_embed

        new_view = EphemeralLanguageToggle(
            self.english_embed, self.hindi_embed, self.showing_english
        )

        await interaction.response.edit_message(embed=embed, view=new_view)

class LanguageToggleButton(discord.ui.View):
    def __init__(self, english_embed: Embed, hindi_embed: Embed):
        super().__init__(timeout=None)
        self.english_embed = english_embed
        self.hindi_embed = hindi_embed

        self.hindi_available = (hindi_embed is not None and \
                                (hindi_embed.title or hindi_embed.description or hindi_embed.fields))

        start_toggle_button = discord.ui.Button(
            label="See in Hindi",
            style=discord.ButtonStyle.primary,
            custom_id="start_private_toggle"
        )

        if not self.hindi_available:
            start_toggle_button.disabled = True
            start_toggle_button.label = "No Hindi Available"
            start_toggle_button.style = discord.ButtonStyle.gray

        start_toggle_button.callback = self.start_ephemeral_toggle
        self.add_item(start_toggle_button)

    async def start_ephemeral_toggle(self, interaction: Interaction):
        if not self.hindi_available:
            await interaction.response.send_message("There is no Hindi translation available for this message.", ephemeral=True)
            return

        ephemeral_view = EphemeralLanguageToggle(
            english_embed=self.hindi_embed,
            hindi_embed=self.english_embed,
            showing_english=False
        )
        await interaction.response.send_message(
            embed=ephemeral_view.english_embed,
            view=ephemeral_view,
            ephemeral=True
        )

class PreviewButtons(discord.ui.View):
    def __init__(self, original_interaction: Interaction, public_embed: Embed, public_view: discord.ui.View, target_channel: TextChannel):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction
        self.public_embed = public_embed
        self.public_view = public_view
        self.target_channel = target_channel

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.original_interaction.user:
            await interaction.response.send_message("⚠️ You can't interact with these buttons.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Confirm & Send", style=discord.ButtonStyle.success, custom_id="confirm_send_embed")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        try:
            await self.target_channel.send(
                embed=self.public_embed,
                view=self.public_view,
                allowed_mentions=AllowedMentions.none()
            )
            await interaction.followup.send("✅ Embed successfully sent!", ephemeral=False)
            for item in self.children:
                item.disabled = True
            await self.original_interaction.edit_original_response(content="✅ Embed successfully sent!", embed=None, view=self)
        except Exception as e:
            await interaction.followup.send(f"❌ An unexpected error occurred while sending: `{e}`", ephemeral=True)
            await self.original_interaction.edit_original_response(content=f"❌ Failed to send embed: `{e}`", embed=None, view=None)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_embed")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Canceled sending the embed.", embed=None, view=None)
        await self.original_interaction.edit_original_response(content="❌ Canceled sending the embed.", embed=None, view=None)

class EmbedComposerModal(discord.ui.Modal, title="Compose Embed Message"):
    def __init__(self, target_channel: TextChannel, base_color: str, image_url: str = None, thumbnail_url: str = None,
                 button1_label: str = None, button1_url: str = None, button2_label: str = None, button2_url: str = None):
        super().__init__(timeout=600)
        self.target_channel = target_channel
        self.base_color_str = base_color
        self.image_url = image_url
        self.thumbnail_url = thumbnail_url
        self.button1_label = button1_label
        self.button1_url = button1_url
        self.button2_label = button2_label
        self.button2_url = button2_url

        self.color_map = {
            "cyan": discord.Color.teal(),
            "blue": discord.Color.blue(),
            "red": discord.Color.red(),
            "green": discord.Color.green(),
            "purple": discord.Color.purple(),
            "yellow": discord.Color.gold()
        }

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
        embed_color = self.color_map.get(self.base_color_str.lower(), discord.Color.teal())

        english_embed = create_styled_embed(
            title=self.title_en.value,
            description=self.description_en.value,
            color=embed_color,
            image_url=self.image_url,
            thumbnail_url=self.thumbnail_url,
            footer_text=f"Sent by {interaction.user.display_name} | {discord.utils.format_dt(discord.utils.utcnow(), 'F')}"
        )

        hindi_embed = None
        hindi_is_actually_available = False

        if self.title_hi.value or self.description_hi.value:
            hindi_is_actually_available = True
            hindi_embed = create_styled_embed(
                title=self.title_hi.value if self.title_hi.value else self.title_en.value,
                description=self.description_hi.value if self.description_hi.value else "अधिक जानकारी के लिए देखें।",
                color=embed_color,
                image_url=self.image_url,
                thumbnail_url=self.thumbnail_url,
                footer_text=f"द्वारा प्रेषित {interaction.user.display_name} | {discord.utils.format_dt(discord.utils.utcnow(), 'F')}"
            )

        public_view = discord.ui.View()
        if hindi_is_actually_available:
            public_view.add_item(LanguageToggleButton(english_embed=english_embed, hindi_embed=hindi_embed).children[0])

        if self.button1_label and self.button1_url:
            public_view.add_item(discord.ui.Button(label=self.button1_label, url=self.button1_url, style=discord.ButtonStyle.link))
        if self.button2_label and self.button2_url:
            public_view.add_item(discord.ui.Button(label=self.button2_label, url=self.button2_url, style=discord.ButtonStyle.link))

        preview_buttons_view = PreviewButtons(
            original_interaction=interaction,
            public_embed=english_embed,
            public_view=public_view,
            target_channel=self.target_channel
        )

        await interaction.followup.send(
            content="👀 Here is a preview of your **English** embed. Click 'Confirm & Send' to post it to the channel, or 'Cancel'.",
            embed=english_embed,
            view=preview_buttons_view,
            ephemeral=True
        )


class EmbedMsgCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sendembed", description="Admin command to send a custom styled embed with multi-language support and preview.")
    @app_commands.describe(
        channel="The channel where the embed will be sent.",
        color="The main color of the embed (cyan, blue, red, green, purple, yellow).",
        image_url="Optional image URL for the embed.",
        thumbnail_url="Optional thumbnail URL for the embed.",
        button1_label="Label for the first link button (optional).",
        button1_url="URL for the first link button (optional).",
        button2_label="Label for the second link button (optional).",
        button2_url="URL for the second link button (optional)."
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
    await bot.add_cog(EmbedMsgCog(bot))