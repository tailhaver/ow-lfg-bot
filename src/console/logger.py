import logging

from src.console.console import print


class CustomHandler(logging.Handler):
    MAP = {
        logging.DEBUG: "blue",
        logging.INFO: "spring_green4",
        logging.WARNING: "dark_khaki",
        logging.ERROR: "red",
        logging.CRITICAL: "bold red",
    }
    BRIGHT_MAP = {
        logging.DEBUG: "blue",
        logging.INFO: "green",
        logging.WARNING: "yellow",
        logging.ERROR: "red",
        logging.CRITICAL: "bold red",
    }

    def __init__(self) -> None:
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        color = self.MAP.get(record.levelno)
        bright = self.BRIGHT_MAP.get(record.levelno)
        print(
            f"[{color}]"
            + f"[{bright} bold]{record.levelname[0]}[/{bright} bold] "
            + self.format(record)
            + f"[/{color}]"
        )


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(asctime)s %(module)s: %(message)s", handlers=[CustomHandler()]
)
