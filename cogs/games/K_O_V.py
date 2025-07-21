import discord
from discord.ext import commands, tasks
import random
import asyncio
import aiohttp # For async HTTP requests to Gaianet.ai
import os

# --- Configuration & Global Variables (REPLACE THESE PLACEHOLDERS) ---
# It's best to store these in environment variables (e.g., using python-dotenv)
# GAIANET_API_KEY: Get this from your Gaianet.ai dashboard.
GAIANET_API_KEY = os.getenv('GAIANET_API_KEY') # REPLACE THIS

# GAIANET_API_ENDPOINT: REPLACE THIS with the actual API endpoint for Gaianet.ai's LLM.
# Example: "https://api.gaianet.ai/v1/completions" or similar based on their docs.
GAIANET_API_ENDPOINT = os.getenv('GAIANET_BASE_URL') # REPLACE THIS

# GAIANET_LLM_MODEL: REPLACE THIS with the specific model name Gaianet.ai uses (e.g., "text-davinci-003", "gaianet-v1", etc.)
GAIANET_LLM_MODEL = os.getenv('GAIANET_MODEL_NAME') # REPLACE THIS

# MAIN_GAME_CHANNEL_ID: The ID of the public channel where the game announcements and public chat happen.
# Right-click the channel in Discord -> Copy ID (Developer Mode must be on)
MAIN_GAME_CHANNEL_ID = 1395713146236440736 # REPLACE THIS with your main game channel ID

# ROLE_IDS: The IDs of the *hidden* roles you created in your Discord server.
# Right-click the role in Server Settings -> Roles -> Copy ID
OFFICER_ROLE_ID = 1395713259826315349 # REPLACE THIS
KILLER_ROLE_ID = 1395713362888884368 # REPLACE THIS
VOTER_ROLE_ID = 1395713446334693436 # REPLACE THIS

# Game Parameters
MIN_PLAYERS = 2
MAX_PLAYERS = 75 # Set a hard cap for very large games
SIGNUP_TIME_SECONDS = 180 # 15 minutes for players to join
UNIT_REVEAL_PAUSE_SECONDS = 5 # Pause between each unit being announced

# Phase Timers (for a fast-paced game with 60 players)
NIGHT_PHASE_TIME_SECONDS = 180 # 2 minutes for Killers to decide
DISCUSSION_TIME_SECONDS = 300 # 5 minutes for public debate
VOTING_TIME_SECONDS = 90 # 1 minute 30 seconds for voting

# EP Prize Pool Distribution (Percentages)
PRIZE_WINNER_SHARE = 0.70
PRIZE_SECOND_PLACE_SHARE = 0.20
PRIZE_ELIMINATED_SHARE = 0.10

# Game State Storage (In-memory. For persistence, use a database like SQLite, PostgreSQL, etc.)
class GameState:
    def __init__(self):
        self.is_game_running = False
        self.current_phase = "IDLE" # IDLE, SIGNUP, NIGHT, DAY, END
        self.registered_players = {} # {member_id: member_object} - all players who signed up
        self.live_players = {} # {member_id: {"member": member_object, "role": "Officer", "unit": 1, "is_alive": True}} - current game players
        self.roles = {} # {member_id: "role_string"} - quick lookup
        self.units = {} # {unit_num: [member_id1, member_id2, ...]}
        self.game_channels = {} # {role_name: channel_object} - private game channels
        self.game_id = None # Unique ID for current game instance
        self.votes = {} # {voter_id: target_id} for current voting round
        self.killer_targets = [] # List of (killer_id, [target_ids], power_used, framed_id) for current night
        self.game_message = None # To update signup message etc.
        self.prize_pool_ep = 10000 # Example base prize pool for the game

    def reset(self):
        # Reset all game-specific attributes to their initial state
        self.is_game_running = False
        self.current_phase = "IDLE"
        self.registered_players = {}
        self.live_players = {}
        self.roles = {}
        self.units = {}
        self.game_channels = {}
        self.game_id = None
        self.votes = {}
        self.killer_targets = []
        self.game_message = None
        self.prize_pool_ep = 10000 # Reset prize pool if it varies per game


# Global game state object instance
game_state = GameState()

# --- LLM Integration Function ---
async def get_llm_response(prompt: str) -> str:
    """
    Calls the Gaianet.ai LLM API to get a dynamic text response.
    REPLACE THE API ENDPOINT, MODEL, AND PAYLOAD STRUCTURE ACCORDING TO GAIANET.AI DOCS.
    """
    headers = {
        'Authorization': f'Bearer {GAIANET_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": GAIANET_LLM_MODEL, # e.g., "text-davinci-003" or a specific Gaianet.ai model
        "prompt": prompt,
        "max_tokens": 100, # Adjust token limit as needed for hints
        "temperature": 0.7, # Controls creativity (0.0-1.0)
        # Add other parameters like top_p, frequency_penalty etc., if supported/needed
    }
    
    if not GAIANET_API_ENDPOINT or not GAIANET_API_KEY or not GAIANET_LLM_MODEL:
        print("Gaianet.ai API credentials or endpoint not set. Skipping LLM call.")
        return "The ancient prophecies are silent on this matter. (LLM API not configured)"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(GAIANET_API_ENDPOINT, headers=headers, json=payload) as response:
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                data = await response.json()
                # *** REVISE THIS BASED ON GAIANET.AI's ACTUAL RESPONSE STRUCTURE ***
                # Example: data.get('choices')[0].get('text').strip() for OpenAI-like APIs
                # You might need to check data['data'][0]['text'] or similar.
                if 'choices' in data and len(data['choices']) > 0 and 'text' in data['choices'][0]:
                    return data['choices'][0]['text'].strip()
                elif 'response' in data: # Some APIs might directly return under a 'response' key
                    return data['response'].strip()
                else:
                    print(f"Unexpected LLM response structure: {data}")
                    return "The cosmic threads are tangled... my vision is unclear."
    except aiohttp.ClientError as e:
        print(f"Gaianet.ai API connection error: {e}")
        return "A static hum fills the void... (LLM connection error)"
    except Exception as e:
        print(f"An unexpected error occurred with LLM call: {e}")
        return "I am unable to process this request right now. (General LLM error)"


class GameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game_timer_task = None # Task for managing timers (signup, night, day)

    def get_main_game_channel(self):
        """Helper to get the main game channel object."""
        return self.bot.get_channel(MAIN_GAME_CHANNEL_ID)

    async def send_to_role_channel(self, role_name: str, message: str):
        """Helper to send messages to a specific private role channel."""
        if role_name in game_state.game_channels:
            try:
                await game_state.game_channels[role_name].send(message)
            except discord.Forbidden:
                print(f"Bot lacks permissions to send to {role_name} channel or channel deleted.")
            except Exception as e:
                print(f"Error sending to {role_name} channel: {e}")
        else:
            print(f"Error: Channel for role {role_name} not found in game_channels.")

    # --- Game Management Commands ---
    @commands.command(name='startgame')
    @commands.has_permissions(administrator=True) # Only admins can start the game
    async def start_game_cmd(self, ctx):
        if game_state.is_game_running:
            return await ctx.send("A game is already in progress!")
        
        # Ensure the main game channel is correct
        main_channel = self.get_main_game_channel()
        if not main_channel:
            return await ctx.send("Error: Main game channel not found. Please set `MAIN_GAME_CHANNEL_ID` correctly in the bot's configuration.")

        game_state.reset() # Reset previous game state for a fresh start
        game_state.is_game_running = True
        game_state.current_phase = "SIGNUP"
        game_state.game_id = f"game-{random.randint(1000, 9999)}" # Unique ID for current game channels

        signup_embed = discord.Embed(
            title=f"Discord Deception: [Your Epic Theme] - Game Starting!",
            description=(f"@everyone **A Grand Conspiracy brews in [Your Epic Game World]! "
                         f"Minimum {MIN_PLAYERS} souls are called to uncover the truth or spread the deception!**\n\n"
                         f"**Important Rules:**\n"
                         f"• **Hidden Identities:** Your role is secret! Do not check server settings or user profiles for roles. Cheating will result in severe penalties.\n"
                         f"• **Fair Play:** Engage in strategic discussion and deduction, not metagaming.\n"
                         f"• **EP Rewards:** The winning team will receive the largest share of the **{game_state.prize_pool_ep} EP** prize pool! Consolation prizes for other participants!\n\n"
                         f"**React with 🎮 to join this massive game!**\n"
                         f"Signups close in {SIGNUP_TIME_SECONDS // 60} minutes or when {MIN_PLAYERS} players join!")
        )
        game_state.game_message = await main_channel.send(embed=signup_embed)
        await game_state.game_message.add_reaction("🎮")

        # Start the signup timer
        self.game_timer_task = self.bot.loop.create_task(self.start_signup_timer())

    async def start_signup_timer(self):
        """Manages the signup period timer."""
        await asyncio.sleep(SIGNUP_TIME_SECONDS)
        if game_state.is_game_running and game_state.current_phase == "SIGNUP":
            await self.end_signup() # Automatically end signup after timer

    @commands.command(name='join')
    async def join_game_cmd(self, ctx):
        """Allows players to join the game by reacting or using the command."""
        if not game_state.is_game_running or game_state.current_phase != "SIGNUP":
            return await ctx.send("A game is not currently in the signup phase.")
        if ctx.author.id in game_state.registered_players:
            return await ctx.send("You've already joined the game!")
        
        if len(game_state.registered_players) >= MAX_PLAYERS:
            return await ctx.send("Sorry, the game has reached its maximum player limit!")

        game_state.registered_players[ctx.author.id] = ctx.author
        await ctx.send(f"{ctx.author.display_name} has joined the game! Current players: {len(game_state.registered_players)}/{MIN_PLAYERS}")

        # If minimum players met early, end signup
        if len(game_state.registered_players) >= MIN_PLAYERS:
            if self.game_timer_task and not self.game_timer_task.done():
                self.game_timer_task.cancel() # Cancel the current timer
            await self.end_signup()

    # --- Core Game Flow Logic ---
    async def end_signup(self):
        """Ends the signup phase, checks player count, and proceeds to role assignment."""
        if self.game_timer_task:
            self.game_timer_task.cancel() # Ensure the signup timer is stopped

        main_channel = self.get_main_game_channel()
        if len(game_state.registered_players) < MIN_PLAYERS:
            game_state.is_game_running = False
            game_state.current_phase = "IDLE"
            return await main_channel.send(f"Not enough players to start the game. ({len(game_state.registered_players)}/{MIN_PLAYERS}) Game cancelled.")

        await main_channel.send("**Signups are now closed! Preparing for role assignment...**")
        await asyncio.sleep(2) # Short pause for dramatic effect

        await self.create_role_channels() # Create private channels for roles
        await self.assign_roles_and_units() # Assign roles, units, and DM players
        
        # Start the main game loop after everything is set up
        self.game_loop_task = self.bot.loop.create_task(self.game_loop())

    async def create_role_channels(self):
        """Creates the hidden Discord channels for Officers, Killers, and Voters."""
        guild = self.get_main_game_channel().guild
        
        # Get actual role objects from the guild
        officer_role = guild.get_role(OFFICER_ROLE_ID)
        killer_role = guild.get_role(KILLER_ROLE_ID)
        voter_role = guild.get_role(VOTER_ROLE_ID)

        if not all([officer_role, killer_role, voter_role]):
            await self.get_main_game_channel().send("Error: One or more game roles not found. Please check `ROLE_IDS` in config.")
            return await self.end_game_early("Missing game roles.")

        # Define permissions for hidden roles
        bot_perms = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, manage_roles=True)
        everyone_denied = discord.PermissionOverwrite(read_messages=False, send_messages=False)
        
        # Create Officer Channel
        game_state.game_channels['Officer'] = await guild.create_text_channel(
            f"officer-intel-{game_state.game_id}",
            overwrites={
                guild.default_role: everyone_denied, # Deny @everyone
                officer_role: discord.PermissionOverwrite(read_messages=True, send_messages=True), # Allow Officers
                guild.me: bot_perms # Allow the bot
            },
            reason="Discord Deception game channel: Officer Intel"
        )
        await game_state.game_channels['Officer'].send("Welcome, brave Officers! Your secret intel channel is ready.")

        # Create Killer Channel
        game_state.game_channels['Killer'] = await guild.create_text_channel(
            f"killer-lair-{game_state.game_id}",
            overwrites={
                guild.default_role: everyone_denied, # Deny @everyone
                killer_role: discord.PermissionOverwrite(read_messages=True, send_messages=True), # Allow Killers
                guild.me: bot_perms
            },
            reason="Discord Deception game channel: Killer Lair"
        )
        await game_state.game_channels['Killer'].send("Welcome, architects of chaos! Your secret lair is open.")

        # Create Voter Channel
        game_state.game_channels['Voter'] = await guild.create_text_channel(
            f"voter-booth-{game_state.game_id}",
            overwrites={
                guild.default_role: everyone_denied, # Deny @everyone
                voter_role: discord.PermissionOverwrite(read_messages=True, send_messages=True), # Allow Voters
                guild.me: bot_perms
            },
            reason="Discord Deception game channel: Voter Booth"
        )
        await game_state.game_channels['Voter'].send("Welcome, arbiters of fate! Coordinate your suspicions here.")

        await self.get_main_game_channel().send("Secret channels created and secured!")
        await asyncio.sleep(1) # Small pause

    async def assign_roles_and_units(self):
        """Assigns roles and units, then DMs players their info with paced unit announcements."""
        main_channel = self.get_main_game_channel()
        players_list = list(game_state.registered_players.values())
        random.shuffle(players_list) # Randomize players before assigning roles and units

        # Determine role counts based on the actual number of players
        num_killers = 1
        num_officers = 1
        num_voters = len(players_list) - num_killers - num_officers

        if num_voters < 0: # Safety check for too many killers/officers for player count
            await main_channel.send("Error: Too many Killers/Officers assigned for the number of players. Adjust role counts.")
            return await self.end_game_early("Role count error.")

        # Assign roles to players in the shuffled list
        roles_assigned = []
        roles_assigned.extend(["Killer"] * num_killers)
        roles_assigned.extend(["Officer"] * num_officers)
        roles_assigned.extend(["Voter"] * num_voters)
        random.shuffle(roles_assigned) # Shuffle roles so they're not in blocks

        # Map role string to role object
        role_objects = {
            "Officer": self.get_main_game_channel().guild.get_role(OFFICER_ROLE_ID),
            "Killer": self.get_main_game_channel().guild.get_role(KILLER_ROLE_ID),
            "Voter": self.get_main_game_channel().guild.get_role(VOTER_ROLE_ID)
        }

        # Assign units and apply roles, updating live_players
        # For 60 players, 10 units of 6 or 12 units of 5
        unit_size = len(players_list) // 10 # Aim for around 10 units
        if unit_size == 0: unit_size = 1 # Prevent division by zero for very small player counts

        current_unit_num = 1
        current_unit_members = []
        
        await main_channel.send("**The Conclave of 60 is Forming!**")
        await asyncio.sleep(2) # Short pause before first unit reveal

        for i, player_member in enumerate(players_list):
            assigned_role_name = roles_assigned[i]
            
            # Add hidden Discord role to the player
            try:
                await player_member.add_roles(role_objects[assigned_role_name], reason="Game role assignment")
            except Exception as e:
                print(f"Failed to add role {assigned_role_name} to {player_member.display_name}: {e}")
                # Decide how to handle: end game, skip player, etc. For now, log.

            # Update game_state.live_players and units
            game_state.live_players[player_member.id] = {
                "member": player_member,
                "role": assigned_role_name,
                "unit": current_unit_num,
                "is_alive": True
            }
            game_state.roles[player_member.id] = assigned_role_name # Simplified lookup
            
            current_unit_members.append(player_member)

            # Check if unit is full or if it's the last player
            if len(current_unit_members) >= unit_size or i == len(players_list) - 1:
                game_state.units[current_unit_num] = [m.id for m in current_unit_members]
                unit_names = "\n".join([m.display_name for m in current_unit_members])
                await main_channel.send(f"**Unit {current_unit_num}:**\n{unit_names}")
                await asyncio.sleep(UNIT_REVEAL_PAUSE_SECONDS) # Pause between unit reveals

                current_unit_num += 1
                current_unit_members = [] # Reset for next unit

        await main_channel.send("All units are now revealed. The stage is set!")
        await asyncio.sleep(2)

        # DM roles and channels to players
        officers_list = [p["member"] for p_id, p in game_state.live_players.items() if p["role"] == "Officer"]
        killers_list = [p["member"] for p_id, p in game_state.live_players.items() if p["role"] == "Killer"]
        voters_list = [p["member"] for p_id, p in game_state.live_players.items() if p["role"] == "Voter"]


        for player_id, data in game_state.live_players.items():
            member = data["member"]
            role = data["role"]
            
            try:
                if role == "Officer":
                    await member.send(
                        f"You are an **Officer** in [Your Game World]! A secret channel, <#{game_state.game_channels['Officer'].id}>, "
                        f"has been unlocked for you and your {len(officers_list)-1} fellow Officers. Go there now to coordinate and receive crucial intelligence. "
                        f"Your fellow Officers are: {', '.join([o.display_name for o in officers_list if o.id != member.id])}. You hold the key to uncovering the deep conspiracy."
                    )
                elif role == "Killer":
                    await member.send(
                        f"You are a **Killer** in [Your Game World]! Head to <#{game_state.game_channels['Killer'].id}> to conspire with your {len(killers_list)-1} fellow Killers. "
                        f"Your goal: eliminate the opposition and evade detection. The Officers are: {', '.join([o.display_name for o in officers_list])}. Let the deception begin!"
                    )
                elif role == "Voter":
                    await member.send(
                        f"You are a **Voter** in [Your Game World]! Your role is crucial: listen to all arguments, debate wisely, and cast your vote to unmask the deceivers. "
                        f"Discuss strategies privately in <#{game_state.game_channels['Voter'].id}>!"
                    )
                await asyncio.sleep(0.1) # Small delay to avoid Discord rate limits on DMs
            except discord.Forbidden:
                print(f"Could not DM {member.display_name}. They might have DMs disabled. Role: {role}")
                await main_channel.send(f"Warning: Could not DM {member.display_name} their role. Please enable DMs from server members.")
            except Exception as e:
                print(f"Error sending DM to {member.display_name}: {e}")

        # Final public message after all DMs are attempted
        await main_channel.send(
            "@everyone **Attention, all players! Roles have been assigned.**\n"
            "**Please check your DMs NOW for your role information and access to your secret channels (if applicable)!**\n\n"
            "The first Night Phase will begin shortly. Prepare yourselves!"
        )
        await asyncio.sleep(5) # A short pause before Night Phase begins

    # --- Main Game Loop ---
    async def game_loop(self):
        """Main loop managing game phases."""
        game_state.current_phase = "NIGHT"
        while game_state.is_game_running:
            await self.night_phase()
            if not game_state.is_game_running: break # Game might end in night phase (e.g., Killer exposed)
            
            await self.day_phase()
            if not game_state.is_game_running: break # Game might end in day phase (e.g., Killer executed)
            
            # After each full round (night + day), check for game end
            await self.check_game_end()
            # If check_game_end sets is_game_running to False, loop will terminate next iteration

    async def night_phase(self):
        """Manages the Killer's action phase."""
        main_channel = self.get_main_game_channel()
        await main_channel.send(f"@everyone **Night descends upon [Your Epic Game World]! The silence is broken only by the whispers of the Killers...**\nAll players, stand by. Killers are making their move.")
        
        game_state.killer_targets = [] # Reset killer targets for the new night
        game_state.current_phase = "NIGHT"

        killer_channel = game_state.game_channels.get('Killer')
        if not killer_channel:
            print("Killer channel not found, cannot proceed with night phase.")
            return await self.end_game_early("Killer channel missing.")

        alive_killers = [data["member"] for data in game_state.live_players.values() if data["role"] == "Killer" and data["is_alive"]]
        if not alive_killers:
            # All killers eliminated, game should have ended. This is a safeguard.
            await main_channel.send("No Killers left. Skipping Night Phase.")
            return await self.check_game_end()

        # Prompt Killers
        await killer_channel.send(
            f"**Killers, execute your plan! Choose target(s) and killing power for the night:**\n"
            f"1.  **Standard Elimination (Moderate Risk):** Target ONE player.\n"
            f"2.  **Double Strike (High Risk - Immediate Exposure Chance):** Target TWO players.\n"
            f"3.  **Subtle Elimination (Lower Hint Specificity, Moderate Risk):** Target ONE player, Officers get a vaguer hint.\n"
            f"4.  **Framing Strike (Moderate Risk - Leaves a False Clue):** Target ONE player and choose an *innocent* player to frame.\n"
            f"5.  **Massacre (VERY High Risk - Target 3 Players):** Simultaneously eliminate THREE players. Highest risk of exposure.\n\n"
            f"**Command:** `!kill [PowerNumber] @Target1 [@Target2 if Double Strike] [@Target3 if Massacre] [optional @PlayerToFrame if Framing]`\n"
            f"**You have ONLY {NIGHT_PHASE_TIME_SECONDS // 60} minute(s) {NIGHT_PHASE_TIME_SECONDS % 60} second(s) to decide and execute! The first valid command will be processed.**"
        )
        
        # Start a timer for the night phase
        self.game_timer_task = self.bot.loop.create_task(asyncio.sleep(NIGHT_PHASE_TIME_SECONDS))
        try:
            await self.game_timer_task
        except asyncio.CancelledError:
            print("Night phase timer cancelled (e.g., kill command received early).")
        
        # Process targets after timer or early submission
        await self.process_killer_actions()


    async def process_killer_actions(self):
        """Processes the Killers' chosen actions after the night phase timer ends."""
        main_channel = self.get_main_game_channel()
        victims = []
        exposed_killer_member = None # Store member object of exposed killer
        hint_type = "standard" # Default hint type

        if not game_state.killer_targets:
            await main_channel.send("The Killers failed to make a move this night. No one was eliminated.")
            return # No kills, move to next phase

        # For simplicity, we process only the first valid kill submission if multiple killers
        # In a more complex bot, you'd aggregate votes/commands from all 10 killers.
        killer_id, target_ids_raw, power_used, framed_id = game_state.killer_targets[0]
        
        killer_data = game_state.live_players.get(killer_id)
        if not killer_data or not killer_data["is_alive"]:
            print(f"Killer ID {killer_id} not found or is dead. Skipping their action.")
            return # Should not happen if filters are good, but a safeguard

        killer_member = killer_data["member"]

        # Define exposure chances for each power
        exposure_chance_map = {
            1: 20, # Standard Elimination
            2: 50, # Double Strike
            3: 15, # Subtle Elimination (lower risk as hint is vague)
            4: 25, # Framing Strike
            5: 70  # Massacre (highest risk)
        }
        exposure_chance = exposure_chance_map.get(power_used, 20) # Default to 20%

        # Roll for Killer exposure
        if random.randint(1, 100) <= exposure_chance:
            exposed_killer_member = killer_member
            game_state.live_players[killer_id]["is_alive"] = False
            await main_channel.send(f"**FLASH NEWS: A Killer was apprehended!**\n"
                                    f"**{exposed_killer_member.display_name} (Killer - Unit {game_state.live_players[killer_id]['unit']})** "
                                    f"was unmasked and swiftly dealt with while attempting to [thematic failed action]! Their reign of terror is over.")
            await self.check_game_end() # Check if game ends after exposure
            return # Skip victim processing if killer was exposed

        # Process victims if killer was NOT caught
        for target_id in target_ids_raw:
            if target_id in game_state.live_players and game_state.live_players[target_id]["is_alive"]:
                game_state.live_players[target_id]["is_alive"] = False
                victims.append(game_state.live_players[target_id]["member"])
        
        # Set hint type based on power used for Officer intel
        if power_used == 3: hint_type = "subtle"
        elif power_used == 4: hint_type = "framing"
        elif power_used == 5: hint_type = "massacre"

        # Deliver Officer Intel
        await self.deliver_officer_intel(victims, killer_member, hint_type, framed_id)
        
        # Announce victims publicly if any
        if victims:
            victim_names_str = ", ".join([v.display_name for v in victims])
            await main_channel.send(f"@everyone **Morning breaks over [Your Epic Game World]! The sun rises, but its warmth cannot erase the horror of the night...**\n"
                                    f"We grieve for the loss of **{victim_names_str}** who tragically perished last night.")
        else:
            await main_channel.send(f"@everyone **Morning breaks over [Your Epic Game World]! Miraculously, no one perished last night... but the tension remains.**")


    async def deliver_officer_intel(self, victims: list, killer_member: discord.Member, hint_type: str, framed_id: int = None):
        """Sends a dynamically generated hint to the Officer's private channel."""
        officer_channel = game_state.game_channels.get('Officer')
        if not officer_channel: return

        victim_names = ", ".join([v.display_name for v in victims])
        victim_units = ", ".join([str(game_state.live_players[v.id]['unit']) for v in victims])
        killer_unit = game_state.live_players[killer_member.id]['unit']

        hint_message_template = f"**Officer Intel Report - Night Cycle:**\n"
        hint_message_template += f"A tragedy has befallen {victim_names} (Unit(s): {victim_units}).\n"

        llm_prompt = f"The game theme is [Your Epic Theme, e.g., Glitch in the Matrix, Void's Whisper]. Generate a cryptic, thematic observation. The killer is from Unit {killer_unit}. "
        
        if hint_type == "standard":
            llm_prompt += f"The killer performed a standard elimination on players from unit(s) {victim_units}. Provide a moderately clear hint about the killer's unit."
            hint_message_template += "Our surveillance indicates **Unit [Killer's Unit Number]** was heavily active in the vicinity. Further analysis suggests a **[Thematic Descriptor]** originating from that unit."
        elif hint_type == "subtle":
            llm_prompt += f"The killer performed a subtle elimination on players from unit(s) {victim_units}. Provide a very vague, hard-to-interpret hint about the killer's unit."
            hint_message_template += "A faint disturbance was detected. A shadow flickered near **Unit [Killer's Unit Number]**, but the details are elusive. Proceed with extreme caution."
        elif hint_type == "framing":
            framed_member_data = game_state.live_players.get(framed_id, {})
            framed_member_name = framed_member_data.get("member").display_name if framed_member_data.get("member") else "unknown"
            framed_unit = framed_member_data.get("unit")
            llm_prompt += f"The killer from Unit {killer_unit} framed an innocent player from Unit {framed_unit}. Create a false clue implicating the framed unit, using game theme elements."
            hint_message_template += (f"Our surveillance indicates **Unit [Killer's Unit Number]** was active. However, an unusual [False Clue/Thematic Element] was found near the scene, "
                                      f"subtly implicating **Unit [Framed Player's Unit Number]**.")
        elif hint_type == "massacre":
            llm_prompt += f"The killer from Unit {killer_unit} performed a massacre, eliminating multiple players from unit(s) {victim_units}. Provide a hint indicating widespread activity and high power, using game theme elements."
            hint_message_template += (f"A powerful, widespread [Thematic Descriptor] emanated from **Unit [Killer's Unit Number]**, causing multiple casualties across units {victim_units}. "
                                      f"This was a coordinated, devastating attack.")
        
        # Call LLM to get the dynamic thematic descriptor or false clue
        llm_thematic_descriptor = await get_llm_response(llm_prompt)
        
        # Replace placeholders in the template with actual values
        final_hint_message = hint_message_template.replace("[Killer's Unit Number]", str(killer_unit))
        final_hint_message = final_hint_message.replace("[Victim's Unit Number]", victim_units) # Keep as string for multiple victims
        
        if framed_id:
             final_hint_message = final_hint_message.replace("[Framed Player's Unit Number]", str(framed_unit))

        # Inject the LLM's dynamic response
        final_hint_message = final_hint_message.replace("[Thematic Descriptor]", llm_thematic_descriptor)
        final_hint_message = final_hint_message.replace("[False Clue/Thematic Element]", llm_thematic_descriptor) # For framing too

        try:
            await officer_channel.send(final_hint_message)
        except Exception as e:
            print(f"Error sending Officer intel: {e}")


    # Listener for Killer commands
    @commands.command(name='kill')
    @commands.has_role(KILLER_ROLE_ID) # Only Killers can use this command
    async def kill_cmd(self, ctx, power_number: int, target1: discord.Member, target2: discord.Member = None, target3: discord.Member = None, framed_player: discord.Member = None):
        """Allows Killers to submit their nightly action."""
        if ctx.channel.id != game_state.game_channels.get('Killer', {}).id:
            return # Command must be in the Killer's private channel

        if game_state.current_phase != "NIGHT":
            return await ctx.send("It's not night phase. Wait for your opportunity.")
        
        if ctx.author.id not in game_state.live_players or not game_state.live_players[ctx.author.id]["is_alive"]:
            return await ctx.send("You are not an active Killer in this game.")

        # Validate power number and targets
        targets_to_kill = [target1]
        if power_number == 2: # Double Strike
            if not target2: return await ctx.send("Double Strike requires two targets.")
            targets_to_kill.append(target2)
        elif power_number == 5: # Massacre
            if not target2 or not target3: return await ctx.send("Massacre requires three targets.")
            targets_to_kill.extend([target2, target3])
        elif power_number == 4: # Framing
            if not framed_player: return await ctx.send("Framing Strike requires a player to frame.")
            # Basic check that framed player is alive and not a killer (ideally an innocent)
            if framed_player.id not in game_state.live_players or not game_state.live_players[framed_player.id]["is_alive"]:
                return await ctx.send("You can only frame an active, living player.")
            if game_state.live_players[framed_player.id]["role"] == "Killer":
                return await ctx.send("You cannot frame a fellow Killer.")

        # Validate all selected targets are alive and not the killer themselves
        for t in targets_to_kill:
            if t.id == ctx.author.id:
                return await ctx.send("You cannot target yourself.")
            if t.id not in game_state.live_players or not game_state.live_players[t.id]["is_alive"]:
                return await ctx.send(f"{t.display_name} is not a valid target (either not in game or already dead).")
        
        # If a kill order is already registered for this night, ignore subsequent ones for simplicity.
        # In a more advanced bot, you might implement a voting system among killers.
        if game_state.killer_targets:
            return await ctx.send("A kill order has already been submitted for this night. The first one takes precedence.")

        game_state.killer_targets.append(
            (ctx.author.id, [t.id for t in targets_to_kill], power_number, framed_player.id if framed_player else None)
        )
        await ctx.send(f"Your kill order ({' '.join([t.display_name for t in targets_to_kill])} with power {power_number}) has been registered!")
        
        # If a kill is submitted early, we can end the night phase immediately (optional)
        if self.game_timer_task and not self.game_timer_task.done():
            self.game_timer_task.cancel() # This will cause night_phase to proceed to process_killer_actions


    async def day_phase(self):
        """Manages the public discussion and voting phase."""
        main_channel = self.get_main_game_channel()
        
        game_state.current_phase = "DAY"
        await main_channel.send(
            f"@everyone **Now begins the Day Phase!**\n"
            f"**Debate furiously!** Who do you suspect? What have you observed? The fate of [Your Epic Game World] hangs in the balance!\n"
            f"You have **ONLY {DISCUSSION_TIME_SECONDS // 60} minute(s) {DISCUSSION_TIME_SECONDS % 60} second(s)** for open discussion. Make it count!"
        )
        
        # Start timer for discussion
        self.game_timer_task = self.bot.loop.create_task(asyncio.sleep(DISCUSSION_TIME_SECONDS))
        try:
            await self.game_timer_task
        except asyncio.CancelledError:
            pass # Discussion timer might be cancelled by an admin command to speed up

        await main_channel.send(
            f"@everyone **Time for Judgment! The fate of our world is in your hands.**\n"
            f"**All surviving players, cast your vote!**\n"
            f"To vote for an execution, use the command: `!vote @PlayerName` in this channel.\n"
            f"You have **ONLY {VOTING_TIME_SECONDS // 60} minute(s) {VOTING_TIME_SECONDS % 60} second(s)** to vote. Your vote is final!"
        )
        game_state.votes = {} # Reset votes for the new voting round
        
        # Start timer for voting
        self.game_timer_task = self.bot.loop.create_task(asyncio.sleep(VOTING_TIME_SECONDS))
        try:
            await self.game_timer_task
        except asyncio.CancelledError:
            print("Voting phase timer cancelled (e.g., all votes in or admin command).")
            # If cancelled, proceed to process votes
        
        await self.process_votes()

    # Listener for vote command
    @commands.command(name='vote')
    async def vote_cmd(self, ctx, target: discord.Member):
        """Allows living players to cast their vote for execution."""
        if ctx.channel.id != self.get_main_game_channel().id:
            return # Command must be in main game channel

        if game_state.current_phase != "DAY":
            return await ctx.send("It's not voting time!")
        
        # Check if voter is alive
        if ctx.author.id not in game_state.live_players or not game_state.live_players[ctx.author.id]["is_alive"]:
            return await ctx.send("You are not alive to vote in this game.")

        # Check if target is alive and in game
        if target.id not in game_state.live_players or not game_state.live_players[target.id]["is_alive"]:
            return await ctx.send(f"{target.display_name} is not a valid target (either not in game or already eliminated).")

        game_state.votes[ctx.author.id] = target.id
        await ctx.send(f"{ctx.author.display_name} has cast their vote for {target.display_name}.")
        
        # Optional: End voting early if all living players have voted
        # To make this robust, track living voters and compare.
        # alive_voters_count = len([p_id for p_id, p_data in game_state.live_players.items() if p_data["is_alive"] and p_data["role"] == "Voter"])
        # if len(game_state.votes) >= alive_voters_count:
        #    if self.game_timer_task and not self.game_timer_task.done():
        #        self.game_timer_task.cancel() # Cancel the voting timer
        #        print("Voting ended early as all alive voters have voted.")


    async def process_votes(self):
        """Tallies votes and announces the execution outcome."""
        main_channel = self.get_main_game_channel()
        
        if not game_state.votes:
            return await main_channel.send("No votes were cast this round. No one is executed.")

        vote_counts = {}
        for voter_id, target_id in game_state.votes.items():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

        # Determine the player with the most votes
        executed_player_id = None
        max_votes = -1
        tie_occurred = False

        for player_id, count in vote_counts.items():
            if count > max_votes:
                max_votes = count
                executed_player_id = player_id
                tie_occurred = False # Reset tie status
            elif count == max_votes:
                tie_occurred = True # A tie occurred

        await main_channel.send(f"**The votes are in! The verdict is delivered.**")
        
        # Announce vote breakdown (optional, can be very long for 60 players)
        # for player_id, count in sorted(vote_counts.items(), key=lambda item: item[1], reverse=True):
        #     player_name = game_state.live_players.get(player_id, {}).get("member").display_name
        #     await main_channel.send(f"{player_name}: {count} votes.")
        
        if tie_occurred or not executed_player_id:
            return await main_channel.send("There was a tie in votes, or no clear target. No one is executed this round.")

        executed_player_data = game_state.live_players.get(executed_player_id)
        if not executed_player_data:
            print(f"Error: Executed player data not found for ID {executed_player_id}.")
            return await main_channel.send("An error occurred during execution. No one was executed.")

        executed_member = executed_player_data["member"]
        executed_role = executed_player_data["role"]
        executed_unit = executed_player_data["unit"]
        
        game_state.live_players[executed_player_id]["is_alive"] = False # Mark as dead

        await main_channel.send(
            f"The majority has spoken. **{executed_member.display_name} (Unit {executed_unit})** has been condemned!\n"
            f"Their true role was... **{executed_role}**!\n"
        )

        if executed_role == "Killer":
            await main_channel.send("A wave of relief washes over the populace! One less threat! Hope rekindles in [Your Game World].")
        else:
            await main_channel.send("A cry of despair! An innocent life sacrificed to fear! The shadows deepen, mocking your judgment...")

        await self.check_game_end()


    async def check_game_end(self):
        """Checks if any win condition has been met and ends the game."""
        alive_killers = [p_id for p_id, data in game_state.live_players.items() if data["is_alive"] and data["role"] == "Killer"]
        alive_good_guys = [p_id for p_id, data in game_state.live_players.items() if data["is_alive"] and data["role"] in ["Officer", "Voter"]]

        main_channel = self.get_main_game_channel()

        if len(alive_killers) == 0:
            winning_team = "Good Guys"
            await main_channel.send(f"**VICTORY! The brave citizens of [Your Epic Game World] have banished the darkness! Truth prevails! The {winning_team} have won this round!**")
            await self.distribute_prizes(winning_team)
            await self.end_game_cleanup()
            game_state.is_game_running = False # End the loop
            
        elif len(alive_killers) >= len(alive_good_guys): # Killers win condition
            winning_team = "Killers"
            await main_channel.send(f"**The Grand Conspiracy has triumphed! The shadows consume [Your Epic Game World]. The {winning_team} have won this round!**")
            await self.distribute_prizes(winning_team)
            await self.end_game_cleanup()
            game_state.is_game_running = False # End the loop


    async def distribute_prizes(self, winning_team: str):
        """Calculates and distributes EP rewards to players based on game outcome."""
        main_channel = self.get_main_game_channel()
        
        alive_players_data = [data for data in game_state.live_players.values() if data["is_alive"]]
        eliminated_players_data = [data for data in game_state.live_players.values() if not data["is_alive"]]

        total_ep = game_state.prize_pool_ep
        
        # Initialize EP amounts
        winning_ep_per_player = 0
        second_place_ep_per_player = 0
        eliminated_ep_per_player = 0

        # Calculate winning share
        winning_team_members = [
            p_data for p_data in alive_players_data 
            if (p_data["role"] == "Killer" and winning_team == "Killers") or 
               (p_data["role"] in ["Officer", "Voter"] and winning_team == "Good Guys")
        ]
        if winning_team_members:
            winning_ep_per_player = (total_ep * PRIZE_WINNER_SHARE) / len(winning_team_members)

        # Calculate second place share
        second_place_team_members = [p_data for p_data in alive_players_data if p_data not in winning_team_members]
        if second_place_team_members:
            second_place_ep_per_player = (total_ep * PRIZE_SECOND_PLACE_SHARE) / len(second_place_team_members)
        
        # Calculate eliminated players share (spread across ALL eliminated players)
        if eliminated_players_data:
            eliminated_ep_per_player = (total_ep * PRIZE_ELIMINATED_SHARE) / len(eliminated_players_data)

        # Distribute and announce EP via DMs
        for player_id, data in game_state.live_players.items():
            member = data["member"]
            role = data["role"]
            ep_awarded = 0

            if data["is_alive"]:
                if (role == "Killer" and winning_team == "Killers") or (role in ["Officer", "Voter"] and winning_team == "Good Guys"):
                    ep_awarded = winning_ep_per_player
                    try:
                        await member.send(f"Congratulations! Your team won! You received **{ep_awarded:.2f} EP**.")
                    except discord.Forbidden: print(f"Could not DM {member.display_name} about EP (DM disabled).")
                else:
                    ep_awarded = second_place_ep_per_player
                    try:
                        await member.send(f"Good effort! Your team placed second. You received **{ep_awarded:.2f} EP**.")
                    except discord.Forbidden: print(f"Could not DM {member.display_name} about EP (DM disabled).")
            else: # Eliminated players
                ep_awarded = eliminated_ep_per_player
                try:
                    await member.send(f"Thanks for playing! You received a consolation prize of **{ep_awarded:.2f} EP**.")
                except discord.Forbidden: print(f"Could not DM {member.display_name} about EP (DM disabled).")
            
            # --- IMPORTANT: INTEGRATE YOUR ACTUAL EP SYSTEM HERE ---
            # This is where you would call your backend/database to update the player's EP balance.
            # Example: your_ep_system.add_ep(member.id, ep_awarded)
            print(f"Awarded {ep_awarded:.2f} EP to {member.display_name} (Role: {role}, Alive: {data['is_alive']})")
            await asyncio.sleep(0.1) # Small delay for DMs


        await main_channel.send(
            f"**GAME OVER!**\n"
            f"The **{winning_team}** have emerged victorious! All living {winning_team} members receive **{winning_ep_per_player:.2f} EP** each!\n"
            f"The {'Good Guys' if winning_team == 'Killers' else 'Killers'} players fought valiantly and receive a consolation of **{second_place_ep_per_player:.2f} EP** each.\n"
            f"All participants who were eliminated receive **{eliminated_ep_per_player:.2f} EP** for their efforts.\n\n"
            f"A total of **{total_ep} EP** was distributed in this epic battle!"
        )


    async def end_game_cleanup(self):
        """Performs all necessary cleanup actions after a game ends."""
        main_channel = self.get_main_game_channel()
        
        # Reveal all final roles
        final_role_list = "\n".join([
            f"• {data['member'].display_name} (Unit {data['unit']}): {data['role']} ({'Alive' if data['is_alive'] else 'Eliminated'})"
            for data in game_state.live_players.values()
        ])
        await main_channel.send(f"**Final Roles Revealed:**\n{final_role_list}")

        # Remove game-specific roles from players
        guild = self.get_main_game_channel().guild
        for player_id, data in game_state.live_players.items():
            member = data["member"]
            try:
                # Remove all game roles (they only have one, but safe to try all)
                if guild.get_role(OFFICER_ROLE_ID) in member.roles:
                    await member.remove_roles(guild.get_role(OFFICER_ROLE_ID), reason="Game end cleanup")
                if guild.get_role(KILLER_ROLE_ID) in member.roles:
                    await member.remove_roles(guild.get_role(KILLER_ROLE_ID), reason="Game end cleanup")
                if guild.get_role(VOTER_ROLE_ID) in member.roles:
                    await member.remove_roles(guild.get_role(VOTER_ROLE_ID), reason="Game end cleanup")
                await asyncio.sleep(0.1) # Small delay to avoid rate limits
            except Exception as e:
                print(f"Could not remove role from {member.display_name}: {e}")

        # Delete temporary channels
        for role_name, channel_obj in list(game_state.game_channels.items()): # Iterate on a copy
            try:
                await channel_obj.delete(reason="Game end cleanup")
                del game_state.game_channels[role_name] # Remove from game_channels dict
            except Exception as e:
                print(f"Could not delete channel {channel_obj.name}: {e}")
        
        game_state.reset() # Reset game state for next game
        print("Game ended and cleaned up.")

    async def end_game_early(self, reason=""):
        """Ends the current game prematurely due to error or admin command."""
        main_channel = self.get_main_game_channel()
        if main_channel:
            await main_channel.send(f"The game has ended prematurely. Reason: {reason}")
        
        game_state.is_game_running = False
        game_state.current_phase = "END" # Ensure game loop terminates

        # Cancel any active game timers/tasks
        if self.game_loop_task and not self.game_loop_task.done():
            self.game_loop_task.cancel()
        if self.game_timer_task and not self.game_timer_task.done():
            self.game_timer_task.cancel()
        
        await self.end_game_cleanup() # Perform cleanup even if game ended early


    @commands.command(name='endgame')
    @commands.has_permissions(administrator=True)
    async def end_game_cmd(self, ctx):
        """Admin command to forcibly end the current game."""
        if game_state.is_game_running:
            await ctx.send("Ending current game by admin command...")
            await self.end_game_early("Admin command.")
        else:
            await ctx.send("No game is currently running.")


# --- Setup function for the Cog ---
async def setup(bot):
    """Adds the GameCog to the bot."""
    await bot.add_cog(GameCog(bot))