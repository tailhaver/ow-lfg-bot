__all__ = ["main"]

import discord
from rich import print
import platform

print(f"""\r
[bright_red]                                                          .o8[/bright_red] \t
[light_salmon3]                                                         "888 [/light_salmon3]\t
[orange1]oo.ooooo.  oooo    ooo  .ooooo.   .ooooo.  oooo d8b  .oooo888 [/orange1]\t[bright_white bold]pycord v{(lambda v: f"{v.major}.{v.minor}.{v.micro}")(discord.version_info)}[/bright_white bold]
[yellow2] 888' `88b  `88.  .8'  d88' `"Y8 d88' `88b `888""8P d88' `888 [/yellow2]\t[bright_white bold]interpreter:[/bright_white bold]\t[grey70]{platform.python_implementation()} {platform.python_version()}[/grey70]
[sea_green2] 888   888   `88..8'   888       888   888  888     888   888 [/sea_green2]\t[bright_white bold]running on:[/bright_white bold]\t[grey70]{platform.machine()} {platform.platform(terse=True).replace("-", " ")}[/grey70]
[medium_turquoise] 888   888    `888'    888   .o8 888   888  888     888   888 [/medium_turquoise]\t
[dodger_blue1] 888bod8P'     .8'     `Y8bod8P' `Y8bod8P' d888b    `Y8bod88P"[/dodger_blue1]\t
[orchid] 888       .o..P'                                             [/orchid]\t
[purple]o888o      `Y8P'                                              [/purple]\t
""".strip())

from src.bot.client import main  # noqa: E402
