import os
import asyncio
import discord
import botresponses
import random
from discord.ext import commands
from openai import OpenAI
from dotenv import load_dotenv

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GAIANET_API_KEY = os.getenv("GAIANET_API_KEY")
GAIANET_BASE_URL = os.getenv("GAIANET_BASE_URL")
GAIANET_MODEL_NAME = os.getenv("GAIANET_MODEL_NAME") 


load_dotenv()
gaia_client = OpenAI(
    base_url=GAIANET_BASE_URL,
    api_key=GAIANET_API_KEY
)



intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
intents.dm_messages = True 
intents.presences = True 
intents.guilds = True
intents.message_content = True
intents.guild_messages = True

bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)



async def get_gaia_ai_response(question: str) -> str:
    if not GAIANET_API_KEY:
        print("Error: GaiaNet API key is not configured in .env.")
        return botresponses.ERROR_GENERIC 

    try:
        response = gaia_client.chat.completions.create(
            model=GAIANET_MODEL_NAME, 
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant on Discord, powered by GaiaNet. Provide concise and direct answers."},
                {"role": "user", "content": question}
            ],
            temperature=0.7, 
            max_tokens=500
        )
 
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling GaiaNet API: {e}")
        return botresponses.GAIANET_ERROR

@bot.event
async def on_ready():
    guild = discord.utils.get(bot.guilds, name=GUILD)
    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})')
    
    await bot.tree.sync()
    print(f"Bot is Working as {bot.user}")
    print(botresponses.HELLO_MESSAGE)





@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    bot_mentioned = bot.user.mentioned_in(message)

    is_reply_to_bot = (
        message.reference 
        and message.reference.resolved 
        and message.reference.resolved.author == bot.user 
    )

    question_content = message.content.strip()

    
    if bot_mentioned or is_reply_to_bot:
        if bot_mentioned:
            mention_string = f"<@{bot.user.id}>"
            mention_string_nickname = f"<@!{bot.user.id}>"
            question_content = question_content.replace(mention_string, "").replace(mention_string_nickname, "").strip()

        if not question_content:
            await message.reply(botresponses.GAIANET_NO_QUESTION_MENTION_REPLY)
            return 


        ai_response = await get_gaia_ai_response(question_content)
        await message.reply(ai_response)
        return 
    await bot.process_commands(message)


@bot.command(name='askgaia', help=botresponses.GAIANET_NO_QUESTION_COMMAND)
async def ask_gaia_command(ctx, *, question: str = None):
    if question is None:
        await ctx.send(botresponses.GAIANET_NO_QUESTION_COMMAND)
        return
    await ctx.send(botresponses.GAIANET_LOADING)

    ai_response = await get_gaia_ai_response(question)
    await ctx.send(f"**GaiaNet AI says:** {ai_response}")

@bot.command(name='hello', help='Says hello to the user.')
async def hello_command(ctx):
    await ctx.send(botresponses.HELLO_MESSAGE)

@bot.command(name='ping', help='Checks if the bot is alive.')
async def ping_command(ctx):
    await ctx.send(botresponses.PONG_MESSAGE)

@bot.command(name='coinflip', help='Flips a coin (Heads or Tails).')
async def coinflip_command(ctx):
    if random.choice([True, False]):
        await ctx.send(botresponses.FLIP_COIN_HEADS)
    else:
        await ctx.send(botresponses.FLIP_COIN_TAILS)

@bot.command(name='helpme', help='Shows available commands.')
async def helpme_command(ctx):
    await ctx.send(botresponses.command_help_message(bot.command_prefix))


async def load_cogs():
    await bot.load_extension("cogs.Utility.embedmsg")
    await bot.load_extension("cogs.Utility.editembedmsg")
    await bot.load_extension("cogs.Utility.welcome")
    await bot.load_extension("Utilities.Leaderboard")
    await bot.load_extension("Utilities.leaderboardreset_cmd")
    await bot.load_extension("cogs.Utility.send")
    await bot.load_extension("cogs.Utility.poll")

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
    



async def main():
    await load_cogs()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
    