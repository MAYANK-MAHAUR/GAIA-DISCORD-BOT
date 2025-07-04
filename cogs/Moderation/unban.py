import discord
from discord.ext import commands
from cogs.Moderation_Utils import log_action

class Unban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="unban", help="Unbans a member by username or ID.")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, target: str):
        banned_users = await ctx.guild.bans()

        # Try to unban by user ID
        if target.isdigit():
            user_id = int(target)
            for ban_entry in banned_users:
                if ban_entry.user.id == user_id:
                    await ctx.guild.unban(ban_entry.user)
                    await ctx.send(f"✅ Unbanned **{ban_entry.user}**.")

                    embed = discord.Embed(
                        title="🔓 Member Unbanned",
                        description=f"**{ban_entry.user}** was unbanned by **{ctx.author}**.",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text=f"User ID: {ban_entry.user.id}")
                    await log_action(self.bot, ctx.guild, embed)
                    return
            await ctx.send("❌ User ID not found in ban list.")
            return

        # Try to unban by username (new Discord format, no discriminator)
        for ban_entry in banned_users:
            if ban_entry.user.name == target:
                await ctx.guild.unban(ban_entry.user)
                await ctx.send(f"✅ Unbanned **{ban_entry.user}**.")

                embed = discord.Embed(
                    title="🔓 Member Unbanned",
                    description=f"**{ban_entry.user}** was unbanned by **{ctx.author}**.",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"User ID: {ban_entry.user.id}")
                await log_action(self.bot, ctx.guild, embed)
                return

        await ctx.send("❌ User not found in ban list.")

    @unban.error
    async def unban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to unban members.")
        else:
            await ctx.send("⚠️ Something went wrong. Please check the input and try again.")

async def setup(bot):
    await bot.add_cog(Unban(bot))
