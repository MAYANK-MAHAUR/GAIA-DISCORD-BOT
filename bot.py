import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')


intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
intents.dm_messages = True 
intents.guilds = True
intents.message_content = True
intents.guild_messages = True

bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

@bot.event
async def on_ready():
    guild = discord.utils.get(bot.guilds, name=GUILD)
    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})')
    
    await bot.tree.sync()
    print(f"Bot is Working as {bot.user}")
    

@bot.event
async def on_member_join(member):
    channel_id = 1379347453462970519  
    channel = bot.get_channel(channel_id)
    if channel:
        embed = discord.Embed(
            title="👋 Welcome to Gaia!",
            description=(
                "We're so glad you're here! 🎉 Please take a moment to introduce yourself by answering:\n\n"
                "🙋 **Your Name**\n"
                "🌍 **Your Location**\n"
                "ℹ️ **About You**\n"
                "🔥 **How would you like to contribute to Gaia?**\n"
                "🌱 **What excites you most about Gaia?**\n\n"
                "💡 Feel free to add anything else you’d love to share. We’re building something amazing together!"
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="Let’s grow the future, one idea at a time 🌱")
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        await channel.send(
            content=member.mention,  
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True)
        )



#Hello Command(Just to check bot is working)
@bot.command(name="hello")
async def hello(ctx):
    await ctx.send(f"Hi {ctx.author.name}, I’m GAIA Bot!")

async def load_cogs():
    await bot.load_extension("cogs.basic")
    await bot.load_extension("cogs.games.GUESS_THE_NUMBER")
    await bot.load_extension("cogs.games.TRIVIA")
    await bot.load_extension("cogs.games.R-P-S")
    await bot.load_extension("cogs.games.scramble_words")
    await bot.load_extension("cogs.games.Lyrics_Guess")
    await bot.load_extension("cogs.games.emoji_guess")
    
    await bot.load_extension("cogs.Moderation.ban")
    await bot.load_extension("cogs.Moderation.kick")
    await bot.load_extension("cogs.Moderation.unban")
    await bot.load_extension("cogs.Moderation.lock_channel")
    await bot.load_extension("cogs.Moderation.unlock_channel")
    await bot.load_extension("cogs.Moderation.purge")
    await bot.load_extension("cogs.Moderation.warn")
    await bot.load_extension("cogs.Moderation.mute")
    await bot.load_extension("cogs.Moderation.nickname_change")
    await bot.load_extension("cogs.Moderation.slowmode")
    await bot.load_extension("cogs.Moderation.unmute")
    await bot.load_extension("cogs.Moderation.role")
    
    await bot.load_extension("Utilities.leaderboardreset_cmds")
    await bot.load_extension("cogs.Utility.embedmsg")
    await bot.load_extension("cogs.Utility.editembedmsg")
    await bot.load_extension("cogs.Utility.send")
    await bot.load_extension("cogs.Utility.poll")



async def main():
    await load_cogs()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
    