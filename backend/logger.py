import sys
import asyncio
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from traceback import format_exception

DATE = datetime.now().strftime("%Y-%m-%d")
IS_RENDER = bool(os.environ.get("RENDER") or os.environ.get("RENDER_SERVICE_ID"))

_loggers = {}

def get_logger(name="soda"):
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    class FileLineFormatter(logging.Formatter):
        def format(self, record):
            record.shortpath = f"{os.path.relpath(record.pathname, Path(__file__).parent.parent)}:{record.lineno}"
            return f"[{self.formatTime(record, '%Y-%m-%d %H:%M:%S')}] [{record.levelname:5s}] [{record.shortpath}] {record.getMessage()}"

    formatter = FileLineFormatter()

    if IS_RENDER:
        # Render: WARNING+ to stdout only. No file I/O.
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.WARNING)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)
    else:
        # Local: file-based logging as before
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)

        main_handler = logging.handlers.TimedRotatingFileHandler(
            log_dir / f"soda-{DATE}.log", when="midnight", interval=1, backupCount=30, encoding="utf-8"
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(formatter)

        debug_handler = logging.handlers.TimedRotatingFileHandler(
            log_dir / f"soda-{DATE}.debug.log", when="midnight", interval=1, backupCount=14, encoding="utf-8"
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)

        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "soda.errors.log", maxBytes=5_242_880, backupCount=5, encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(formatter)

        logger.addHandler(main_handler)
        logger.addHandler(debug_handler)
        logger.addHandler(error_handler)
        logger.addHandler(stdout_handler)

    _loggers[name] = logger
    return logger

log = get_logger()


def _global_excepthook(exc_type, exc_value, exc_traceback):
    log.critical(
        f"Unhandled exception: {''.join(format_exception(exc_type, exc_value, exc_traceback))}"
    )


def _asyncio_exception_handler(loop, context):
    message = context.get("message", "Unknown async error")
    exc = context.get("exception")
    if exc:
        log.error(f"[ASYNCIO] {message}: {''.join(format_exception(type(exc), exc, exc.__traceback__))}")
    else:
        log.error(f"[ASYNCIO] {message}")


sys.excepthook = _global_excepthook
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.set_exception_handler(_asyncio_exception_handler)
except RuntimeError:
    pass

log.info("Logger initialized")
