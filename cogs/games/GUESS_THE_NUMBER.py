import discord
import random
import asyncio
from discord.ext import commands
from discord import app_commands
from Utilities.Leaderboard import (
    add_recent_winner, get_recent_winners, reset_leaderboard,
    is_leaderboard_full, set_last_leaderboard
)

ALLOWED_ROLES = ["Game Master", "Moderator"]
LEADERBOARD_CHANNEL_ID = 1379347453462970519

class Guess_no(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.winner_lock = asyncio.Lock()
        self.hint_tasks = {}  

    @app_commands.command(name="startguess", description="Starts the Guess Number game")
    @app_commands.describe(max_number="The maximum number to guess", host="Optional host name")
    async def startguess(self, interaction: discord.Interaction, max_number: int, host: str = None):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id in self.active_games:
            await interaction.response.send_message("**A game is already active in this channel!**", ephemeral=True)
            return

        secret_number = random.randint(1, max_number)

        embed = discord.Embed(
            title="🎮 Guess the Number",
            description=f"Pick a number between `1` and `{max_number}`!\n\n",
            color=discord.Color.blue()
        )
        embed.add_field(name="🎯 Join the Game", value="React with 🎯 to join in.", inline=False)
        embed.add_field(name="Game Paused", value="Chat is paused for 20 seconds for fair gameplay.", inline=False)
        embed.add_field(name="👥 Players Joined", value="*No one yet*", inline=False)

        await interaction.response.send_message(embed=embed)
        game_msg = await interaction.original_response()

        self.active_games[interaction.channel.id] = {
            "number": secret_number,
            "players": set(),
            "message": game_msg,
            "max": max_number,
            "host_id": interaction.user.id,
            "host_name": host or interaction.user.name,
            "game_name": "Guess the Number"
        }

        await game_msg.add_reaction("🎯")

        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        try:
            overwrite.send_messages = False
            await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            await asyncio.sleep(20)
        finally:
            overwrite.send_messages = True
            await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        await interaction.followup.send("🔓 **The game has started! You can now guess the number!**")


        task = self.bot.loop.create_task(self.send_hints(interaction.channel.id, secret_number, max_number, interaction.channel))
        self.hint_tasks[interaction.channel.id] = task

    @app_commands.command(name="resetguessleaderboard", description="Manually resets the Guess the Number leaderboard")
    async def reset_leaderboard_command(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to reset the leaderboard.", ephemeral=True)
            return

        reset_leaderboard()
        await interaction.response.send_message("🔄 The leaderboard has been reset!", ephemeral=True)

    async def send_hints(self, channel_id, number, max_num, channel):
        await asyncio.sleep(20)
        if channel_id not in self.active_games:
            return

        mid = max_num // 2
        hint1 = discord.Embed(
            title="🔍 Hint 1",
            description=f"The number is **{'greater than' if number > mid else 'less than or equal to'} {mid}**.",
            color=discord.Color.orange()
        )
        await channel.send(embed=hint1)

        await asyncio.sleep(40)
        if channel_id not in self.active_games:
            return

        quarter = max_num // 4
        three_quarters = 3 * quarter
        desc = f"The number is **between {quarter} and {three_quarters}**." \
            if quarter <= number <= three_quarters else (
            f"The number is **greater than {three_quarters}**." if number > three_quarters
            else f"The number is **less than {quarter}**."
        )

        hint2 = discord.Embed(title="🔍 Hint 2", description=desc, color=discord.Color.orange())
        await channel.send(embed=hint2)

        await asyncio.sleep(90)
        if channel_id in self.active_games:
            final_hint = discord.Embed(
                title="⏰ Final Hint",
                description=f"No one guessed it. The number was `{number}`.",
                color=discord.Color.red()
            )
            await channel.send(embed=final_hint)

            await self.active_games[channel_id]["message"].edit(content="❌ **Game Ended! No one guessed the number.**", embed=None)
            del self.active_games[channel_id]
            self.hint_tasks.pop(channel_id, None)  

    @app_commands.command(name="stopguess", description="Stops the ongoing Guess the Number game")
    async def stopguess(self, interaction: discord.Interaction):
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id not in self.active_games:
            await interaction.response.send_message("❌ **No active game in this channel.**", ephemeral=True)
            return

        number = self.active_games[interaction.channel.id]["number"]

      
        task = self.hint_tasks.pop(interaction.channel.id, None)
        if task and not task.done():
            task.cancel()

        await self.active_games[interaction.channel.id]["message"].edit(content="🛑 **Game stopped.**", embed=None)
        del self.active_games[interaction.channel.id]
        await interaction.response.send_message(f"🛑 **The game has been stopped. The number was `{number}`.**")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot or not reaction.message.guild:
            return

        for channel_id, game in self.active_games.items():
            if reaction.message.id == game["message"].id:
                if user.id in game["players"]:
                    return

                game["players"].add(user.id)
                joined = "\n".join(f"<@{uid}>" for uid in game["players"])

                embed = discord.Embed(
                    title="🎮 Guess the Number",
                    description=f"Guess a number between `1` and `{game['max']}`!",
                    color=discord.Color.blue()
                )
                embed.add_field(name="🎯 Join the Game", value="Only those who react can play.", inline=False)
                embed.add_field(name="Game Paused", value="Chat is paused for 20 seconds for fair gameplay.", inline=False)
                embed.add_field(name="👥 Players Joined", value=joined, inline=False)

                await game["message"].edit(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        channel_id = message.channel.id
        if channel_id not in self.active_games:
            return

        game = self.active_games[channel_id]

        if message.author.id not in game["players"]:
            return

        try:
            guess = int(message.content.strip())
        except ValueError:
            return

        if not (1 <= guess <= game["max"]):
            return

        async with self.winner_lock:
            if channel_id not in self.active_games:
                return

            if guess != game["number"]:
                return

            recent_winners = get_recent_winners()
            if any(str(w['user_id']) == str(message.author.id) for w in recent_winners):
                return

            await message.add_reaction("🎉")
            embed = discord.Embed(
                title="🎊 We Have a Winner!",
                description=f"{message.author.mention} guessed the number correctly! 🎯 It was `{game['number']}`.",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)

            add_recent_winner(
                user_id=message.author.id,
                username=message.author.name,
                game_name=game["game_name"],
                host_id=game["host_id"],
                host_name=game["host_name"]
            )

            leaderboard_embed = await self.build_leaderboard_embed()
            try:
                await game["message"].reply(embed=leaderboard_embed)
            except Exception as e:
                print(f"Failed to reply under game message: {e}")

            if is_leaderboard_full():
                leaderboard_channel = await self.bot.fetch_channel(LEADERBOARD_CHANNEL_ID)
                leaderboard_msg = await leaderboard_channel.send(embed=leaderboard_embed)
                set_last_leaderboard(leaderboard_channel.id, leaderboard_msg.id)
                await leaderboard_channel.send(
                    "🎉 **Leaderboard Full!** We've reached 10 winners.\n"
                    "🔄 **Leaderboard has been reset. Let the next round begin!**"
                )
                reset_leaderboard()

           
            task = self.hint_tasks.pop(channel_id, None)
            if task and not task.done():
                task.cancel()

            await game["message"].edit(content="🎯 **Game Over: We have a winner!**", embed=None)
            del self.active_games[channel_id]

    async def build_leaderboard_embed(self):
        recent = get_recent_winners()
        embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.gold())
        for idx, winner in enumerate(recent, start=1):
            timestamp = winner.get('timestamp', 'Unknown')
            embed.add_field(
                name=f"{idx}. @{winner['username']}",
                value=f"`{winner['game_name']}` | Host: {winner['host_name']} | {timestamp}",
                inline=False
            )
        return embed

async def setup(bot):
    await bot.add_cog(Guess_no(bot))
