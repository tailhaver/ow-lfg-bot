from math import ceil

import discord
from discord.ext import commands
from sqlalchemy import select

from src.cogs.leveling import get_level
from src.database.database import Member, Server, Session
from src.views import MythicView


async def get_mythic_prism_count(ctx: discord.ApplicationContext) -> int:
    author = getattr(ctx, "author", ctx.user)
    async with Session() as db_session:
        stmt = select(Member).where(
            Member.guild_id == ctx.guild_id, Member.id == author.id
        )
        result = await db_session.execute(stmt)
        member = result.scalars().one_or_none()
        level = get_level(member.xp)
        spent_prisms = 0 if member.spent_prisms is None else member.spent_prisms
        return (level[0] // 5) * 10 - spent_prisms


async def get_mythic_prism_role_list(ctx: discord.ApplicationContext, page: int = 1):
    author = getattr(ctx, "author", ctx.user)
    async with Session() as db_session:
        stmt = select(Server).where(Server.id == ctx.guild_id)
        result = await db_session.execute(stmt)
        server_data = result.scalars().one_or_none()
        if server_data is not None:
            roles: dict = server_data.mythic_prism_roles
        else:
            raise Exception
        stmt = select(Member).where(
            Member.guild_id == ctx.guild_id, Member.id == author.id
        )
        result = await db_session.execute(stmt)
        member = result.scalars().one_or_none()
        paginated = list(roles.items())[20 * (page - 1) : 20 * page]
        paginated = [
            (role[0], {"cost": "(owned)", "name": role[1]["name"]})
            if role[0] in member.mythic_inventory
            else role
            for role in paginated
        ]
        paginated.sort(key=lambda role: role[1] == "owned", reverse=True)
    return paginated


async def create_shop_embed(
    ctx: discord.ApplicationContext, page: int = 1
) -> discord.Embed:
    roles_list = await get_mythic_prism_role_list(ctx, page)
    max_pages = ceil(len(roles_list) / 20)
    prism_count = await get_mythic_prism_count(ctx)
    description = f"""
### Mythic Shop
{"\n".join([f"<@&{role[0]}> - " + (f"<:mythic_prism:1483233288951955538> {role[1]['cost']}" if isinstance(role[1]["cost"], int) else role[1]["cost"]) for role in roles_list])}
-# You have <:mythic_prism:1483233288951955538> {prism_count}
"""
    embed = discord.Embed(description=description.strip(), color=0xFA9C1D)
    author = getattr(ctx, "author", ctx.user)
    embed.set_author(name=author.name, icon_url=author.avatar)
    embed.set_footer(text=f"Page {page} / {max_pages}")
    return {
        "embed": embed,
        "view": MythicView(page, max_pages, prism_count, roles_list, create_shop_embed),
    }


async def create_inventory_embed(
    ctx: discord.ApplicationContext, page: int = 1
) -> dict[str, discord.Embed | discord.ui.View]:
    author = getattr(ctx, "author", ctx.user)
    async with Session() as db_session:
        stmt = select(Member).where(
            Member.guild_id == ctx.guild_id, Member.id == author.id
        )
        result = await db_session.execute(stmt)
        member = result.scalars().one_or_none()
        if member is None:
            raise Exception
        paginated = list(member.mythic_inventory)[20 * (page - 1) : 20 * page]
        paginated = [
            (role[0], {"cost": "(owned)", "name": role[1]["name"]})
            if role[0] in member.mythic_inventory
            else role
            for role in paginated
        ]
        paginated.sort(key=lambda role: role[1] == "owned", reverse=True)
    max_pages = ceil(len(paginated) / 20)
    prism_count = await get_mythic_prism_count(ctx)
    description = f"""
### Mythic Inventory
{"\n".join([f"<@&{role}>" for role in paginated])}
-# You have <:mythic_prism:1483233288951955538> {prism_count}
    """
    embed = discord.Embed(description=description.strip(), color=0xFA9C1D)
    author = getattr(ctx, "author", ctx.user)
    embed.set_author(name=author.name, icon_url=author.avatar)
    embed.set_footer(text=f"Page {page} / {max_pages}")
    return {"embed": embed, "view": MythicView(page, max_pages, create_inventory_embed)}


async def get_roles_autocomplete(ctx: discord.AutocompleteContext):
    async with Session() as db_session:
        stmt = select(Server).where(Server.id == ctx.interaction.guild_id)
        result = await db_session.execute(stmt)
        server_data = result.scalars().one_or_none()
        if server_data is not None:
            roles: dict = server_data.mythic_prism_roles
        else:
            raise Exception
        stmt = select(Member).where(
            Member.guild_id == ctx.interaction.guild_id,
            Member.id == ctx.interaction.user.id,
        )
        result = await db_session.execute(stmt)
        member = result.scalars().one_or_none()
        if member is None:
            raise Exception
        return [
            discord.OptionChoice(name=roles[role]["name"], value=role)
            for role in member.mythic_inventory
            if role in roles.keys()
        ]


class MythicCommands(commands.Cog):
    mythic_group = discord.SlashCommandGroup(
        "mythic", "for all commands relating to mythics!"
    )

    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @mythic_group.command(
        name="shop", description="View all mythic roles available for purchase"
    )
    async def mythic_shop(self, ctx: discord.ApplicationContext) -> None:
        await ctx.respond(**await create_shop_embed(ctx), ephemeral=True)

    @mythic_group.command(
        name="inventory", description="See which mythic roles you have purchased!"
    )
    async def mythic_inventory(self, ctx: discord.ApplicationContext) -> None:
        await ctx.respond(**await create_inventory_embed(ctx, 1), ephemeral=True)

    @mythic_group.command(
        name="equip",
        description="Equip a Mythic role from one in your inventory, or unequip your current mythic.",
    )
    @discord.option(
        "role",
        description="Select a role from your inventory. Alternatively, leave blank to unequip.",
        required=False,
        autocomplete=discord.utils.basic_autocomplete(get_roles_autocomplete),
    )
    async def equip_role(self, ctx: discord.ApplicationContext, role) -> None:
        async with Session() as db_session:
            stmt = select(Server).where(Server.id == ctx.guild_id)
            result = await db_session.execute(stmt)
            server_data = result.scalars().one_or_none()
            if server_data is not None:
                roles: dict = server_data.mythic_prism_roles
            else:
                raise Exception
        equipped_roles = [
            user_role for user_role in ctx.author.roles if str(user_role.id) in roles
        ]
        if len(equipped_roles) > 0:
            await ctx.author.remove_roles(*equipped_roles)
        if role is None:
            if len(equipped_roles) == 0:
                description = "### You do not have any role equipped!"
            else:
                description = "### ✅ Successfully unequipped your mythic role!"
            embed = discord.Embed(description=description, color=0xFA9C1D)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar)
            await ctx.respond(embed=embed, ephemeral=True)
            return
        await ctx.author.add_roles(ctx.guild.get_role(int(role)))
        embed = discord.Embed(
            description=f"### ✅ Successfully equipped <@&{role}>!", color=0xFA9C1D
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar)
        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(MythicCommands(bot))
