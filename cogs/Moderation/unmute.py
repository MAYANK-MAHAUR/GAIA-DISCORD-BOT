import discord
from discord.ext import commands
from cogs.Moderation_Utils import check_user_perms, check_bot_perms, log_action

class Unmute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="unmute", help="Unmute a user (restores their ability to talk).")
    async def unmute(self, ctx, member: discord.Member):
        if not await check_user_perms(ctx, "mute") or not await check_bot_perms(ctx, member, "mute"):
            return

        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role or mute_role not in member.roles:
            await ctx.send("❌ This user is not muted.")
            return

        await member.remove_roles(mute_role, reason="Unmuted by moderator.")
        await ctx.send(f"🔊 {member.mention} has been unmuted.")

        embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green())
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Moderator", value=ctx.author, inline=False)
        await log_action(self.bot, ctx.guild, embed)

    @unmute.error
    async def unmute_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to unmute members.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("⚠️ Please mention a valid member.")
        else:
            await ctx.send("❌ An unexpected error occurred.")

async def setup(bot):
    await bot.add_cog(Unmute(bot))
