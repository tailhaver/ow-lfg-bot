import discord
from discord.ext import commands
from sqlalchemy import select, update

from src.bot.logging import send_log
from src.database.database import Server, Session

"""class VCButtons1(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="New voice channel", custom_id="new-vc-button", style=discord.ButtonStyle.primary)
    async def callback(self, button, interaction: discord.Interaction):
        await interaction.response.send_message(view=)

class VCButtonsMode(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="5v5 / Role QUeue", custom_id="new-vc-button-5v5", style=discord.ButtonStyle.primary)
    async def callback(self, button, interaction: discord.Interaction):
        await interaction.response.send_message(view=)"""


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

    """@admin_group.command(
        name="create_vc_buttons",
        description="Send a message with buttons to create a voice channel automatically",
    )
    @discord.default_permissions(administrator=True)
    @discord.option("channel", type=discord.SlashCommandOptionType.channel, channel_types=[discord.ChannelType.text])
    async def admin_create_vc_buttons_command(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel
    ) -> None:
        pass"""


def setup(bot: discord.Bot):
    bot.add_cog(AdminCommands(bot))
