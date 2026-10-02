"""Logging for the API: one format with a request id on every line, to the console and an optional file."""

import logging
import logging.handlers
from contextvars import ContextVar
from pathlib import Path

LOGGER_NAME: str = "casm"
LOG_FORMAT: str = "%(asctime)s %(levelname)-7s %(name)s [%(request_id)s] %(message)s"
FILE_MAX_BYTES: int = 5_000_000
FILE_BACKUPS: int = 3
NO_REQUEST: str = "-"

# The id of the request being served; it follows the request into the worker threads that run the services.
request_id_var: ContextVar[str] = ContextVar("request_id", default=NO_REQUEST)


class RequestIdFilter(logging.Filter):
    """Stamps every record with the current request id."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging(*, level: str, log_file: Path | None) -> None:
    """Send everything under the `casm` logger to the console and, if given, a rotating file.

    Safe to call again: handlers added by an earlier call are replaced, not duplicated.

    Args:
        level: A logging level name such as `INFO` or `DEBUG`.
        log_file: Where to also write the log (created with its folder), or None for console only.

    Raises:
        ValueError: If `level` is not a logging level name.
    """
    numeric: int | str = logging.getLevelName(level.upper())
    if not isinstance(numeric, int):
        raise ValueError(
            f"Unknown log level {level!r}; use DEBUG, INFO, WARNING or ERROR."
        )
    logger: logging.Logger = logging.getLogger(LOGGER_NAME)
    for handler in [h for h in logger.handlers if getattr(h, "_casm", False)]:
        logger.removeHandler(handler)
        handler.close()
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=FILE_MAX_BYTES,
                backupCount=FILE_BACKUPS,
                encoding="utf-8",
            )
        )
    for handler in handlers:
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handler.addFilter(RequestIdFilter())
        handler._casm = True  # type: ignore[attr-defined]  # marks the handlers this function owns
        logger.addHandler(handler)
    logger.setLevel(numeric)
    logger.propagate = False
