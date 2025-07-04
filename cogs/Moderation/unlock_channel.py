import discord
from discord.ext import commands
from cogs.Moderation_Utils import log_action

class Unlock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="unlock", help="Unlocks the current channel for @everyone.")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        channel = ctx.channel
        everyone_role = ctx.guild.default_role

        overwrite = channel.overwrites_for(everyone_role)
        if overwrite.send_messages is None or overwrite.send_messages is True:
            await ctx.send("🔓 This channel is already unlocked.")
            return

        overwrite.send_messages = True
        await channel.set_permissions(everyone_role, overwrite=overwrite)

        await ctx.send("🔓 Channel has been unlocked for @everyone.")

        embed = discord.Embed(
            title="🔓 Channel Unlocked",
            description=f"**{ctx.author}** unlocked {channel.mention}.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await log_action(self.bot, ctx.guild, embed)

    @unlock.error
    async def unlock_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to manage channels.")
        else:
            await ctx.send("❌ Something went wrong.")

async def setup(bot):
    await bot.add_cog(Unlock(bot))
