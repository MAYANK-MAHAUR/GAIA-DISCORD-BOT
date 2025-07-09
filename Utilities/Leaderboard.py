import json
import os
import discord
from discord.ext import commands
from datetime import datetime
import asyncio
from dotenv import load_dotenv


load_dotenv()

LEADERBOARD_CHANNEL_ID = int(os.getenv('LEADERBOARD_CHANNEL_ID'))
LEADERBOARD_FILE = os.path.join("Data", "leaderboard.json")
LAST_MESSAGE_FILE = os.path.join("Data", "last_leaderboard_messages.json")

os.makedirs("Data", exist_ok=True)

LAST_LEADERBOARD_MESSAGES = {}

MAX_LEADERBOARD_ENTRIES = 10

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _load_last_messages(self):
        if os.path.exists(LAST_MESSAGE_FILE):
            try:
                with open(LAST_MESSAGE_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: {LAST_MESSAGE_FILE} is corrupted or empty. Starting with empty last messages.")
                return {}
        return {}

    def _save_last_messages(self):
        with open(LAST_MESSAGE_FILE, "w") as f:
            json.dump(LAST_LEADERBOARD_MESSAGES, f, indent=4)

    def get_recent_winners(self):
        if not os.path.exists(LEADERBOARD_FILE):
            return []
        try:
            with open(LEADERBOARD_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {LEADERBOARD_FILE} is corrupted or empty. Starting with empty recent leaderboard.")
            return []

    def save_recent_winners(self, winners):
        with open(LEADERBOARD_FILE, "w") as f:
            json.dump(winners, f, indent=4)

    def add_recent_winner(self, user_id, username, game_name, host_id, host_name):
        winners = self.get_recent_winners()

        user_id = str(user_id)

        if any(w["user_id"] == user_id for w in winners):
            return False, False

        new_entry = {
            "user_id": user_id,
            "username": username,
            "game_name": game_name,
            "host_id": str(host_id),
            "host_name": host_name,
            "timestamp": datetime.now().strftime("%b %d, %Y %I:%M %p")
        }

        winners.append(new_entry)
        
        if len(winners) > MAX_LEADERBOARD_ENTRIES:
            winners = winners[-MAX_LEADERBOARD_ENTRIES:]

        self.save_recent_winners(winners)
        
        is_full = len(winners) == MAX_LEADERBOARD_ENTRIES
        return True, is_full

    def is_leaderboard_full(self):
        return len(self.get_recent_winners()) >= MAX_LEADERBOARD_ENTRIES

    def reset_leaderboard(self):
        self.save_recent_winners([])

    def set_last_leaderboard_message(self, channel_id, message_id):
        LAST_LEADERBOARD_MESSAGES[str(channel_id)] = message_id
        self._save_last_messages()

    def get_last_leaderboard_message(self, channel_id):
        return LAST_LEADERBOARD_MESSAGES.get(str(channel_id))

    @commands.command(name='addwinner', help=f'Adds a winner to the recent winners leaderboard. Displays after {MAX_LEADERBOARD_ENTRIES} wins.')
    @commands.has_permissions(manage_roles=True)
    async def add_winner_command(self, ctx, winner: discord.Member, *, game_name: str):
        added, is_full = self.add_recent_winner(winner.id, winner.name, game_name, ctx.author.id, ctx.author.name)

        if added:
            if is_full:
                await ctx.send(f"✅ {winner.mention} has been added. The leaderboard is now full with {MAX_LEADERBOARD_ENTRIES} winners! Updating display...")
                leaderboard_channel = self.bot.get_channel(LEADERBOARD_CHANNEL_ID)
                if leaderboard_channel:
                    await self.update_leaderboard_display(leaderboard_channel)
                else:
                    await ctx.send(f"⚠️ Leaderboard channel (ID: {LEADERBOARD_CHANNEL_ID}) not found for automatic update. Please check the ID in your `.env` file.")
            else:
                await ctx.send(f"✅ {winner.mention} has been added to the recent winners for `{game_name}`. We need {MAX_LEADERBOARD_ENTRIES - len(self.get_recent_winners())} more winners to display the leaderboard.")
        else:
            await ctx.send(f"ℹ️ {winner.mention} is already in the current leaderboard of {MAX_LEADERBOARD_ENTRIES} winners.")

    @commands.command(name='leaderboard', help='Displays the recent winners leaderboard manually, regardless of fullness.')
    async def display_leaderboard_command(self, channel: discord.TextChannel = None):
        channel = channel 
        
        winners = self.get_recent_winners()

        if not winners:
            await channel.send("The leaderboard is currently empty.")
            return

        embed = discord.Embed(
            title="🏆 Recent Game Winners Leaderboard 🏆",
            description=f"Here are the last {len(winners)} players to win a game!",
            color=discord.Color.gold()
        )

        for i, entry in enumerate(winners, 1):
            winner_display_name = entry['username']
            
            host_member = channel.guild.get_member(int(entry['host_id']))
            host_display_name = host_member.mention if host_member else entry['host_name']

            embed.add_field(
                name=f"#{i}. **{winner_display_name}**",
                value=(f"• Game: `{entry['game_name']}`\n"
                       f"• Hosted by: {host_display_name}\n"
                       f"• When: {entry['timestamp']}"),
                inline=False
            )

        leaderboard_msg = await channel.send(embed=embed)
        if channel.id == LEADERBOARD_CHANNEL_ID:
            self.set_last_leaderboard_message(channel.id, leaderboard_msg.id)

    @commands.command(name='clearleaderboard', help='Resets the entire recent winners leaderboard and clears its display.')
    @commands.has_permissions(administrator=True)
    async def clear_leaderboard_command(self, ctx):
        self.reset_leaderboard()
        await ctx.send("✅ The recent winners leaderboard has been cleared.")
        
        leaderboard_channel = self.bot.get_channel(LEADERBOARD_CHANNEL_ID)
        if leaderboard_channel:
            last_message_id = self.get_last_leaderboard_message(leaderboard_channel.id)
            if last_message_id:
                try:
                    old_msg = await leaderboard_channel.fetch_message(last_message_id)
                    await old_msg.delete()
                    self.set_last_leaderboard_message(leaderboard_channel.id, None)
                except discord.NotFound:
                    print("Old leaderboard message not found, probably already deleted.")
                except discord.Forbidden:
                    await ctx.send("🚫 I don't have permissions to delete old leaderboard messages in the dedicated channel.")
                except Exception as e:
                    await ctx.send(f"⚠️ Error deleting old leaderboard message: {e}")

            await self.update_leaderboard_display(leaderboard_channel)

    @commands.command(name='givewinnerroles', help=f'Assigns a specified role to all {MAX_LEADERBOARD_ENTRIES} current leaderboard winners. Only works when full.')
    @commands.has_permissions(manage_roles=True)
    async def give_winner_roles_command(self, ctx):
        role_name_to_assign = await self._winners_role_logic(ctx.channel, self.bot, lambda m: m.author == ctx.author and m.channel == ctx.channel)
        if role_name_to_assign:
            await self._giverole_logic(ctx.channel, role_name_to_assign)
            await self.clear_leaderboard_command(ctx)
        else:
            await ctx.send("❌ Role assignment process cancelled or failed.")

    async def _winners_role_logic(self, channel, bot, check):
        winners = self.get_recent_winners()
        if len(winners) < MAX_LEADERBOARD_ENTRIES:
            await channel.send(f"❌ The leaderboard is not yet full. It needs {MAX_LEADERBOARD_ENTRIES} winners to assign roles. Current: {len(winners)}.")
            return None

        await channel.send("Please enter the name of the role you want to assign to the winners:")

        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await channel.send("⏱️ Timed out waiting for role name. No role will be given.")
            return None

        role_name = msg.content.strip()
        if not role_name:
            await channel.send("⚠️ No role name entered. Skipping role creation.")
            return None

        guild = channel.guild
        try:
            existing_role = discord.utils.get(guild.roles, name=role_name)
            if existing_role:
                await channel.send(f"ℹ️ Role `{role_name}` already exists. It will be used.")
                return existing_role.name

            new_role = await guild.create_role(name=role_name)
            await channel.send(f"✅ Role `{new_role.name}` created successfully!")
            return new_role.name
        except discord.Forbidden:
            await channel.send("🚫 I don't have permission to create roles. Make sure my role is high enough in the hierarchy!")
        except Exception as e:
            await channel.send(f"⚠️ Failed to create role: {e}")
        return None

    async def _giverole_logic(self, channel, role_name: str):
        role = discord.utils.get(channel.guild.roles, name=role_name)
        if not role:
            await channel.send(f"⚠️ Role `{role_name}` not found. Make sure it exists.")
            return

        if channel.guild.me.top_role <= role:
            await channel.send(f"🚫 My role is not high enough to assign the role `{role.name}`. Please move my role higher than `{role.name}` in server settings.")
            return

        winners = self.get_recent_winners()
        assigned = []

        for entry in winners:
            user_id = int(entry["user_id"])
            member = channel.guild.get_member(user_id)
            if member is None:
                try:
                    member = await channel.guild.fetch_member(user_id)
                except discord.NotFound:
                    await channel.send(f"⚠️ User with ID `{user_id}` (`{entry['username']}`) not found in this server (they might have left). Skipping.")
                    continue
                except Exception as e:
                    await channel.send(f"⚠️ Failed to fetch user `{user_id}`: {e}. Skipping.")
                    continue

            if member is None:
                continue

            try:
                if role in member.roles:
                    continue

                await member.add_roles(role, reason="Leaderboard winner")
                assigned.append(member.mention)
            except discord.Forbidden:
                await channel.send(f"🚫 Missing permissions to add role to {member.mention}. Check my role hierarchy and permissions.")
            except Exception as e:
                await channel.send(f"⚠️ Error adding role to {member.mention}: {e}")

        if assigned:
            await channel.send(f"✅ Role `{role.name}` added to: {', '.join(assigned)}.")
        else:
            await channel.send("⚠️ No new valid winners found to assign the role, or they already had it.")

    async def update_leaderboard_display(self, channel: discord.TextChannel):
        winners = self.get_recent_winners()
        last_message_id = self.get_last_leaderboard_message(channel.id)

        embed = discord.Embed(
            title="🏆 Recent Game Winners Leaderboard 🏆",
            description=f"Here are the last {len(winners)} players to win a game!",
            color=discord.Color.gold()
        )

        if not winners:
            embed.description = "The leaderboard is currently empty."
            if embed.fields:
                embed.clear_fields()
        else:
            for i, entry in enumerate(winners, 1):
                winner_display_name = entry['username']
                
                host_member = channel.guild.get_member(int(entry['host_id']))
                host_display_name = host_member.mention if host_member else entry['host_name']

                embed.add_field(
                    name=f"#{i}. **{winner_display_name}**",
                    value=(f"• Game: `{entry['game_name']}`\n"
                           f"• Hosted by: {host_display_name}\n"
                           f"• When: {entry['timestamp']}"),
                    inline=False
                )

        try:
            if last_message_id:
                try:
                    message = await channel.fetch_message(last_message_id)
                    await message.edit(embed=embed)
                    print(f"Updated existing leaderboard message in {channel.name} ({channel.id}).")
                except discord.NotFound:
                    new_msg = await channel.send(embed=embed)
                    self.set_last_leaderboard_message(channel.id, new_msg.id)
                    print(f"Old leaderboard message not found, sent new one in {channel.name} ({channel.id}).")
                except discord.Forbidden:
                    print(f"Error: Missing permissions to edit messages in leaderboard channel {channel.name} ({channel.id}). Sending a new one.")
                    new_msg = await channel.send(embed=embed)
                    self.set_last_leaderboard_message(channel.id, new_msg.id)
            else:
                new_msg = await channel.send(embed=embed)
                self.set_last_leaderboard_message(channel.id, new_msg.id)
                print(f"No last leaderboard message stored, sent new one in {channel.name} ({channel.id}).")
        except Exception as e:
            print(f"CRITICAL ERROR updating leaderboard display in channel {channel.name} ({channel.id}): {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Leaderboard cog is ready. Leaderboard channel ID: {LEADERBOARD_CHANNEL_ID}")
        global LAST_LEADERBOARD_MESSAGES
        LAST_LEADERBOARD_MESSAGES = self._load_last_messages()
        print(f"Loaded last leaderboard messages: {LAST_LEADERBOARD_MESSAGES}")

        leaderboard_channel = self.bot.get_channel(LEADERBOARD_CHANNEL_ID)
        if leaderboard_channel and self.is_leaderboard_full():
             print(f"Leaderboard is full on startup, updating display in {leaderboard_channel.name}.")
             await self.update_leaderboard_display(leaderboard_channel)
        elif leaderboard_channel:
             print(f"Leaderboard not full on startup ({len(self.get_recent_winners())}/{MAX_LEADERBOARD_ENTRIES} winners).")


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))