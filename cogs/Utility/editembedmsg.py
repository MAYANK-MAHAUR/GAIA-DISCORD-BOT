import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput

class EditExistingEmbedModal(Modal):
    def __init__(self, message: discord.Message):
        super().__init__(title="Edit Existing Embed")
        self.message = message
        self.embed = message.embeds[0] if message.embeds else discord.Embed()

        self.title_input = TextInput(label="Title", required=False, default=self.embed.title or "")
        self.desc_input = TextInput(label="Description", style=discord.TextStyle.paragraph, required=False, default=self.embed.description or "")
        self.footer_input = TextInput(label="Footer", required=False, default=self.embed.footer.text if self.embed.footer else "")
        self.field1_name = TextInput(label="Field 1 Name", required=False, default=self.embed.fields[0].name if len(self.embed.fields) > 0 else "")
        self.field1_value = TextInput(label="Field 1 Value", required=False, style=discord.TextStyle.paragraph, default=self.embed.fields[0].value if len(self.embed.fields) > 0 else "")

        self.add_item(self.title_input)
        self.add_item(self.desc_input)
        self.add_item(self.footer_input)
        self.add_item(self.field1_name)
        self.add_item(self.field1_value)

    async def on_submit(self, interaction: discord.Interaction):
        new_embed = discord.Embed(
            title=self.title_input.value or None,
            description=self.desc_input.value or None,
            color=self.embed.color
        )

        if self.footer_input.value:
            new_embed.set_footer(text=self.footer_input.value)

        if self.field1_name.value and self.field1_value.value:
            new_embed.add_field(name=self.field1_name.value, value=self.field1_value.value, inline=False)

        if self.embed.thumbnail and self.embed.thumbnail.url:
            new_embed.set_thumbnail(url=self.embed.thumbnail.url)
        if self.embed.image and self.embed.image.url:
            new_embed.set_image(url=self.embed.image.url)

        await self.message.edit(embed=new_embed)
        await interaction.response.send_message("✅ Embed edited!", ephemeral=True)

class EmbedEditor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="edit_embed_message", description="Edit an existing embed message")
    @app_commands.describe(message_id="The message ID of the embed you want to edit", channel="The channel where the message is")
    async def edit_embed_message(self, interaction: discord.Interaction, message_id: str, channel: discord.TextChannel):
        try:
            msg = await channel.fetch_message(int(message_id))
            if not msg.embeds:
                return await interaction.response.send_message("❌ That message has no embeds.", ephemeral=True)
            await interaction.response.send_modal(EditExistingEmbedModal(msg))
        except discord.NotFound:
            await interaction.response.send_message("❌ Message not found.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don’t have permission to view that message.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmbedEditor(bot))
