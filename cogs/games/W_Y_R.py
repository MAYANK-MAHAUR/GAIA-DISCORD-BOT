import discord
from discord.ext import commands
import asyncio
import random
import time
import Utilities
import os
import json

from Utilities.wyr_utils import get_gaia_ai_response, get_embedding, calculate_cosine_similarity 
from Data.wyr_questions import WYR_QUESTIONS

WINNING_PROMPT_TEMPLATE = (
    "Generate a **very concise (1-2 sentences), funny, and insightful POSITIVE explanation** "
    "for why someone would choose '{winner_option_text}'. "
    "Do not mention any specific user. Focus on the benefits or humor of the choice. "
    "Keep it to **one, short sentence**."
)

LOSING_PROMPT_TEMPLATE = (
    "Generate a **very concise (1-2 sentences), slightly humorous or 'unfortunate' NEGATIVE explanation** "
    "for why someone would NOT choose '{loser_option_text}' or why it's the less popular option. "
    "Do not mention any specific user. Focus on the drawbacks or absurdity of the choice. "
    "Keep it to **one, short sentence**."
)

ALLOWED_ROLES = ["Game Master", "Moderator"]
VOTING_TIME_SECONDS = 60
EXPLANATION_READ_TIME_SECONDS = 25
MAX_POINTS_FOR_FIRST = 100
MIN_POINTS_FOR_CORRECT = 20
POINT_DECREMENT_PER_VOTER = 5
TOTAL_ROUNDS_PER_GAME = 20
SESSION_WIN_MILESTONE = 5 

MAX_QUESTION_RETRIES = 3 
QUESTION_SIMILARITY_THRESHOLD = 0.8 


LEADERBOARD_CHANNEL_ID = int(os.getenv('LEADERBOARD_CHANNEL_ID', '0')) 
PRIVATE_CHANNEL_ID = int(os.getenv('PRIVATE_CHANNEL_ID', '0')) 

class WyrGame:
    def __init__(self, host: discord.Member, total_rounds: int):
        self.host = host
        self.total_rounds = total_rounds
        self.current_round = 0
        self.message: discord.Message = None
        self.options: list[str] = []
        self.votes = {
            'A': [],
            'B': []
        }
        self.voted_users = set()
        self.start_time = time.time()
        self.is_active = True
        self.message_url: str = None
        self.available_local_questions = list(WYR_QUESTIONS)

