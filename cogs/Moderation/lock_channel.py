import discord
from discord.ext import commands
from cogs.Moderation_Utils import log_action

class Lock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="lock", help="Locks the current channel for @everyone.")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        channel = ctx.channel
        everyone_role = ctx.guild.default_role

        overwrite = channel.overwrites_for(everyone_role)
        if overwrite.send_messages is False:
            await ctx.send("🔒 This channel is already locked.")
            return

        overwrite.send_messages = False
        await channel.set_permissions(everyone_role, overwrite=overwrite)

        await ctx.send("🔒 Channel has been locked for @everyone.")

        embed = discord.Embed(
            title="🔒 Channel Locked",
            description=f"**{ctx.author}** locked {channel.mention}.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await log_action(self.bot, ctx.guild, embed)

    @lock.error
    async def lock_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to manage channels.")
        else:
            await ctx.send("❌ Something went wrong.")

async def setup(bot):
    await bot.add_cog(Lock(bot))
