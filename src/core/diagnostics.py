import logging
from logging.handlers import RotatingFileHandler


def configure_diagnostics(directory):
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("tikoplay")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    handler = RotatingFileHandler(
        directory / "application.log",
        maxBytes=1_000_000,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger
