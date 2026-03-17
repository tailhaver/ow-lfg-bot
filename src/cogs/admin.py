from math import ceil

import discord
from discord.ext import commands
from sqlalchemy import select, update

from src.bot.logging import send_log
from src.database.database import Server, Session


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
            description=f"### Current roles:\n{'\n'.join([f'-# <@&{k}>: <:mythic_prism:1483233288951955538> {v}' for k, v in paginated])}",
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


class MythicView(discord.ui.View):
    def __init__(
        self,
        current_page: int,
        max_pages: int,
        function=get_mythic_prism_role_list,  # noqa: ANN001
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


class AdminCommands(commands.Cog):
    admin_group = discord.SlashCommandGroup(
        "admin",
        "administrator commands :)",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @admin_group.command(
        name="set_voice_category",
        description="Sets the default voice channel category for creation commands.",
    )
    @discord.default_permissions(administrator=True)
    @discord.option(
        "category",
        type=discord.SlashCommandOptionType.channel,
        channel_types=[discord.ChannelType.category],
    )
    async def admin_move_voice_category_command(
        self, ctx: discord.ApplicationContext, category: discord.CategoryChannel
    ) -> None:
        previous_channel_id = None
        try:
            async with Session() as db_session:
                stmt = select(Server).where(Server.id == ctx.guild_id)
                result = await db_session.execute(stmt)
                server_data = result.scalars().one_or_none()
                if (
                    server_data is not None
                    and server_data.voice_channel_category is not None
                ):
                    previous_channel_id = server_data.voice_channel_category

                stmt = (
                    update(Server)
                    .where(Server.id == ctx.guild_id)
                    .values(voice_channel_category=category.id)
                )
                await db_session.execute(stmt)
                await db_session.commit()

            embed = discord.Embed(
                title=f"✅ Successfully moved voice channel category to {category.mention}!",
                color=0xFA9C1D,
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception:
            embed = discord.Embed(
                title="❌ Unable to move voice channel category.", color=0xFA9C1D
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        if not server_data.logging_enabled or server_data.log_channel is None:
            return

        if previous_channel_id is not None:
            embed = discord.Embed(
                title="Voice channel category changed",
                description=f"Moved from <#{previous_channel_id}> to {category.mention}",
                color=0xFA9C1D,
            )
        else:
            embed = discord.Embed(
                title="Voice channel category set",
                description=f"Set to {category.mention}",
                color=0xFA9C1D,
            )

        await send_log(ctx, server_data.log_channel, embed)

    @admin_group.command(
        name="toggle_logging",
        description="Enable, disable, or toggle logging.",
    )
    @discord.default_permissions(administrator=True)
    @discord.option(
        "state",
        type=discord.SlashCommandOptionType.string,
        choices=["enable", "disable", "toggle"],
        default="toggle",
    )
    async def admin_toggle_logging_command(
        self, ctx: discord.ApplicationContext, state: str
    ) -> None:
        try:
            async with Session() as db_session:
                stmt = select(Server).where(Server.id == ctx.guild_id)
                result = await db_session.execute(stmt)
                server_data = result.scalars().one_or_none()
                if server_data is not None:
                    match state:
                        case "enable":
                            stmt = (
                                update(Server)
                                .where(Server.id == ctx.guild_id)
                                .values(logging_enabled=True)
                            )
                        case "disable":
                            stmt = (
                                update(Server)
                                .where(Server.id == ctx.guild_id)
                                .values(logging_enabled=False)
                            )
                        case _:
                            stmt = (
                                update(Server)
                                .where(Server.id == ctx.guild_id)
                                .values(logging_enabled=not server_data.logging_enabled)
                            )
                    await db_session.execute(stmt)
                    await db_session.commit()

            embed = discord.Embed(
                title=f"✅ Successfully {state}d logging.", color=0xFA9C1D
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception:
            embed = discord.Embed(
                title=f"❌ Unable to {state} logging.", color=0xFA9C1D
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        if not server_data.logging_enabled or server_data.log_channel is None:
            return

        embed = discord.Embed(title=f"Logging {state}d", color=0xFA9C1D)
        await send_log(ctx, server_data.log_channel, embed=embed)

    @admin_group.command(
        name="set_logging_channel",
        description="Move the logging channel for Jetpack Cat",
    )
    @discord.default_permissions(administrator=True)
    @discord.option(
        "channel",
        type=discord.SlashCommandOptionType.channel,
        channel_types=[discord.ChannelType.text],
    )
    async def admin_set_logging_channel_command(
        self, ctx: discord.ApplicationContext, channel: discord.TextChannel
    ) -> None:
        try:
            async with Session() as db_session:
                stmt = select(Server).where(Server.id == ctx.guild_id)
                result = await db_session.execute(stmt)
                server_data = result.scalars().one_or_none()
                if server_data is not None:
                    stmt = (
                        update(Server)
                        .where(Server.id == ctx.guild_id)
                        .values(log_channel=int(channel.id))
                    )
                    await db_session.execute(stmt)
                    await db_session.commit()

            embed = discord.Embed(
                description=f"✅ Successfully set logging channel to {channel.mention}",
                color=0xFA9C1D,
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception:
            embed = discord.Embed(
                description="❌ Unable to change logging channel.", color=0xFA9C1D
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        if not server_data.logging_enabled or server_data.log_channel is None:
            return

        embed = discord.Embed(
            description=f"Logging channel set to {channel.mention}", color=0xFA9C1D
        )
        await send_log(ctx, server_data.log_channel, embed)

    @admin_group.command(
        name="add_mythic_role",
        description="Add a Mythic role to the shop",
    )
    @discord.default_permissions(administrator=True)
    @discord.option(
        "role",
        type=discord.SlashCommandOptionType.role,
    )
    @discord.option("cost", type=int, required=False, default=10)
    async def add_mythic_role(
        self, ctx: discord.ApplicationContext, role: discord.Role, cost: int
    ) -> None:
        try:
            async with Session() as db_session:
                stmt = select(Server).where(Server.id == ctx.guild_id)
                result = await db_session.execute(stmt)
                server_data = result.scalars().one_or_none()
                if server_data is not None:
                    roles: dict = server_data.mythic_prism_roles
                    roles[role.id] = cost
                    stmt = (
                        update(Server)
                        .where(Server.id == ctx.guild_id)
                        .values(mythic_prism_roles=roles)
                    )
                    await db_session.execute(stmt)
                    await db_session.commit()

            embed = discord.Embed(
                description=f"### ✅ Successfully added {role.mention} to the shop!\nCurrent roles:\n{'\n'.join([f'-# <@&{k}>: <:mythic_prism:1483233288951955538> {v}' for k, v in roles.items()])}",
                color=0xFA9C1D,
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                description=f"❌ Unable to add role to the shop!\n-# exception: {e}",
                color=0xFA9C1D,
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

    @admin_group.command(
        name="remove_mythic_role",
        description="Remove a Mythic role from the shop (but not inventories)",
    )
    @discord.default_permissions(administrator=True)
    @discord.option(
        "role",
        type=discord.SlashCommandOptionType.role,
    )
    async def remove_mythic_role(
        self, ctx: discord.ApplicationContext, role: discord.Role
    ) -> None:
        try:
            async with Session() as db_session:
                stmt = select(Server).where(Server.id == ctx.guild_id)
                result = await db_session.execute(stmt)
                server_data = result.scalars().one_or_none()
                if server_data is not None:
                    roles: dict = server_data.mythic_prism_roles
                    roles.pop(str(role.id))
                    stmt = (
                        update(Server)
                        .where(Server.id == ctx.guild_id)
                        .values(mythic_prism_roles=roles)
                    )
                    await db_session.execute(stmt)
                    await db_session.commit()

            embed = discord.Embed(
                description=f"### ✅ Successfully removed {role.mention} from the shop!",
                color=0xFA9C1D,
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except KeyError:
            embed = discord.Embed(
                description="❌ That role isn't in the shop!", color=0xFA9C1D
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception:
            embed = discord.Embed(
                description="❌ Unable to remove role from the shop!", color=0xFA9C1D
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @admin_group.command(
        name="change_mythic_price",
        description="Change the price of a Mythic role in the shop",
    )
    @discord.default_permissions(administrator=True)
    @discord.option(
        "role",
        type=discord.SlashCommandOptionType.role,
    )
    @discord.option("cost", type=int, required=False, default=10)
    async def change_mythic_price(
        self, ctx: discord.ApplicationContext, role: discord.Role, cost: int
    ) -> None:
        try:
            async with Session() as db_session:
                stmt = select(Server).where(Server.id == ctx.guild_id)
                result = await db_session.execute(stmt)
                server_data = result.scalars().one_or_none()
                if server_data is not None:
                    roles: dict = server_data.mythic_prism_roles
                    if role.id not in roles:
                        raise KeyError
                    roles[str(role.id)] = cost
                    stmt = (
                        update(Server)
                        .where(Server.id == ctx.guild_id)
                        .values(mythic_prism_roles=roles)
                    )
                    await db_session.execute(stmt)
                    await db_session.commit()

            embed = discord.Embed(
                description=f"### ✅ Changed the cost of {role.mention} to {cost}!",
                color=0xFA9C1D,
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except KeyError:
            embed = discord.Embed(
                description="❌ That role isn't in the shop!", color=0xFA9C1D
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                description=f"❌ Unable to change role cost!\n-# exception: {e}",
                color=0xFA9C1D,
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

    @admin_group.command(
        name="list_mythic_roles",
        description="List all Mythic roles currently in the shop",
    )
    @discord.default_permissions(administrator=True)
    async def list_mythic_roles(self, ctx: discord.ApplicationContext) -> None:
        await ctx.respond(**await get_mythic_prism_role_list(ctx, 1), ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(AdminCommands(bot))
