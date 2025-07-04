import discord
from discord.ext import commands
from cogs.Moderation_Utils import log_action

class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="role", help="Add or remove a role from a member.")
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, member: discord.Member, *, role: discord.Role):
        # Prevent managing roles higher than bot's top role
        if role >= ctx.guild.me.top_role:
            await ctx.send("⚠️ I can't manage that role due to role hierarchy.")
            return

        action = ""
        if role in member.roles:
            await member.remove_roles(role)
            action = "Removed"
        else:
            await member.add_roles(role)
            action = "Added"

        await ctx.send(f"✅ {action} role `{role.name}` {'from' if action == 'Removed' else 'to'} {member.mention}.")

        # Logging embed
        embed = discord.Embed(
            title="🛠️ Role Updated",
            description=f"{ctx.author.mention} {action.lower()} role `{role.name}` {'from' if action == 'Removed' else 'to'} {member.mention}",
            color=discord.Color.gold()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Role", value=role.name, inline=True)
        embed.set_footer(text=f"User ID: {member.id}")
        await log_action(self.bot, ctx.guild, embed)

    @role.error
    async def role_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to manage roles.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("⚠️ Please mention a valid user and role.")
        else:
            await ctx.send("❌ Something went wrong.")

async def setup(bot):
    await bot.add_cog(Role(bot))
