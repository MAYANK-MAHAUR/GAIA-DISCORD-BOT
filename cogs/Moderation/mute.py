import discord
import Utilities
from discord.ext import commands
from cogs.Moderation_Utils import check_user_perms, check_bot_perms, log_action

class Mute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mute", help="Mute a user (prevents sending messages).")
    async def mute(self, ctx, member: discord.Member, *, reason=None):
        if not await check_user_perms(ctx, "mute") or not await check_bot_perms(ctx, member, "mute"):
            return

        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted", reason="Mute command used")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False)

        await member.add_roles(mute_role, reason=reason)
        await ctx.send(f"🔇 {member.mention} has been muted.")

        embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.dark_gray())
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Moderator", value=ctx.author, inline=False)
        embed.add_field(name="Reason", value=reason or "No reason provided.", inline=False)
        await log_action(self.bot, ctx.guild, embed)

async def setup(bot):
    await bot.add_cog(Mute(bot))
