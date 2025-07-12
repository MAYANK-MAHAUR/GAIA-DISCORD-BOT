import os
import asyncio
import discord
import botresponses
import random
import sqlite3
import json
from discord.ext import commands
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GAIANET_API_KEY = os.getenv("GAIANET_API_KEY")
GAIANET_BASE_URL = os.getenv("GAIANET_BASE_URL")
GAIANET_MODEL_NAME = os.getenv("GAIANET_MODEL_NAME") 

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

DB_NAME = 'bot_memory.db'
MAX_HISTORY_MESSAGES = 20

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_histories (
            conversation_id TEXT PRIMARY KEY,
            history TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_chat_history(conversation_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT history FROM chat_histories WHERE conversation_id = ?', (conversation_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return json.loads(result[0])
    return []

def save_chat_history(conversation_id, history):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    history_json = json.dumps(history)
    cursor.execute(
        'INSERT OR REPLACE INTO chat_histories (conversation_id, history) VALUES (?, ?)',
        (conversation_id, history_json)
    )
    conn.commit()
    conn.close()

def clear_chat_history_db(conversation_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM chat_histories WHERE conversation_id = ?', (conversation_id,))
    conn.commit()
    conn.close()

async def get_gaia_ai_response(prompt_text, conversation_id):
    if not GAIANET_API_KEY:
        print("Error: GaiaNet API key is not configured in .env.")
        return botresponses.ERROR_GENERIC 

    try:
        chat_history = get_chat_history(conversation_id)

        system_message = {"role": "system", "content": "You are a helpful AI assistant on Discord, powered by GaiaNet. Provide concise and direct answers."}

        user_message = {"role": "user", "content": prompt_text}
        chat_history.append(user_message)

        messages_for_api = [system_message] + chat_history[-(MAX_HISTORY_MESSAGES - 1):]

        response = gaia_client.chat.completions.create(
            model=GAIANET_MODEL_NAME, 
            messages=messages_for_api,
            temperature=0.7, 
            max_tokens=500
        )
    
        ai_response_content = response.choices[0].message.content

        ai_message = {"role": "assistant", "content": ai_response_content}
        chat_history.append(ai_message)

        save_chat_history(conversation_id, chat_history[-MAX_HISTORY_MESSAGES:])

        return ai_response_content
    except Exception as e:
        print(f"Error calling GaiaNet API: {e}")
        return botresponses.GAIANET_ERROR

@bot.event
async def on_ready():
    guild = discord.utils.get(bot.guilds, name=GUILD)
    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})')
    
    init_db()
    await bot.tree.sync()
    print(f"Bot is Working as {bot.user}")
    print(botresponses.HELLO_MESSAGE)

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    conversation_id = str(message.channel.id)

    bot_mentioned = bot.user.mentioned_in(message)

    is_reply_to_bot = (
        message.reference 
        and message.reference.resolved 
        and message.reference.resolved.author == bot.user 
    )

    question_content = message.content.strip()

    if bot_mentioned or is_reply_to_bot or question_content.startswith(bot.command_prefix + 'askgaia'):
        async with message.channel.typing():
            if bot_mentioned:
                mention_string = f"<@{bot.user.id}>"
                mention_string_nickname = f"<@!{bot.user.id}>"
                question_content = question_content.replace(mention_string, "").replace(mention_string_nickname, "").strip()
            
            if question_content.startswith(bot.command_prefix + 'askgaia'):
                question_content = question_content[len(bot.command_prefix + 'askgaia'):].strip()

            if not question_content:
                await message.reply()
                return 

            ai_response = await get_gaia_ai_response(question_content, conversation_id)
            await message.reply(ai_response)
            return 
    await bot.process_commands(message)

@bot.command(name='askgaia', help=botresponses.GAIANET_NO_QUESTION_COMMAND)
async def ask_gaia_command(ctx, *, question: str = None):
    if question is None:
        await ctx.send(botresponses.GAIANET_NO_QUESTION_COMMAND)
        return

    conversation_id = str(ctx.channel.id)
    ai_response = await get_gaia_ai_response(question, conversation_id)
    await ctx.send(f"{ai_response}")

@bot.command(name='clear_history', help='Clears the bot\'s conversation memory for this channel.')
async def clear_history(ctx):
    conversation_id = str(ctx.channel.id)
    clear_chat_history_db(conversation_id)
    await ctx.send("My conversation memory for this channel has been cleared!")

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