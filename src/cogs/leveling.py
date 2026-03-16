from datetime import UTC, datetime, timedelta
from math import sqrt
from secrets import randbelow

import discord
from discord.ext import commands, tasks
from sqlalchemy import select, update

from src.database.database import Member, Session


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

async def create_user_level(guild_id: int, member_id: int):
    async with Session() as session:
        level = Member(
            guild_id=guild_id,
            id=member_id,
            xp=0,
            vc_time=0
        )
        session.add(level)
        await session.commit()
        await session.refresh(level)
    return level

async def generate_level_embed(ctx: discord.ApplicationContext):
    async with Session() as session:
        stmt = select(Member).where(Member.guild_id == ctx.guild_id, Member.id == ctx.author.id)
        result = await session.execute(stmt)
        level_info = result.scalars().one_or_none()

    if level_info is None:
        level_info = await create_user_level(ctx.guild_id, ctx.author.id)

    level, progress, xp_for_next_level = get_level(level_info.xp)

    level_progress_percent = progress / xp_for_next_level
    progress_bar: str = "█" * round(level_progress_percent * 15)
    progress_bar = progress_bar.ljust(15, "▒")

    description = f"""
### Level {int(level)}
{progress_bar} **{level_progress_percent * 100:.1f}%**
{progress} / {xp_for_next_level}xp"""
    embed = discord.Embed(
        description=description.strip(),
        color=0xFA9C1D
    )
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar)
    return embed

class LevellingCommands(commands.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot
        self.add_voice_call_time.start()

    def cog_unload(self):
        self.add_voice_call_time.cancel()

    @commands.slash_command(
        name="level",
        description=""
    )
    async def level(self, ctx: discord.ApplicationContext) -> None:
        embed = await generate_level_embed(ctx)
        await ctx.respond(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(
        self, message: discord.Message
    ) -> None:
        if message is None or message.author.bot:
            return
        async with Session() as session:
            stmt = select(Member).where(Member.guild_id == message.guild.id, Member.id == message.author.id)
            result = await session.execute(stmt)
            member = result.scalars().one_or_none()
            if member is None:
                member = await create_user_level(message.guild.id, message.author.id)
            elif datetime.now(UTC) < member.next_message_xp.replace(tzinfo=UTC):
                return

            message_xp = randbelow(10) + 10
            stmt = (
                update(Member)
                .where(Member.guild_id == message.guild.id, Member.id == message.author.id)
                .values(xp=member.xp + message_xp, next_message_xp=datetime.now(UTC) + timedelta(seconds=60))
            )
            await session.execute(stmt)
            await session.commit()

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, _: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if member is None or member.bot:
            return
        async with Session() as session:
            stmt = select(Member).where(Member.guild_id == member.guild.id, Member.id == member.id)
            result = await session.execute(stmt)
            member_info = result.scalars().one_or_none()
            if member_info is None:
                member_info = await create_user_level(member.guild.id, member.id)
            if after.channel is None:
                last_vc_join = member_info.last_vc_join
                time_in_vc = (datetime.now(UTC) - member_info.last_vc_join.replace(tzinfo=UTC)).total_seconds()
                in_vc = False
            else:
                last_vc_join = datetime.now(UTC)
                time_in_vc = 0
                in_vc = True
            if member_info.in_vc and in_vc:
                return
            stmt = (
                update(Member)
                .where(Member.guild_id == member.guild.id, Member.id == member.id)
                .values(next_vc_xp=datetime.now(UTC) + timedelta(seconds=300), in_vc=in_vc, last_vc_join=last_vc_join, vc_time=member_info.vc_time + time_in_vc)
            )
            await session.execute(stmt)
            await session.commit()

    @tasks.loop(minutes=1)
    async def add_voice_call_time(self) -> None:
        async with Session() as session:
            stmt = select(Member).where(Member.in_vc)
            result = await session.execute(stmt)
            members = result.scalars().all()

            for member in members:
                if datetime.now(UTC) < member.next_vc_xp.replace(tzinfo=UTC):
                    continue
                time_in_vc = (datetime.now(UTC) - member.last_vc_join.replace(tzinfo=UTC)).total_seconds()
                half_hours_in_vc = time_in_vc // 1800 # used to add deteriorating returns for time in vc
                message_xp = randbelow(10) + 10
                stmt = (
                    update(Member)
                    .where(Member.guild_id == member.guild_id, Member.id == member.id)
                    .values(xp=member.xp + message_xp, next_vc_xp=datetime.now(UTC) + timedelta(seconds=300 + 60 * half_hours_in_vc))
                )
                await session.execute(stmt)
            await session.commit()


def setup(bot: discord.Bot):
    bot.add_cog(LevellingCommands(bot))
