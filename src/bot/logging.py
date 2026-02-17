import discord
from datetime import datetime, timezone

async def send_log(
    ctx: discord.ApplicationContext,
    channel_id: int,
    embed: discord.Embed
) -> None: 
    embed.set_author(
        name=ctx.author.name,
        icon_url=ctx.author.avatar
    )

    embed.set_footer(
        text=datetime.now(timezone.utc).strftime("%d/%m/%Y · %H:%M")
    )

    await ctx.bot.get_channel(channel_id).send(embed=embed)