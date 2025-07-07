import discord
from discord.ext import commands
from cogs.Moderation_Utils import log_action

class ChangeNick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="changenick", help="Change a member's nickname.")
    @commands.has_permissions(manage_nicknames=True)
    async def changenick(self, ctx, member: discord.Member, *, new_nick: str = None):
        old_nick = member.display_name
        try:
            await member.edit(nick=new_nick)
        except discord.Forbidden:
            await ctx.send("❌ I don’t have permission to change that member’s nickname.")
            return

        if new_nick:
            await ctx.send(f"✅ Changed nickname of {member.mention} to `{new_nick}`.")
        else:
            await ctx.send(f"✅ Reset nickname of {member.mention}.")

        embed = discord.Embed(
            title="✏️ Nickname Changed",
            description=f"**{ctx.author}** changed nickname for {member.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="Old Nickname", value=f"`{old_nick}`", inline=True)
        embed.add_field(name="New Nickname", value=f"`{new_nick or member.name}`", inline=True)
        embed.set_footer(text=f"User ID: {member.id}")
        await log_action(self.bot, ctx.guild, embed)

    @changenick.error
    async def changenick_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to manage nicknames.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("⚠️ Please mention a valid user.")
        else:
            await ctx.send("❌ Something went wrong.")

async def setup(bot):
    await bot.add_cog(ChangeNick(bot))
