from math import ceil, sqrt

import discord
from discord.ext import commands
from sqlalchemy import select

from src.database.database import MemberLevel, Session


def get_total_xp_for_level(level: int) -> int:
    if level <= 0:
        return 0
    return 25 * (level**2) + 75 * level + 25 * (((level - 1) ** 2) // 4)


def get_level(xp: int) -> tuple:
    if xp <= 0:
        return 0, 0, 100

    level = int(sqrt(xp / 31.25))
    if xp < get_total_xp_for_level(level):
        level -= 1

    xp_for_current = get_total_xp_for_level(level)
    progress = xp - xp_for_current
    xp_for_next_level = get_total_xp_for_level(level + 1) - xp_for_current

    return (level, progress, xp_for_next_level)


async def generate_xp_leaderboard(ctx: discord.ApplicationContext, page: int = 1):
    async with Session() as session:
        stmt = (
            select(MemberLevel)
            .where(MemberLevel.guild_id == ctx.guild_id, MemberLevel.xp > 0)
            .order_by(MemberLevel.xp.desc())
        )
        result = await session.execute(stmt)
        members = result.scalars().all()

    paginated = members[10 * (page - 1) : 10 * page]
    response_list = []
    for index, member in enumerate(paginated):
        level, progress, xp_for_next_level = get_level(member.xp)
        level_progress_percent = progress / xp_for_next_level
        progress_bar: str = "█" * round(level_progress_percent * 15)
        progress_bar = progress_bar.ljust(15, "▒")
        response_list.append(
            f"**{index + 1 + 10 * (page - 1)}.** <@{member.id}> - Level {level} ({progress} / {xp_for_next_level}xp)\n{progress_bar} **{level_progress_percent * 100:.1f}%**"
        )
    embed = discord.Embed(description="\n".join(response_list), color=0xFA9C1D)
    author = getattr(ctx, "author", ctx.user)
    embed.set_author(name=author.name, icon_url=author.avatar)
    embed.set_footer(text=f"Page {page} / {ceil(len(members) / 10)}")
    return {"embed": embed, "view": LeaderboardView(1, ceil(len(members) / 10))}


def format_time(seconds: float) -> str:
    time_str = ""
    if days := seconds // 86400 >= 1:
        time_str += f"{days} days "
    seconds -= days * 86400
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    time_str += f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    return time_str


async def generate_voice_leaderboard(ctx: discord.ApplicationContext, page: int = 1):
    async with Session() as session:
        stmt = (
            select(MemberLevel)
            .where(MemberLevel.guild_id == ctx.guild_id, MemberLevel.vc_time > 0)
            .order_by(MemberLevel.vc_time.desc())
        )
        result = await session.execute(stmt)
        members = result.scalars().all()

    paginated = members[10 * (page - 1) : 10 * page]
    response_list = []
    for index, member in enumerate(paginated):
        response_list.append(
            f"**{index + 1 + 10 * (page - 1)}.** <@{member.id}> - {format_time(member.vc_time)}"
        )
    embed = discord.Embed(description="\n".join(response_list), color=0xFA9C1D)
    author = getattr(ctx, "author", ctx.user)
    embed.set_author(name=author.name, icon_url=author.avatar)
    embed.set_footer(
        text=f"^Call time is updated upon leaving voice.\nPage {page} / {ceil(len(members) / 10)}"
    )
    return {
        "embed": embed,
        "view": LeaderboardView(1, ceil(len(members) / 10), generate_voice_leaderboard),
    }


class LeaderboardView(discord.ui.View):
    def __init__(
        self,
        current_page: int,
        max_pages: int,
        function=generate_xp_leaderboard,  # noqa: ANN001
    ) -> None:
        super().__init__()
        self.current_page = current_page
        self.max_pages = max_pages
        self.function = function
        self.button_callback()

    def button_callback(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.emoji:
                if child.emoji.name in ["⏪", "◀️"]:
                    child.disabled = self.current_page <= 1
                elif child.emoji.name in ["▶️", "⏩"]:
                    child.disabled = self.current_page >= self.max_pages

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⏪", row=0)
    async def double_left_callback(
        self, _: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.current_page = 1
        self.button_callback()
        await interaction.response.edit_message(
            embed=(await self.function(interaction, self.current_page))["embed"],
            view=self,
        )

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="◀️", row=0)
    async def left_callback(
        self, _: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.current_page = max(self.current_page - 1, 1)
        self.button_callback()
        await interaction.response.edit_message(
            embed=(await self.function(interaction, self.current_page))["embed"],
            view=self,
        )

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="▶️", row=0)
    async def right_callback(
        self, _: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.current_page = min(self.current_page + 1, self.max_pages)
        self.button_callback()
        await interaction.response.edit_message(
            embed=(await self.function(interaction, self.current_page))["embed"],
            view=self,
        )

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⏩", row=0)
    async def double_right_callback(
        self, _: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.current_page = self.max_pages
        self.button_callback()
        await interaction.response.edit_message(
            embed=(await self.function(interaction, self.current_page))["embed"],
            view=self,
        )


class LeaderboardCommands(commands.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @commands.slash_command(name="leaderboard", description="")
    @discord.option(
        "type",
        type=discord.SlashCommandOptionType.string,
        choices=["level", "vc"],
        default="level",
    )
    async def leaderboard(self, ctx: discord.ApplicationContext, type: str) -> None:
        match type:
            case "level":
                function = generate_xp_leaderboard
            case _:
                function = generate_voice_leaderboard
        await ctx.respond(ephemeral=True, **await function(ctx))


def setup(bot: discord.Bot):
    bot.add_cog(LeaderboardCommands(bot))
