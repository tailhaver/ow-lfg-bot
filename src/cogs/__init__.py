__all__ = ["cogs"]

import importlib
import logging
import pkgutil

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

__path__ = pkgutil.extend_path(__path__, __name__)

cogs: list[str] = []

for loader, module_name, is_package in pkgutil.walk_packages(__path__):
    full_module_name = f"{__name__}.{module_name}"
    module = importlib.import_module(full_module_name)

    if hasattr(module, "setup"):
        cogs.append(full_module_name)
