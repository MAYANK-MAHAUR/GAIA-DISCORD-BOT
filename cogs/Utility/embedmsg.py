import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button

class PreviewButtons(View):
    def __init__(self, bot, interaction, embed, view, target_channel):
        super().__init__(timeout=60)
        self.bot = bot
        self.interaction = interaction
        self.embed = embed
        self.view = view
        self.target_channel = target_channel

    @discord.ui.button(label="✅ Confirm & Send", style=discord.ButtonStyle.success, custom_id="confirm_send")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("⚠️ You can't confirm this action.", ephemeral=True)
        await self.target_channel.send(embed=self.embed, view=self.view)
        await interaction.response.edit_message(content="✅ Embed successfully sent!", embed=None, view=None)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("⚠️ You can't cancel this.", ephemeral=True)
        await interaction.response.edit_message(content="❌ Canceled sending the embed.", embed=None, view=None)


class EmbedMsg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embedmsg", description="Admin command to send a custom styled embed with preview.")
    @app_commands.describe(
        channel="Channel to send the embed in",
        title="Embed title",
        description="Embed description",
        color="Embed color (cyan, blue, red, green, purple, yellow)",
        image="Image URL (optional)",
        thumbnail="Thumbnail URL (optional)",
        footer="Footer text (optional)",

        field1_name="Field 1 name", field1_value="Field 1 value",
        field2_name="Field 2 name", field2_value="Field 2 value",
        field3_name="Field 3 name", field3_value="Field 3 value",
        field4_name="Field 4 name", field4_value="Field 4 value",
        field5_name="Field 5 name", field5_value="Field 5 value",

        button1_label="Button 1 label", button1_url="Button 1 URL",
        button2_label="Button 2 label", button2_url="Button 2 URL"
    )
    async def embedmsg(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        description: str,
        color: str = "cyan",
        image: str = None,
        thumbnail: str = None,
        footer: str = None,

        field1_name: str = None, field1_value: str = None,
        field2_name: str = None, field2_value: str = None,
        field3_name: str = None, field3_value: str = None,
        field4_name: str = None, field4_value: str = None,
        field5_name: str = None, field5_value: str = None,

        button1_label: str = None, button1_url: str = None,
        button2_label: str = None, button2_url: str = None,
    ):
       
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("🚫 Only admins can use this command.", ephemeral=True)

        
        color_dict = {
            "cyan": discord.Color.teal(),
            "blue": discord.Color.blue(),
            "red": discord.Color.red(),
            "green": discord.Color.green(),
            "purple": discord.Color.purple(),
            "yellow": discord.Color.gold()
        }
        embed_color = color_dict.get(color.lower(), discord.Color.teal())

        
        embed = discord.Embed(title=title, description=description, color=embed_color)
        if image:
            embed.set_image(url=image)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if footer:
            embed.set_footer(text=footer)

        
        fields = [
            (field1_name, field1_value),
            (field2_name, field2_value),
            (field3_name, field3_value),
            (field4_name, field4_value),
            (field5_name, field5_value),
        ]
        for name, value in fields:
            if name and value:
                embed.add_field(name=name, value=value, inline=False)

        
        view = View()
        if button1_label and button1_url:
            view.add_item(Button(label=button1_label, url=button1_url, style=discord.ButtonStyle.link))
        if button2_label and button2_url:
            view.add_item(Button(label=button2_label, url=button2_url, style=discord.ButtonStyle.link))

        
        await interaction.response.send_message(
            content="👀 Here is a preview of your embed. Click to confirm or cancel.",
            embed=embed,
            view=PreviewButtons(self.bot, interaction, embed, view, channel),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(EmbedMsg(bot))
