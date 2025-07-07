import discord
import json
import os
import Utilities
from discord.ext import commands
from cogs.Moderation_Utils import SendDM, check_user_perms, log_action

WARN_FILE = "data/warnings.json"
LOG_CHANNEL_ID = 1390372032751079454

def load_warnings():
    if not os.path.exists(WARN_FILE):
        with open(WARN_FILE, "w") as f:
            json.dump({}, f)
    with open(WARN_FILE, "r") as f:
        return json.load(f)

def save_warnings(data):
    with open(WARN_FILE, "w") as f:
        json.dump(data, f, indent=4)

class Warn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="warn", help="Warn a user. 3 warnings = ban.")
    async def warn(self, ctx, member: discord.Member, *, reason=None):
        if not await check_user_perms(ctx, "ban"):
            return

        warnings = load_warnings()
        user_id = str(member.id)
        warnings[user_id] = warnings.get(user_id, 0) + 1
        save_warnings(warnings)

        await SendDM(f"You were warned in {ctx.guild.name}. Reason: {reason or 'No reason provided.'}", member)
        await ctx.send(f"⚠️ {member.mention} has been warned. Total warnings: {warnings[user_id]}")

        embed = discord.Embed(title="⚠️ Member Warned", color=discord.Color.yellow())
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Moderator", value=ctx.author, inline=False)
        embed.add_field(name="Reason", value=reason or "No reason provided.", inline=False)
        embed.add_field(name="Total Warnings", value=warnings[user_id])
        await log_action(self.bot, ctx.guild, embed)

        if warnings[user_id] >= 3:
            await ctx.send(f"🚨 {member.mention} has 3 warnings and will be banned.")
            await member.ban(reason="Reached 3 warnings")
            del warnings[user_id]
            save_warnings(warnings)

            ban_embed = discord.Embed(title="🚨 Auto-Banned", color=discord.Color.red())
            ban_embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
            ban_embed.add_field(name="Reason", value="Reached 3 warnings")
            await log_action(self.bot, ctx.guild, ban_embed)

    @commands.command(name="checkwarn", help="Check how many warnings a member has.")
    async def checkwarn(self, ctx, member: discord.Member):
        warnings = load_warnings()
        count = warnings.get(str(member.id), 0)
        await ctx.send(f"⚠️ {member.display_name} has **{count}** warning(s).")

async def setup(bot):
    await bot.add_cog(Warn(bot))
