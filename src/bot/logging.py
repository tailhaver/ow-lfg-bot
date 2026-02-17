from datetime import UTC, datetime

import discord


async def send_log(
    ctx: discord.ApplicationContext, channel_id: int, embed: discord.Embed
) -> None:
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar)

    embed.set_footer(text=datetime.now(UTC).strftime("%d/%m/%Y · %H:%M"))

    await ctx.bot.get_channel(channel_id).send(embed=embed)
