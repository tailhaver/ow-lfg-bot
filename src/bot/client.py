import asyncio
import discord
from os import getenv
from time import time
from src.console import logger

bot = discord.Bot(
    heartbeat_timeout=120.0,
    intents=discord.Intents.all()
)
start_time = None

def main():
    global start_time
    for extension in ["src.cogs.events", "src.cogs.admin", "src.cogs.voice_channel"]:
        bot.load_extension(extension)
        logger.info(f"extension '{extension}' loaded successfully")
    try:
        bot.run(
            token=getenv("BOT_TOKEN")
        )
    except Exception as e:
        raise e
    finally:
        if bot.is_closed():
            logger.info("bot shut down successfully")
        logger.info("successfully terminated")