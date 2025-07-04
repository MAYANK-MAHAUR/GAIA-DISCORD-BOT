import discord
import Utilities
from discord.ext import commands
from cogs.Moderation_Utils import check_user_perms, log_action

class Purge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="purge", help="Deletes a specified number of messages from the channel.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        if amount < 1 or amount > 100:
            return await ctx.send("⚠️ Please provide a number between 1 and 100.")

        await ctx.channel.purge(limit=amount + 1)  # +1 includes the purge command message

        embed = discord.Embed(
            title="🧹 Messages Purged",
            description=f"**{ctx.author}** purged **{amount}** messages in {ctx.channel.mention}.",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"User ID: {ctx.author.id}")
        await log_action(self.bot, ctx.guild, embed)

        confirm = await ctx.send(f"✅ Deleted {amount} messages.", delete_after=5)

    @purge.error
    async def purge_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to purge messages.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("⚠️ Please enter a valid number of messages to purge.")

async def setup(bot):
    await bot.add_cog(Purge(bot))
