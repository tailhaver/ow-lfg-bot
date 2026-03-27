from math import ceil

import discord
from sqlalchemy import select, update

from src.database.database import Member, Server, Session


async def get_mythic_prism_role_list(ctx: discord.ApplicationContext, page: int = 1):
    try:
        author = getattr(ctx, "author", ctx.user)
        async with Session() as db_session:
            stmt = select(Server).where(Server.id == ctx.guild_id)
            result = await db_session.execute(stmt)
            server_data = result.scalars().one_or_none()
            if server_data is not None:
                roles: dict = server_data.mythic_prism_roles
            else:
                raise Exception
            paginated = list(roles.items())[20 * (page - 1) : 20 * page]

        embed = discord.Embed(
            description=f"### Current roles:\n{'\n'.join([f'-# <@&{k}>: <:mythic_prism:1483233288951955538> {v["cost"]}' for k, v in paginated])}",
            color=0xFA9C1D,
        )
        embed.set_author(name=author.name, icon_url=author.avatar)
        embed.set_footer(text=f"Page {page} / {ceil(len(paginated) / 20)}")
        return {"embed": embed, "view": MythicView(page, ceil(len(paginated) / 20))}
    except Exception:
        embed = discord.Embed(
            description="❌ Unable to get server from the database!", color=0xFA9C1D
        )
        embed.set_author(name=author.name, icon_url=author.avatar)
        return {"embed": embed}


class RoleSelect(discord.ui.Select):
    def __init__(self, roles: list, prism_count: int = 0) -> None:
        options = []
        for role_id, data in roles:
            if not isinstance(data["cost"], int):
                continue
            options.append(
                discord.SelectOption(label=f"{data['name']}", value=str(role_id))
            )
        if len(options) == 0:
            options.append(
                discord.SelectOption(label="test lorem ipsum etc", value="testtest")
            )

        super().__init__(
            placeholder="Select role to purchase...",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
            disabled=prism_count < 10,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_role_id = self.values[0]
        async with Session() as session:
            stmt = select(Server).where(Server.id == interaction.guild_id)
            result = await session.execute(stmt)
            server_data = result.scalars().one_or_none()
            if server_data is not None:
                roles: dict = server_data.mythic_prism_roles
            else:
                raise Exception
            stmt = select(Member).where(
                Member.guild_id == interaction.guild_id,
                Member.id == interaction.user.id,
            )
            result = await session.execute(stmt)
            member = result.scalars().one_or_none()
            if member is None:
                raise Exception
            spent_prisms = 0 if member.spent_prisms is None else member.spent_prisms
            stmt = (
                update(Member)
                .where(
                    Member.guild_id == interaction.guild_id,
                    Member.id == interaction.user.id,
                )
                .values(
                    spent_prisms=spent_prisms + roles[selected_role_id]["cost"],
                    mythic_inventory=member.mythic_inventory + [selected_role_id],
                )
            )
            await session.execute(stmt)
            await session.commit()

        if self.view:
            await self.view.update_view(interaction)


class MythicView(discord.ui.View):
    def __init__(
        self,
        current_page: int,
        max_pages: int,
        prism_count: int = None,
        roles: list = None,
        function=get_mythic_prism_role_list,  # noqa: ANN001
    ) -> None:
        super().__init__()
        self.current_page = current_page
        self.max_pages = max_pages
        self.function = function
        self.prism_count = prism_count
        self.roles = roles

        if self.roles:
            self.add_item(RoleSelect(roles, prism_count))

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
        await self.update_view(interaction)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="◀️", row=0)
    async def left_callback(
        self, _: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.current_page = max(self.current_page - 1, 1)
        await self.update_view(interaction)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="▶️", row=0)
    async def right_callback(
        self, _: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.current_page = min(self.current_page + 1, self.max_pages)
        await self.update_view(interaction)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⏩", row=0)
    async def double_right_callback(
        self, _: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.current_page = self.max_pages
        await self.update_view(interaction)

    async def update_view(self, interaction: discord.Interaction):
        data = await self.function(interaction, self.current_page)

        await interaction.response.edit_message(embed=data["embed"], view=data["view"])
