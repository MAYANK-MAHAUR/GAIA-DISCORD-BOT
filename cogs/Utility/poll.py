import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import asyncio

class PollView(discord.ui.View):
    def __init__(self, options, timeout, multiple_choice):
        super().__init__(timeout=timeout)
        self.votes = {option: [] for option in options}
        self.multiple_choice = multiple_choice
        self.options = options
        self.message = None
        self.question = ""

        for option in options:
            self.add_item(PollButton(label=option, parent=self))

    def disable_all(self):
        for item in self.children:
            item.disabled = True

    def get_results(self):
        return "\n".join(f"**{opt}** - {len(voters)} votes" for opt, voters in self.votes.items()) or "No votes recorded."

    async def update_embed(self):
        if self.message:
            desc = f"**{self.question}**\n\n"
            desc += "\n".join(f" 1. {opt} — `{len(self.votes[opt])} votes`" for opt in self.options)
            embed = discord.Embed(title="📊 Poll (Live)", description=desc, color=0x3498db)
            embed.set_footer(text="Poll is running...")
            await self.message.edit(embed=embed, view=self)

class PollButton(discord.ui.Button):
    def __init__(self, label, parent):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if not self.parent.multiple_choice:
            for voters in self.parent.votes.values():
                if user_id in voters:
                    voters.remove(user_id)

        if user_id not in self.parent.votes[self.label]:
            self.parent.votes[self.label].append(user_id)
            await interaction.response.send_message(f"You voted for **{self.label}**.", ephemeral=True)
            await self.parent.update_embed()
        else:
            await interaction.response.send_message("❗ You've already voted for this option.", ephemeral=True)

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_polls = {}

    @app_commands.command(name="poll", description="Create a poll")
    @app_commands.describe(
        question="The poll question.",
        option1="First option (optional)",
        option2="Second option (optional)",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
        time="Duration in seconds (default: 60)"
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: Optional[str] = None,
        option2: Optional[str] = None,
        option3: Optional[str] = None,
        option4: Optional[str] = None,
        time: Optional[int] = 60
    ):
        await interaction.response.defer()

        options = [opt for opt in [option1, option2, option3, option4] if opt]
        if not options:
            options = ["Yes", "No"]
            multiple = False
        elif len(options) < 2:
            return await interaction.followup.send("⚠️ At least two options required for a custom poll.", ephemeral=True)
        else:
            multiple = True

        view = PollView(options, timeout=time, multiple_choice=multiple)
        view.question = question

        embed = discord.Embed(
            title="📊 Poll Started!",
            description=f"**{question}**\n\n" + "\n".join(f"1. **{opt}**" for opt in options),
            color=0x3498db
        )
        embed.set_footer(text=f"Poll will close in {time} seconds. Vote now!")
        msg = await interaction.followup.send(embed=embed, view=view, wait=True)
        view.message = msg
        self.active_polls[msg.id] = view

        await asyncio.sleep(time)

        if msg.id in self.active_polls:
            view.disable_all()
            await msg.edit(view=view)
            result_embed = discord.Embed(
                title="📊 Poll Results",
                description=f"**{question}**\n\n{view.get_results()}",
                color=0x2ecc71
            )
            await interaction.followup.send(embed=result_embed)
            del self.active_polls[msg.id]

    @app_commands.command(name="closepoll", description="Manually close the most recent active poll in this channel")
    async def closepoll(self, interaction: discord.Interaction):
        for message_id in sorted(self.active_polls.keys(), reverse=True):
            try:
                message = await interaction.channel.fetch_message(message_id)
                view = self.active_polls[message_id]
                view.disable_all()
                await message.edit(view=view)
                embed = discord.Embed(title="📊 Poll Closed", description=view.get_results(), color=0xe67e22)
                await interaction.response.send_message(embed=embed)
                del self.active_polls[message_id]
                return
            except:
                continue
        await interaction.response.send_message("❌ No active poll found in this channel.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Poll(bot))