class WYR(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.user_session_correct_votes = {} 
        self.leaderboard_cog = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.leaderboard_cog = self.bot.get_cog('PointsLeaderboard') 
        if not self.leaderboard_cog:
            print("PointsLeaderboard cog not found. Points will not be awarded.")
        else:
            print("PointsLeaderboard cog successfully loaded into WYR.")
        await self.bot.tree.sync() 

    @discord.app_commands.command(name='wyr', description=f'Starts a {TOTAL_ROUNDS_PER_GAME}-round "Would You Rather" game!')
    @discord.app_commands.checks.has_any_role(*ALLOWED_ROLES)
    async def wyr_slash_command(self, interaction: discord.Interaction):
        if interaction.channel_id in self.active_games and self.active_games[interaction.channel_id].is_active:
            await interaction.response.send_message("There's already an active 'Would You Rather' game in this channel! Please wait for it to finish or stop it.", ephemeral=True)
            return

        new_game = WyrGame(host=interaction.user, total_rounds=TOTAL_ROUNDS_PER_GAME)
        self.active_games[interaction.channel_id] = new_game
        self.user_session_correct_votes[interaction.channel_id] = {}

        await interaction.response.send_message(f"🧠 Starting a **{TOTAL_ROUNDS_PER_GAME}**-round **`Would You Rather`** game! Get ready for some tough choices!")

        self.bot.loop.create_task(self.run_wyr_game(interaction.channel, new_game))

    async def run_wyr_game(self, channel: discord.TextChannel, game: WyrGame):
        for i in range(game.total_rounds):
            if not game.is_active:
                break

            await channel.send(f"--- **Round {game.current_round + 1}/{game.total_rounds}** ---")
            game.current_round += 1

            game.voted_users.clear()
            game.votes = {'A': [], 'B': []}
            game.start_time = time.time()

            sent_message = await self.ask_wyr_question_round(channel, game)
            if not sent_message:
                game.is_active = False
                await channel.send("Failed to generate a question, ending game early.")
                break
            game.message = sent_message
            game.message_url = sent_message.jump_url

            await asyncio.sleep(VOTING_TIME_SECONDS)

            if game.is_active:
                await self.evaluate_wyr_round(channel, game)
            else:
                if game.message:
                    for item in game.message.components:
                        for child in item.children:
                            child.disabled = True
                    await game.message.edit(view=discord.ui.View.from_message(game.message))

        await self.finalize_wyr_game(channel, game)

    async def ask_wyr_question_round(self, channel: discord.TextChannel, game: WyrGame) -> discord.Message:
        async with channel.typing():
            raw_question = None
            option_A = None
            option_B = None

            if game.available_local_questions:
                raw_question = random.choice(game.available_local_questions)
                game.available_local_questions.remove(raw_question)
                print(f"Using local question: {raw_question}")
            
            if not raw_question:
                for _ in range(MAX_QUESTION_RETRIES):
                    prompt_for_question = (
                        "Generate a **highly unique, diverse, and imaginative** 'Would You Rather' question. "
                        "Ensure the two options are **distinct, silly, and creative**, and not commonly seen. "
                        "Separate the options clearly with ' OR '. "
                        "Do not include any extra sentences, introductory phrases, or explanations. "
                        "Example: 'Have a tiny personal raincloud that only waters your plants OR be able to instantly learn any dance move perfectly?'"
                    )
                    raw_question = await get_gaia_ai_response(prompt_for_question)

                    if not raw_question or ' OR ' not in raw_question:
                        continue 

                    parts = raw_question.split(' OR ', 1)
                    if len(parts) < 2:
                        continue 

                    option_A = parts[0].strip()
                    option_B = parts[1].strip()

                    if option_A.startswith("Would you rather..."):
                        option_A = option_A[len("Would you rather..."):].strip()
                    if option_A.endswith("?") and not option_B.endswith("?"):
                        option_A = option_A[:-1].strip()
                    if option_B.endswith("?"):
                        option_B = option_B[:-1].strip()

                    try:
                        embedding_A = await get_embedding(option_A)
                        embedding_B = await get_embedding(option_B)
                        similarity = calculate_cosine_similarity(embedding_A, embedding_B)

                        if similarity < QUESTION_SIMILARITY_THRESHOLD:
                            game.options = [option_A, option_B]
                            break 
                        else:
                            print(f"Generated options too similar (Similarity: {similarity:.2f}). Retrying...")
                    except Exception as e:
                        print(f"Error checking similarity: {e}. Retrying question generation.")
                        continue 
                else: 
                    await channel.send("I couldn't come up with a sufficiently distinct 'Would You Rather' question after several attempts. Ending game early.")
                    return None
            else: 
                parts = raw_question.split(' OR ', 1)
                option_A = parts[0].strip()
                option_B = parts[1].strip()
                game.options = [option_A, option_B]


            view = discord.ui.View(timeout=VOTING_TIME_SECONDS)
            button_A = discord.ui.Button(label=option_A[:75], style=discord.ButtonStyle.blurple, custom_id=f"wyr_vote_A_{channel.id}_{game.current_round}")
            button_B = discord.ui.Button(label=option_B[:75], style=discord.ButtonStyle.blurple, custom_id=f"wyr_vote_B_{channel.id}_{game.current_round}")

            async def button_callback(interaction: discord.Interaction):
                await interaction.response.defer(ephemeral=True)

                current_game = self.active_games.get(interaction.channel_id)
                full_custom_id = interaction.data['custom_id']
                button_round = int(full_custom_id.split('_')[-1])

                if not current_game or not current_game.is_active or button_round != current_game.current_round:
                    await interaction.followup.send("This game round has ended or this button is from an old round. Your vote wasn't counted.", ephemeral=True)
                    return

                if interaction.user.bot:
                    return

                if interaction.user.id in current_game.voted_users:
                    await interaction.followup.send("You've already voted in this round!", ephemeral=True)
                    return

                choice = full_custom_id.split('_')[2]

                current_game.votes[choice].append((interaction.user.id, time.time()))
                current_game.voted_users.add(interaction.user.id)

                await interaction.followup.send(f"You chose: **`{current_game.options[0] if choice == 'A' else current_game.options[1]}`**", ephemeral=True)

            button_A.callback = button_callback
            button_B.callback = button_callback
            view.add_item(button_A)
            view.add_item(button_B)

            question_embed = discord.Embed(
                title=f"🤔 **`Would You Rather`**: Round **{game.current_round}**/**{game.total_rounds}** 🤔",
                description=f"**`{option_A}`** OR **`{option_B}`**\n\nVote by clicking one of the buttons below!",
                color=discord.Color.blue()
            )
            question_embed.set_footer(text=f"Voting ends in {VOTING_TIME_SECONDS} seconds!")

            return await channel.send(embed=question_embed, view=view)

    async def evaluate_wyr_round(self, channel: discord.TextChannel, game: WyrGame):
        if not game.message:
            return

        for item in game.message.components:
            for child in item.children:
                child.disabled = True
        await game.message.edit(view=discord.ui.View.from_message(game.message))

        votes_A_count = len(game.votes['A'])
        votes_B_count = len(game.votes['B'])
        total_votes = votes_A_count + votes_B_count

        if total_votes == 0:
            result_embed = discord.Embed(
                title=f"😴 **Round {game.current_round} Results**: No Votes! 😴",
                description="Looks like no one decided this round! The dilemma remains unsolved.",
                color=discord.Color.light_gray()
            )
            result_embed.add_field(name="The Question:", value=f"**`{game.options[0]}`** OR **`{game.options[1]}`**", inline=False)
            await game.message.edit(embed=result_embed, view=None)
            return

        winner_option_text = None
        loser_option_text = None
        winning_voters_info = []
        losing_voters_info = []

        if votes_A_count > votes_B_count:
            winner_option_text = game.options[0]
            loser_option_text = game.options[1]
            winning_voters_info = game.votes['A']
            losing_voters_info = game.votes['B']
        elif votes_B_count > votes_A_count:
            winner_option_text = game.options[1]
            loser_option_text = game.options[0]
            winning_voters_info = game.votes['B']
            losing_voters_info = game.votes['A']
        else:
            result_embed = discord.Embed(
                title=f"🤝 **Round {game.current_round} Results**: It's a Tie! 🤝",
                description=f"Both options received **{votes_A_count}** votes!\n\n"
                            "Looks like everyone's equally indecisive! No clear winner this round.",
                color=discord.Color.orange()
            )
            result_embed.add_field(name="The Question:", value=f"**`{game.options[0]}`** OR **`{game.options[1]}`**", inline=False)
            await game.message.edit(embed=result_embed, view=None)
            if self.leaderboard_cog:
                for user_id, _ in game.votes['A'] + game.votes['B']:
                    await self.leaderboard_cog.add_points(user_id, MIN_POINTS_FOR_CORRECT // 2)
            return

        winning_prompt = WINNING_PROMPT_TEMPLATE.format(winner_option_text=winner_option_text)
        losing_prompt = LOSING_PROMPT_TEMPLATE.format(loser_option_text=loser_option_text)

        winning_statement = await get_gaia_ai_response(winning_prompt)
        
        result_embed = discord.Embed(
            title=f"✨ **Round {game.current_round} Results!** ✨",
            description=f"The dilemma of **`{game.options[0]}`** vs. **`{game.options[1]}`** has been decided!\n\n"
                        f"**`{winner_option_text}`** was the most popular choice "
                        f"with **{votes_A_count if winner_option_text == game.options[0] else votes_B_count}** votes.",
            color=discord.Color.green()
        )
        result_embed.add_field(
            name="✅ Why this was the popular pick:",
            value=winning_statement,
            inline=False
        )
        result_embed.set_footer(text=f"Round {game.current_round}/{game.total_rounds} | Results continuing in {EXPLANATION_READ_TIME_SECONDS} seconds...")

        results_message = await channel.send(embed=result_embed)

        await asyncio.sleep(EXPLANATION_READ_TIME_SECONDS)

        winning_voters_info.sort(key=lambda x: x[1])
        awarded_players_info = []

        for i, (user_id, vote_time) in enumerate(winning_voters_info):
            points_to_award = max(MIN_POINTS_FOR_CORRECT, MAX_POINTS_FOR_FIRST - (i * POINT_DECREMENT_PER_VOTER))
            if self.leaderboard_cog:
                await self.leaderboard_cog.add_points(user_id, points_to_award)
                total_points = await self.leaderboard_cog.get_points(user_id)
            else:
                total_points = "N/A"

            self.user_session_correct_votes[channel.id][user_id] = \
                self.user_session_correct_votes[channel.id].get(user_id, 0) + 1

            current_session_wins = self.user_session_correct_votes[channel.id][user_id]
            awarded_players_info.append((user_id, points_to_award, current_session_wins, total_points))


            if current_session_wins >= SESSION_WIN_MILESTONE:
                member = channel.guild.get_member(user_id)
                if member: 
                    await channel.send(embed=discord.Embed(
                        title="🌟 **`WYR` Milestone!**",
                        description=f"{member.mention} reached **{current_session_wins}** correct majority votes in this game session!",
                        color=discord.Color.blue()
                    ))


        losing_statement = await get_gaia_ai_response(losing_prompt)

        result_embed.description += (
            f"\n\n**`{loser_option_text}`** was the less popular choice "
            f"with **{votes_A_count if loser_option_text == game.options[0] else votes_B_count}** votes."
        )
        result_embed.add_field(
            name="❌ Why this might be a challenge:",
            value=losing_statement,
            inline=False
        )

        points_awarded_str = "No points awarded for the losing option."
        if awarded_players_info:
            points_awarded_lines = []
            for user_id, points, _, total_points in awarded_players_info: 
                member = channel.guild.get_member(user_id)
                if member:
                    points_awarded_lines.append(f"{member.mention} (Total: `{total_points}`): **+{points}** points") 
                else:
                    points_awarded_lines.append(f"User ID **{user_id}** (Total: `{total_points}`): **+{points}** points") 
            points_awarded_str = "\n".join(points_awarded_lines)

        result_embed.add_field(name="🏆 **Points Awarded (this round)**:", value=points_awarded_str, inline=False)
        result_embed.set_footer(text=f"**Round {game.current_round}**/**{game.total_rounds}** complete. Total points updated.")
        result_embed.add_field(name="Jump to Question:", value=f"[Original Message]({game.message_url})", inline=False)

        await results_message.edit(embed=result_embed)


    async def finalize_wyr_game(self, channel: discord.TextChannel, game: WyrGame):
        if not self.active_games.get(channel.id) or not self.active_games[channel.id].is_active:
            self.active_games.pop(channel.id, None)
            self.user_session_correct_votes.pop(channel.id, None)
            return

        game.is_active = False

        await channel.send("🎉 **`Would You Rather` Game Over!** 🎉")

        if self.leaderboard_cog:
            await channel.send("💡 To see the updated global leaderboard, use the `/showpoints` command!") 

        milestone_achievers = []
        if channel.id in self.user_session_correct_votes:
            for user_id, correct_votes in self.user_session_correct_votes[channel.id].items():
                if correct_votes >= SESSION_WIN_MILESTONE:
                    milestone_achievers.append(user_id)

        if milestone_achievers:
            await self._handle_role_assignment(channel, game.host, milestone_achievers)
        else:
            await channel.send("No players reached the session milestone for role assignment in this game.")

        self.active_games.pop(channel.id, None)
        self.user_session_correct_votes.pop(channel.id, None)

    async def _handle_role_assignment(self, game_channel: discord.TextChannel, host: discord.Member, winners_ids: list[int]):
        private_channel = self.bot.get_channel(PRIVATE_CHANNEL_ID)
        if not private_channel:
            await game_channel.send(f"⚠️ Private channel for role management (ID: **`{PRIVATE_CHANNEL_ID}`**) not found. Skipping role assignment.")
            return

        winner_mentions = ", ".join([f"<@{uid}>" for uid in winners_ids])
        await private_channel.send(
            f"Attention {host.mention}, the **`Would You Rather`** game has concluded in {game_channel.mention}.\n"
            f"The following players reached the session milestone: {winner_mentions}.\n\n"
            f"What role should they receive? (Type role name, e.g., 'Game Champion' or 'skip')"
        )

        def check(m):
            return m.author == host and m.channel == private_channel and m.content

        try:
            role_message = await self.bot.wait_for('message', check=check, timeout=60.0)
            role_name = role_message.content.strip()

            if role_name.lower() == "skip":
                await private_channel.send("Role assignment skipped.")
                return

            guild = game_channel.guild
            role = discord.utils.get(guild.roles, name=role_name)

            if not role:
                try:
                    role = await guild.create_role(name=role_name)
                    await private_channel.send(f"✅ Role `{role.name}` created and will be assigned to milestone achievers.")
                except discord.Forbidden:
                    await private_channel.send("🚫 I don't have permission to create roles. Please check my role hierarchy.")
                    return

            if guild.me.top_role <= role:
                await private_channel.send("🚫 My role is not high enough to assign this role. Please adjust my role hierarchy.")
                return

            assigned_members = []
            for user_id in winners_ids:
                member = guild.get_member(user_id)
                if member and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Reached WYR session milestone")
                        assigned_members.append(member.mention)
                    except discord.Forbidden:
                        await private_channel.send(f"⚠️ I don't have permission to assign the role '{role_name}' to {member.display_name}. Skipping this user.")
                    except Exception as e:
                        print(f"Error assigning role to {member.display_name}: {e}")
                elif member and role in member.roles:
                    print(f"{member.display_name} already has role {role.name}.")
                else:
                    print(f"Member with ID {user_id} not found in guild.")

            if assigned_members:
                await private_channel.send(f"🏅 Successfully assigned role `{role.name}` to: {', '.join(assigned_members)}.")
                await game_channel.send(f"A special role has been assigned to the top players of this game! Check the private channel for details.")
            else:
                await private_channel.send("ℹ️ No users were assigned the role, they might already have it or not be in the server.")

        except asyncio.TimeoutError:
            await private_channel.send("Role assignment timed out: No response received in time.")
        except Exception as e:
            print(f"An error occurred during role assignment process: {e}")
            await private_channel.send(f"An unexpected error occurred during role assignment: {e}")

    @discord.app_commands.command(name='stopwyr', description='Stops the ongoing Would You Rather game in the current channel.')
    @discord.app_commands.checks.has_any_role(*ALLOWED_ROLES)
    async def stopwyr_slash_command(self, interaction: discord.Interaction):
        if interaction.channel_id in self.active_games and self.active_games[interaction.channel_id].is_active:
            game_to_stop = self.active_games[interaction.channel_id]
            game_to_stop.is_active = False

            if game_to_stop.message:
                for item in game_to_stop.message.components:
                    for child in item.children:
                        child.disabled = True
                await game_to_stop.message.edit(view=discord.ui.View.from_message(game_to_stop.message))

            await interaction.response.send_message("🛑 **`Would You Rather`** game stopped. Finalizing results...")
        else:
            await interaction.response.send_message("❗ No **`Would You Rather`** game running in this channel.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(WYR(bot))