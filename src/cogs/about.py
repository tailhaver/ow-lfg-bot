import os

import discord
import git
from discord.ext import commands


class AboutCommand(commands.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @commands.slash_command(name="about", description="Learn about the bot!")
    async def about(self, ctx: discord.ApplicationContext) -> None:
        repo = git.Repo(os.getcwd())
        branch = repo.head.reference
        description = f"""
### Jetpack Cat - Commit {branch.commit.hexsha[:7]}
-# {branch.commit.message.split("\n")[0]}

Custom made for the *[Kittywatch](<https://jetpack.cat>)* Discord server
Serving **{len(self.bot.guilds)}** guilds

-# Source: https://github.com/tailhaver/ow-lfg-bot
"""
        embed = discord.Embed(description=description.strip(), color=0xFA9A1D)
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(
            text="made with ♥ by taggie tailhaver",
            icon_url=(await self.bot.application_info()).owner.avatar.url,
        )
        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(AboutCommand(bot))
