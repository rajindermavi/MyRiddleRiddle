import logging
from pathlib import Path
from typing import Optional, Union


def get_logger(name: str = "etl", log_file: Optional[Union[str, Path]] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Return a logger that writes to a shared log file.

    Subsequent calls with the same logger name and log file reuse the handler.
    """
    log_path = Path(log_file) if log_file else Path("logs/etl.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    log_path_resolved = log_path.resolve()
    handler_exists = False
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            try:
                if Path(handler.baseFilename).resolve() == log_path_resolved:
                    handler_exists = True
                    break
            except OSError:
                continue

    if not handler_exists:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    return logger
