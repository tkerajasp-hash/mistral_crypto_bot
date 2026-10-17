"""Configuration du logging (console + fichier)."""
from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(level: str = "INFO", logfile: str | None = "logs/bot.log") -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if logfile:
        Path(logfile).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(logfile))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )
