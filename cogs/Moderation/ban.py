import discord
import cogs
from discord.ext import commands
from cogs.Moderation_Utils import SendDM, check_user_perms, check_bot_perms, log_action

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ban", help="Ban a member from the server.")
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        if not await check_user_perms(ctx, "ban") or not await check_bot_perms(ctx, member, "ban"):
            return

        await SendDM(f"You were banned from {ctx.guild.name}. Reason: {reason or 'No reason provided.'}", member)
        await member.ban(reason=reason)

        embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Moderator", value=ctx.author, inline=False)
        embed.add_field(name="Reason", value=reason or "No reason provided.", inline=False)
        await ctx.send(f"✅ Banned {member.mention}")
        await log_action(self.bot, ctx.guild, embed)

async def setup(bot):
    await bot.add_cog(Ban(bot))
