import discord
from discord.ext import commands
from cogs.Moderation_Utils import log_action

class Slowmode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="slowmode", help="Sets slowmode delay for the current channel in seconds.")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        if seconds < 0 or seconds > 21600:
            await ctx.send("⚠️ Please provide a value between **0** and **21600** seconds.")
            return

        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"⏳ Slowmode is now set to **{seconds} seconds**.")

        embed = discord.Embed(
            title="⏳ Slowmode Updated",
            description=f"Slowmode in {ctx.channel.mention} was set to **{seconds} seconds** by **{ctx.author}**.",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Channel ID: {ctx.channel.id}")
        await log_action(self.bot, ctx.guild, embed)

    @slowmode.error
    async def slowmode_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to manage channels.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("⚠️ Please enter a valid number of seconds.")
        else:
            await ctx.send("❌ Something went wrong.")

async def setup(bot):
    await bot.add_cog(Slowmode(bot))
