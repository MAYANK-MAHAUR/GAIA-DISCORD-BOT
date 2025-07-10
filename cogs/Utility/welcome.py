import discord
from discord.ext import commands
from discord import Embed, Colour, ui
import datetime
import os
from dotenv import load_dotenv


load_dotenv()
WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID'))  
RULES_CHANNEL_ID = int(os.getenv('RULES_CHANNEL_ID')) 
ROLES_CHANNEL_ID = int(os.getenv('ROLES_CHANNEL_ID'))  

STATIC_GAIA_BANNER_PATH = 'Data/images/gaia_background.png'

class WelcomeButtons(ui.View):
    def __init__(self, rules_channel: discord.TextChannel = None, roles_channel: discord.TextChannel = None):
        super().__init__(timeout=None)
        if rules_channel:
            self.add_item(ui.Button(label="📘 Rules", url=rules_channel.jump_url, style=discord.ButtonStyle.link))
        if roles_channel:
            self.add_item(ui.Button(label="📜 Get Roles", url=roles_channel.jump_url, style=discord.ButtonStyle.link))

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        welcome_channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if not welcome_channel:
            print("❌ Welcome channel not found!")
            return

        welcome_text = f" ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎  <a:blackheart:1392364272108965888> <a:scribbleheartcute:1392152242995466251> Welcome {member.mention} to GAIA <a:scribbleheartcute:1392152242995466251> <a:blackheart:1392364272108965888>"
        await welcome_channel.send(welcome_text)

        if os.path.exists(STATIC_GAIA_BANNER_PATH):
            try:
                await welcome_channel.send(file=discord.File(STATIC_GAIA_BANNER_PATH))
            except Exception as e:
                print(f"❌ Error sending Gaia banner: {e}")
        else:
            await welcome_channel.send("⚠️ Gaia banner not found.")

        embed = Embed(
            description="<a:welcome:1392366806940913767> Welcome to GAIA! We're thrilled to have you here <a:welcome:1392366806940913767>‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎  ‎   "
                        f"<a:pinned:1392366633544323193> Check out <#{RULES_CHANNEL_ID}> and <#{ROLES_CHANNEL_ID}> to get started <a:pinned:1392366633544323193> ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎     \n",
            color=Colour.from_rgb(144, 238, 144),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        avatar_url = member.avatar.url if member.avatar else None
        embed.set_author(name=member.name, icon_url=avatar_url)

        if member.guild.icon:
            embed.set_footer(text=f"Enjoy your stay! | Member #{member.guild.member_count}", icon_url=member.guild.icon.url)
        else:
            embed.set_footer(text=f"Enjoy your stay! | Member #{member.guild.member_count}")

        rules_channel = self.bot.get_channel(RULES_CHANNEL_ID)
        roles_channel = self.bot.get_channel(ROLES_CHANNEL_ID)

        await welcome_channel.send(embed=embed, view=WelcomeButtons(rules_channel, roles_channel))

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))