import json
import os
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

POINTS_FILE = os.path.join("Data", "global_points.json")
POINTS_DISPLAY_LIMIT = 10
LEADERBOARD_CHANNEL_ID = int(os.getenv("LEADERBOARD_CHANNEL_ID"))

os.makedirs("Data", exist_ok=True)

class PointsLeaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _load_points(self):
        if os.path.exists(POINTS_FILE):
            try:
                with open(POINTS_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: {POINTS_FILE} is corrupted or empty. Starting with empty points data.")
        return {}

    def _save_points(self, data):
        with open(POINTS_FILE, "w") as f:
            json.dump(data, f, indent=4)

    async def add_points(self, user_id, amount):
        data = self._load_points()
        user_id = str(user_id)
        data[user_id] = data.get(user_id, 0) + amount
        self._save_points(data)

    async def get_points(self, user_id):
        data = self._load_points()
        return data.get(str(user_id), 0)

    async def reset_leaderboard(self):
        self._save_points({})

    async def get_leaderboard(self, limit=POINTS_DISPLAY_LIMIT):
        data = self._load_points()
        return sorted(data.items(), key=lambda x: x[1], reverse=True)[:limit]

    @discord.app_commands.command(name='showpoints', description='Displays the global points leaderboard.')
    async def show_points_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer() 
        top_players = await self.get_leaderboard()

        if not top_players:
            await interaction.followup.send("📭 No points data available yet.")
            return

        embed = discord.Embed(
            title="🌐 Global Points Leaderboard",
            description=f"Top {len(top_players)} players by points:",
            color=discord.Color.teal()
        )

        for i, (user_id, points) in enumerate(top_players, 1):
            user = interaction.guild.get_member(int(user_id)) or await self.bot.fetch_user(int(user_id))
            embed.add_field(name=f"#{i}. {user.display_name if user else 'Unknown'}", value=f"Points: `{points}`", inline=False)

        await interaction.followup.send(embed=embed)

    @discord.app_commands.command(name='resetpoints', description='Resets all global points.')
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def reset_points_command(self, interaction: discord.Interaction):
        confirm_embed = discord.Embed(
            title="⚠️ CONFIRM GLOBAL POINTS RESET ⚠️",
            description="Are you absolutely sure you want to reset **ALL** global points? This action is irreversible.",
            color=discord.Color.red()
        )
        confirm_embed.add_field(name="To Confirm:", value="Type `confirm reset` within 30 seconds.", inline=False)

        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel and m.content.lower() == "confirm reset"

        try:
            confirmation_message = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("Leaderboard reset cancelled: No confirmation received in time.", ephemeral=True)
            return

        await self.reset_leaderboard()
        await interaction.followup.send("✅ Global points leaderboard has been reset.")

    @discord.app_commands.command(name='giverolepoints', description='Assigns a role to top leaderboard users.')
    @discord.app_commands.checks.has_permissions(manage_roles=True)
    async def assign_roles_to_leaders(self, interaction: discord.Interaction, role_name: str):
        await interaction.response.defer(ephemeral=True) 
        top_players = await self.get_leaderboard()
        role = discord.utils.get(interaction.guild.roles, name=role_name)

        if not role:
            try:
                role = await interaction.guild.create_role(name=role_name)
                await interaction.followup.send(f"✅ Role `{role.name}` created and will be assigned to top users.")
            except discord.Forbidden:
                await interaction.followup.send("🚫 I don't have permission to create roles.")
                return

        if interaction.guild.me.top_role <= role:
            await interaction.followup.send("🚫 My role is not high enough to assign this role. Please adjust role hierarchy.")
            return

        assigned = []
        for user_id, _ in top_players:
            member = interaction.guild.get_member(int(user_id)) or await interaction.guild.fetch_member(int(user_id))
            if member and role not in member.roles:
                try:
                    await member.add_roles(role, reason="Top of the global points leaderboard")
                    assigned.append(member.mention)
                except Exception as e:
                    await interaction.followup.send(f"⚠️ Could not assign role to {member.display_name}: {e}")

        if assigned:
            await interaction.followup.send(f"🏅 Assigned role `{role.name}` to: {', '.join(assigned)}")
        else:
            await interaction.followup.send("ℹ️ No users were assigned the role, they might already have it or not be in the server.")

async def setup(bot):
    await bot.add_cog(PointsLeaderboard(bot))
   