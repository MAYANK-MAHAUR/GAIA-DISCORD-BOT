import discord
from discord.ext import commands
from cogs.Moderation_Utils import log_action

class Slowmode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="slowmode",
        help="Sets slowmode delay for a specified channel or the current channel in seconds."
    )
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, channel: discord.TextChannel = None, seconds: int = None):
        target_channel = channel if channel else ctx.channel

        if seconds is None and channel is not None:
            await ctx.send("⚠️ When specifying a channel, you must also provide the number of seconds.")
            return

        if seconds is None and channel is None:
            await ctx.send("⚠️ Please provide the number of seconds for slowmode (e.g., `!slowmode 10` or `!slowmode #channel 10`).")
            return
        
        if seconds is None and isinstance(channel, int):
            seconds = channel
            target_channel = ctx.channel
            channel = None

        if not 0 <= seconds <= 21600:
            await ctx.send("⚠️ Please provide a value between **0** and **21600** seconds.")
            return

        try:
            await target_channel.edit(slowmode_delay=seconds)
            
            if seconds == 0:
                await ctx.send(f"⏳ Slowmode has been **disabled** in {target_channel.mention}.")
            else:
                await ctx.send(f"⏳ Slowmode in {target_channel.mention} is now set to **{seconds} seconds**.")

            embed = discord.Embed(
                title="⏳ Slowmode Updated",
                description=f"Slowmode in {target_channel.mention} was set to **{seconds} seconds** by **{ctx.author}**.",
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Channel ID: {target_channel.id}")
            await log_action(self.bot, ctx.guild, embed)

        except discord.Forbidden:
            await ctx.send(f"🚫 I don't have permission to manage channels in {target_channel.mention}.")
        except Exception as e:
            await ctx.send(f"❌ An unexpected error occurred: {e}")

    @slowmode.error
    async def slowmode_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to manage channels.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("⚠️ Invalid arguments. Please ensure you're providing a valid channel and a number for seconds (e.g., `!slowmode #general 10` or `!slowmode 5`).")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("⚠️ You're missing required arguments. Usage: `!slowmode [channel] <seconds>`.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

async def setup(bot):
    await bot.add_cog(Slowmode(bot))