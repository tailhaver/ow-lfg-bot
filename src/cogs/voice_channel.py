from datetime import UTC, datetime

import discord
from discord.ext import commands, tasks
from sqlalchemy import delete, select, update

from src.bot.logging import send_log
from src.console import logger
from src.database.database import Server, Session, VoiceChannel


async def create_vc(
    ctx: discord.ApplicationContext, mode: str, platform: str, competitive: bool = False
) -> None:
    async with Session() as db_session:
        stmt = select(VoiceChannel).where(VoiceChannel.owner == ctx.author.id)
        result = await db_session.execute(stmt)
        channels = result.scalars().one_or_none()
        if channels is not None:
            embed = discord.Embed(
                title="❌ Cannot make new voice channel!",
                description="You already have a voice channel open! Please close it manually (or wait for it to close) before opening a new one.",
                color=0xFA9C1D,
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        stmt = select(Server).where(Server.id == ctx.guild_id)
        result = await db_session.execute(stmt)
        server_data = result.scalars().one_or_none()
        if server_data.voice_channel_category is None:
            embed = discord.Embed(
                title="❌ Cannot make new voice channel!",
                description="This server has not set up a category to create voice channels in!",
                color=0xFA9C1D,
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        channel_name = f"{platform} - {'5v5' if '5v5' in mode else '6v6'} {'Competitive' if competitive else 'Quick Play'}"
        new_vc = await ctx.guild.create_voice_channel(
            name=channel_name,
            category=discord.utils.get(
                ctx.guild.categories, id=server_data.voice_channel_category
            ),
            user_limit=5 if "5v5" in mode else 6,
        )
        db_session.add(VoiceChannel(id=new_vc.id, owner=ctx.author.id))
        await db_session.commit()

    embed = discord.Embed(
        title="Temporary voice channel created",
        description=f"{new_vc.mention}",
        color=0xFA9C1D,
    )
    await ctx.respond(embed=embed, ephemeral=True)

    if not server_data.logging_enabled or server_data.log_channel is None:
        return

    embed = discord.Embed(
        title="Temporary voice channel created",
        description=f"`{channel_name}` · {new_vc.mention}",
        color=0xFA9C1D,
    )
    await send_log(ctx, server_data.log_channel, embed)


class VCCommands(commands.Cog):
    create_voice_channel = discord.SlashCommandGroup(
        "vc", "Create a new temporary voice channel"
    )

    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot
        self.check_all_channels_to_prune.start()
        self.prune_stale_channels.start()

    def cog_unload(self):
        self.check_all_channels_to_prune.cancel()
        self.prune_stale_channels.cancel()

    @create_voice_channel.command(
        name="competitive",
        description="Create a temporary competitive mode voice channel",
    )
    @discord.option(
        "mode",
        description="which mode are you queueing?",
        type=discord.SlashCommandOptionType.string,
        choices=["Role Queue/5v5", "Open Queue/6v6"],
    )
    @discord.option(
        "platform",
        description="are you on pc or console?",
        type=discord.SlashCommandOptionType.string,
        choices=["PC", "Console"],
    )
    async def create_competitive_vc_command(
        self, ctx: discord.ApplicationContext, mode: str, platform: str
    ) -> None:
        await create_vc(ctx, mode, platform, True)

    @create_voice_channel.command(
        name="quickplay",
        description="Create a temporary competitive mode voice channel",
    )
    @discord.option(
        "mode",
        description="which mode are you queueing?",
        type=discord.SlashCommandOptionType.string,
        choices=["Role Queue/5v5", "Open Queue/6v6"],
    )
    @discord.option(
        "platform",
        description="are you on pc or console?",
        type=discord.SlashCommandOptionType.string,
        choices=["PC", "Console"],
    )
    async def create_quickplay_vc_command(
        self, ctx: discord.ApplicationContext, mode: str, platform: str
    ) -> None:
        await create_vc(ctx, mode, platform, False)

    @create_voice_channel.command(
        name="delete", description="Delete your currently open voice channel"
    )
    @discord.option(
        "channel",
        description="Channel to delete. (Admin only)",
        type=discord.SlashCommandOptionType.channel,
        channel_types=[discord.ChannelType.voice],
        default=None,
    )
    @discord.option(
        "force",
        description="Forcefully close the channel, even if people are still in it.",
        type=discord.SlashCommandOptionType.boolean,
        default=False,
    )
    async def delete_vc_command(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.VoiceChannel,
        force: bool,
    ) -> None:
        channel_id = None
        async with Session() as db_session:
            if channel is not None and not ctx.author.guild_permissions.administrator:
                stmt = select(VoiceChannel).where(VoiceChannel.id == channel)
                result = await db_session.execute(stmt)
                channel_resp = result.scalars().one_or_none()
                if channel_resp.owner != int(ctx.author.id):
                    embed = discord.Embed(
                        title="❌ Cannot close that voice channel!",
                        description="You do not have ownership of this channel, or you are not authorized to delete other channels.",
                        color=0xFA9C1D,
                    )
                    await ctx.respond(embed=embed, ephemeral=True)
                    return
                channel_id = channel.id
            elif channel is None:
                stmt = select(VoiceChannel).where(
                    VoiceChannel.owner == int(ctx.author.id)
                )
                result = await db_session.execute(stmt)
                channel_resp = result.scalars().one_or_none()
                if channel_resp is None:
                    embed = discord.Embed(
                        title="❌ You do not have any channels open!", color=0xFA9C1D
                    )
                    await ctx.respond(embed=embed, ephemeral=True)
                    return
                channel_id = channel_resp.id
            else:
                stmt = select(VoiceChannel).where(VoiceChannel.id == int(channel.id))
                result = await db_session.execute(stmt)
                channel = result.scalars().one_or_none()
                if channel is None:
                    embed = discord.Embed(
                        title="❌ That channel is not a temporary channel!",
                        color=0xFA9C1D,
                    )
                    await ctx.respond(embed=embed, ephemeral=True)
                    return
                channel_id = channel.id

            try:
                channel: discord.VoiceChannel = ctx.bot.get_channel(channel_id)
                member_count = len(channel.members)
            except Exception:
                embed = discord.Embed(
                    title="❌ An error occurred trying to delete the channel! What!",
                    color=0xFA9C1D,
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            if member_count > 0 and not force:
                embed = discord.Embed(
                    title="❌ This channel is not empty!",
                    description="You can run this command with Force=True if you truly want to kill it.",
                    color=0xFA9C1D,
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            await channel.delete()
            stmt = delete(VoiceChannel).where(VoiceChannel.id == channel.id)
            await db_session.execute(stmt)

            stmt = select(Server).where(Server.id == ctx.guild_id)
            result = await db_session.execute(stmt)
            server_data = result.scalars().one_or_none()

            await db_session.commit()

        embed = discord.Embed(
            title="✅ Successfully deleted voice channel!", color=0xFA9C1D
        )
        await ctx.respond(embed=embed, ephemeral=True)

        if not server_data.logging_enabled or server_data.log_channel is None:
            return

        embed = discord.Embed(
            title="Temporary voice channel manually deleted",
            description=f"<#{channel_id}>",
            color=0xFA9C1D,
        )
        await send_log(ctx, server_data.log_channel, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, _: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if before.channel == after.channel:
            return
        channel: discord.VoiceChannel

        target = after.channel or before.channel
        if not target:
            return

        async with Session() as db_session:
            stmt = select(VoiceChannel).where(VoiceChannel.id == target.id)
            result = await db_session.execute(stmt)
            is_temp = result.scalars().one_or_none()
            if not is_temp:
                return

            if after.channel is None:  # leaving any vc
                if (channel := self.bot.get_channel(before.channel.id)) is None:
                    logger.warning(
                        f"Bot is not able to access voice channel with ID {before.channel.id}!"
                    )
                    return
                stmt = (
                    update(VoiceChannel)
                    .where(VoiceChannel.id == channel.id)
                    .values(
                        has_user=len(channel.members) > 0, last_leave=datetime.now(UTC)
                    )
                )
            else:  # joining any vc
                if (channel := self.bot.get_channel(after.channel.id)) is None:
                    logger.warning(
                        f"Bot is not able to access voice channel with ID {after.channel.id}!"
                    )
                    return
                stmt = (
                    update(VoiceChannel)
                    .where(VoiceChannel.id == channel.id)
                    .values(has_user=1)
                )

            await db_session.execute(stmt)
            await db_session.commit()

    @tasks.loop(minutes=2)
    async def prune_stale_channels(self) -> None:
        async with Session() as db_session:
            stmt = select(VoiceChannel).where(VoiceChannel.has_user == 0)
            result = await db_session.execute(stmt)
            channels = result.scalars().all()

            for channel in channels:
                if (
                    datetime.now(UTC) - channel.last_leave.replace(tzinfo=UTC)
                ).total_seconds() < 300:
                    continue
                try:
                    voice_channel: discord.VoiceChannel = await self.bot.fetch_channel(
                        channel.id
                    )
                except discord.NotFound:
                    stmt = delete(VoiceChannel).where(VoiceChannel.id == channel.id)
                    await db_session.execute(stmt)
                    continue
                stmt = select(Server).where(Server.id == voice_channel.guild.id)
                result = await db_session.execute(stmt)
                server_data = result.scalars().one_or_none()

                try:
                    voice_members = len(voice_channel.members)
                except AttributeError:
                    voice_members = 0

                if voice_members > 0:
                    stmt = (
                        update(VoiceChannel)
                        .where(VoiceChannel.id == channel.id)
                        .values(has_user=1)
                    )
                    await db_session.execute(stmt)
                    continue
                await voice_channel.delete()
                stmt = delete(VoiceChannel).where(VoiceChannel.id == channel.id)
                await db_session.execute(stmt)

                if not server_data.logging_enabled or server_data.log_channel is None:
                    continue

                embed = discord.Embed(
                    title="Temporary voice channel automatically deleted",
                    description=f"<#{channel.id}>",
                    color=0xFA9C1D,
                )
                embed.set_footer(text=datetime.now(UTC).strftime("%d/%m/%Y · %H:%M"))

                await self.bot.get_channel(server_data.log_channel).send(embed=embed)
            await db_session.commit()

    @tasks.loop(hours=1)
    async def check_all_channels_to_prune(self):
        async with Session() as db_session:
            stmt = select(VoiceChannel)
            result = await db_session.execute(stmt)
            channels = result.scalars().all()

            for channel in channels:
                if (
                    datetime.now(UTC) - channel.last_leave.replace(tzinfo=UTC)
                ).total_seconds() < 300:
                    continue
                try:
                    voice_channel: discord.VoiceChannel = await self.bot.fetch_channel(
                        channel.id
                    )
                except discord.NotFound:
                    stmt = delete(VoiceChannel).where(VoiceChannel.id == channel.id)
                    await db_session.execute(stmt)
                    continue
                stmt = select(Server).where(Server.id == voice_channel.guild.id)
                result = await db_session.execute(stmt)
                try:
                    voice_members = len(voice_channel.members)
                except AttributeError:
                    voice_members = 0

                if channel.has_user != bool(voice_members > 0):
                    stmt = (
                        update(VoiceChannel)
                        .where(VoiceChannel.id == channel.id)
                        .values(has_user=bool(voice_members > 0))
                    )
                    await db_session.execute(stmt)
            await db_session.commit()


def setup(bot: discord.Bot):
    bot.add_cog(VCCommands(bot))
