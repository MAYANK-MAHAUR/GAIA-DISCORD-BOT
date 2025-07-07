import discord
from discord.ext import commands
from discord import app_commands
from cogs.Moderation_Utils import log_action

ALLOWED_ROLES = ["Admin", "Moderator"]  

class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="role", help="Add or remove a role from one or more members.\nUsage: !role @User1 @User2 RoleName")
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, *args):
    
        if not any(role.name in ALLOWED_ROLES for role in ctx.author.roles):
            return await ctx.send("🚫 You don't have permission to use this command.")

        if len(args) < 2:
            return await ctx.send("⚠️ Usage: `!role @User1 @User2 ... RoleName`")

        members = [m for m in ctx.message.mentions if isinstance(m, discord.Member)]
        role_name = " ".join(arg for arg in args if arg not in [m.mention for m in members])

        
        role = None
        if ctx.message.role_mentions:
            role = ctx.message.role_mentions[0]
        else:
            role = discord.utils.get(ctx.guild.roles, name=role_name)

        if not role:
            return await ctx.send("⚠️ Please mention or enter a valid role name.")
        if not members:
            return await ctx.send("⚠️ Please mention at least one valid member.")

       
        if role >= ctx.guild.me.top_role:
            return await ctx.send("⚠️ I can't manage that role due to role hierarchy.")

        added, removed = [], []

        for member in members:
            try:
                if role in member.roles:
                    await member.remove_roles(role)
                    removed.append(member.mention)
                    action = "removed"
                else:
                    await member.add_roles(role)
                    added.append(member.mention)
                    action = "added"

                
                embed = discord.Embed(
                    title="🛠️ Role Updated",
                    description=f"{ctx.author.mention} {action} role `{role.name}` {'from' if action == 'removed' else 'to'} {member.mention}",
                    color=discord.Color.gold()
                )
                embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                embed.add_field(name="Member", value=member.mention, inline=True)
                embed.add_field(name="Role", value=role.name, inline=True)
                embed.set_footer(text=f"User ID: {member.id}")
                await log_action(self.bot, ctx.guild, embed)

            except Exception:
                await ctx.send(f"❌ Could not update role for {member.mention}.")

        msg = ""
        if added:
            msg += f"✅ Added `{role.name}` to: {', '.join(added)}\n"
        if removed:
            msg += f"✅ Removed `{role.name}` from: {', '.join(removed)}"

        await ctx.send(msg or "⚠️ No changes made.")

    @role.error
    async def role_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to manage roles.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("⚠️ Please mention valid users and a role.")
        else:
            await ctx.send("❌ Something went wrong.")

    @app_commands.command(name="createrole", description="Create a new role with a given name.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def createrole(self, interaction: discord.Interaction, name: str):
        guild = interaction.guild

        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("🚫 You don't have permission to use this command.", ephemeral=True)

       
        if discord.utils.get(guild.roles, name=name):
            return await interaction.response.send_message(f"⚠️ A role named `{name}` already exists.", ephemeral=True)

        try:
            new_role = await guild.create_role(name=name, reason=f"Created by {interaction.user}")
            await interaction.response.send_message(f"✅ Role `{name}` created successfully.")

            embed = discord.Embed(
                title="📌 Role Created",
                description=f"{interaction.user.mention} created a new role `{name}`.",
                color=discord.Color.green()
            )
            embed.add_field(name="Created By", value=interaction.user.mention)
            embed.add_field(name="Role Name", value=name)
            embed.set_footer(text=f"User ID: {interaction.user.id}")
            await log_action(self.bot, guild, embed)

        except discord.Forbidden:
            await interaction.response.send_message("🚫 I don't have permission to create roles.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to create role: `{e}`", ephemeral=True)

    @createrole.error
    async def createrole_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("🚫 You don't have permission to manage roles.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Something went wrong while creating the role.", ephemeral=True)


    @commands.command(name="deleterole", help="Delete a role by name or mention.\nUsage: !deleterole @Role or RoleName")
    @commands.has_permissions(manage_roles=True)
    async def deleterole(self, ctx, *, role_input: str):
        if not any(role.name in ALLOWED_ROLES for role in ctx.author.roles):
            return await ctx.send("🚫 You don't have permission to use this command.")

        if ctx.message.role_mentions:
            role = ctx.message.role_mentions[0]
        else:
            role = discord.utils.get(ctx.guild.roles, name=role_input)

        if not role:
            return await ctx.send(f"⚠️ No role found for `{role_input}`.")

        try:
            await role.delete(reason=f"Deleted by {ctx.author}")
            await ctx.send(f"🗑️ Role `{role.name}` deleted successfully.")

            embed = discord.Embed(
                title="🗑️ Role Deleted",
                description=f"{ctx.author.mention} deleted the role `{role.name}`.",
                color=discord.Color.red()
                )
            embed.add_field(name="Deleted By", value=ctx.author.mention)
            embed.add_field(name="Role Name", value=role.name)
            embed.set_footer(text=f"User ID: {ctx.author.id}")
            await log_action(self.bot, ctx.guild, embed)

        except discord.Forbidden:
            await ctx.send("🚫 I don't have permission to delete that role.")
        except Exception as e:
            await ctx.send(f"❌ Failed to delete role: `{e}`")


async def setup(bot):
    await bot.add_cog(Role(bot))
