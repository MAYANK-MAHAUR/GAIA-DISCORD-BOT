import discord
import Utilities
from discord.ext import commands
from cogs.Moderation_Utils import SendDM, check_user_perms, check_bot_perms, log_action

class Kick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="kick", help="Kick a member from the server.")
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        if not await check_user_perms(ctx, "kick") or not await check_bot_perms(ctx, member, "kick"):
            return

        await SendDM(f"You were kicked from {ctx.guild.name}. Reason: {reason or 'No reason provided.'}", member)
        await member.kick(reason=reason)

        embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange())
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Moderator", value=ctx.author, inline=False)
        embed.add_field(name="Reason", value=reason or "No reason provided.", inline=False)
        await ctx.send(f"✅ Kicked {member.mention}")
        await log_action(self.bot, ctx.guild, embed)

async def setup(bot):
    await bot.add_cog(Kick(bot))
