import discord

LOG_CHANNEL_ID = 1390372032751079454

async def SendDM(message, member: discord.Member):
    try:
        await member.send(message)
        return True
    except discord.Forbidden:
        return False

async def check_user_perms(ctx, action: str):
    perms = ctx.author.guild_permissions
    if action == "kick" and not perms.kick_members:
        await ctx.send("🚫 You don't have permission to kick members.")
        return False
    if action == "ban" and not perms.ban_members:
        await ctx.send("🚫 You don't have permission to ban members.")
        return False
    if action == "mute" and not perms.manage_roles:
        await ctx.send("🚫 You don't have permission to mute members.")
        return False
    return True

async def check_bot_perms(ctx, member: discord.Member, action: str):
    perms = ctx.guild.me.guild_permissions
    if action == "kick" and not perms.kick_members:
        await ctx.send("❌ I don't have permission to kick members.")
        return False
    if action == "ban" and not perms.ban_members:
        await ctx.send("❌ I don't have permission to ban members.")
        return False
    if action == "mute" and not perms.manage_roles:
        await ctx.send("❌ I don't have permission to manage roles for muting.")
        return False
    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send("⚠️ I can't perform this action due to role hierarchy.")
        return False
    return True

async def log_action(bot, guild, embed):
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=embed)
