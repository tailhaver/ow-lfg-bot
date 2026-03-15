import discord
import ujson
from discord.ext import commands

HERO_LIST: list = ujson.load(open("heroes/heroes-en.json"))
PASSIVES: dict = ujson.load(open("heroes/passives.json"))

def format_hero_info(hero_name: dict) -> dict[str, discord.Embed | discord.File]:
    hero = ujson.load(open(f"heroes/{hero_name}/{hero_name}.json"))

    file = discord.File(hero["2d"])
    file_name = hero["2d"].split("/")[-1]

    total_hp = hero.get("health", 0) + hero.get("armor", 0) + hero.get("shield", 0)
    if hero["role"] == "tank":
        health = f"**{total_hp}** HP ({total_hp + 150} Role Queue)"
    else:
        health = f"**{total_hp}** HP"
    if hero.get("armor", 0) > 0:
        health += f" - {hero["armor"]} Armor"
    if hero.get("shield", 0) > 0:
        health += f" - {hero["shield"]} Shield"
    health_emojis = f"{"<:health:1482186175660949634>"*int(hero.get("health", 0)/25) if total_hp < 525 else ""}" \
                    + f"{"<:armor:1482189795940896828>"*int(hero.get("armor", 0)/25)}" \
                    + f"{"<:shield:1482189852295299164>"*int(hero.get("shield", 0)/25)}"
    hero_passives = [{"name": f"{PASSIVES[passive]["emoji"]} **{passive}**", "value": f"{PASSIVES[passive]["description"]}{f"\n{PASSIVES[passive].get("data")}" if PASSIVES[passive].get("data") is not None else ""}"} for passive in hero["abilities"]["passive"]]
    description = f"""
{hero["role_emoji"]} **{hero["role"].title()}**    {hero["subrole_emoji"]} **{hero["subrole"].title()}**
{hero["description"]}

{health}
{health_emojis}
{hero["composition"]["poke"]}% Poke - {hero["composition"]["brawl"]}% Brawl - {hero["composition"]["dive"]}% Dive

"""
    embed = discord.Embed(
        title=hero["name"],
        description=description.strip(),
        color=int(hero["color"], 16)
    )
    embed.set_thumbnail(url=f"attachment://{file_name}")
    for passive in hero_passives:
        embed.add_field(**passive)
    return {"files": [file], "embed": embed}

class HeroCommands(commands.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @commands.slash_command(
        name="hero",
        description="Get the info of a hero",
    )
    @discord.option(
        "hero",
        type=discord.SlashCommandOptionType.string,
        choices=list(HERO_LIST)
    )
    async def hero_info(
        self, ctx: discord.ApplicationContext, hero: str
    ) -> None:
        await ctx.respond(**format_hero_info(hero))


def setup(bot: discord.Bot):
    bot.add_cog(HeroCommands(bot))
