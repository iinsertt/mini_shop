import logging
from logging import Logger
from logging.handlers import RotatingFileHandler
from core.config import settings

class BotLogger:
    _instance: Logger | None = None

    @classmethod
    def get_logger(cls, name: str = "bot") -> Logger:
        if cls._instance is None:
            cls._instance = logging.getLogger(name)
            cls._instance.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            cls._instance.addHandler(console_handler)

            file_handler = RotatingFileHandler(
                "bot.log",
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            cls._instance.addHandler(file_handler)

            cls._instance.propagate = False

        return cls._instance
