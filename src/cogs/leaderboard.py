from datetime import UTC, datetime, timedelta
from math import sqrt
from secrets import randbelow

import discord
from discord.ext import commands, tasks
from sqlalchemy import select, update

from src.database.database import MemberLevel, Session


def get_total_xp_for_level(level: int) -> int:
    if level <= 0:
        return 0
    return 25 * (level**2) + 75 * level + 25 * (((level - 1)**2) // 4)

def get_level(xp: int) -> tuple:
    if xp <= 0:
        return 0, 0, 100

    level = int(sqrt(xp / 31.25))
    if xp < get_total_xp_for_level(level):
        level -= 1

    xp_for_current = get_total_xp_for_level(level)
    progress = xp - xp_for_current
    xp_for_next_level = get_total_xp_for_level(level+1) - xp_for_current

    return (level, progress, xp_for_next_level)

async def generate_xp_leaderboard(ctx: discord.ApplicationContext, page: int = 1):
    async with Session() as session:
        stmt = select(MemberLevel).where(MemberLevel.guild_id == ctx.guild_id, MemberLevel.vc_time > 0).order_by(MemberLevel.xp.desc())
        result = await session.execute(stmt)
        members = result.scalars().all()

    paginated = members[10*(page - 1):10*page]
    response_list = []
    for index, member in enumerate(paginated):
        level, progress, xp_for_next_level = get_level(member.xp)
        level_progress_percent = progress / xp_for_next_level
        progress_bar: str = "█" * round(level_progress_percent * 15)
        progress_bar = progress_bar.ljust(15, "▒")
        response_list.append(f"### **{index+1+10*(page-1)}.** <@{member.id}> - Level {level} ({progress} / {xp_for_next_level}xp)\n{progress_bar} **{level_progress_percent * 100:.1f}%**")
    embed = discord.Embed(
        description=f"## {ctx.guild.name} Leaderboard\n" + "\n".join(response_list),
        color=0xFA9C1D
    )
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar)
    return embed


class LeaderboardCommands(commands.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @commands.slash_command(
        name="leaderboard",
        description=""
    )
    async def level(self, ctx: discord.ApplicationContext) -> None:
        embed = await generate_xp_leaderboard(ctx)
        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(LeaderboardCommands(bot))
