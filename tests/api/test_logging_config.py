"""Logging configuration: console and file output, request ids, levels, safe to call twice."""

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from casm.api.logging_config import LOGGER_NAME, configure_logging, request_id_var


@pytest.fixture(autouse=True)
def restore_logger() -> Iterator[None]:
    """Leave the `casm` logger as the test found it."""
    logger = logging.getLogger(LOGGER_NAME)
    before = list(logger.handlers)
    level, propagate = logger.level, logger.propagate
    yield
    for handler in list(logger.handlers):
        if handler not in before:
            logger.removeHandler(handler)
            handler.close()
    logger.setLevel(level)
    logger.propagate = propagate


def owned_handlers() -> list[logging.Handler]:
    return [
        h for h in logging.getLogger(LOGGER_NAME).handlers if getattr(h, "_casm", False)
    ]


def flush() -> None:
    for handler in owned_handlers():
        handler.flush()


def test_lines_go_to_the_file_with_time_level_logger_and_request_id(
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "logs" / "api.log"
    configure_logging(level="INFO", log_file=log_file)
    token = request_id_var.set("abc123def456")
    try:
        logging.getLogger("casm.test").info("hello from a request")
    finally:
        request_id_var.reset(token)
    logging.getLogger("casm.test").info("hello from startup")
    flush()
    first, second = log_file.read_text(encoding="utf-8").splitlines()
    assert (
        "INFO" in first
        and "casm.test" in first
        and "[abc123def456]" in first
        and first.endswith("hello from a request")
    )
    assert "[-]" in second  # outside a request there is no id
    assert first[:4].isdigit()  # starts with a timestamp


def test_the_log_folder_is_created(tmp_path: Path) -> None:
    log_file = tmp_path / "a" / "b" / "api.log"
    configure_logging(level="INFO", log_file=log_file)
    assert log_file.parent.is_dir()


def test_console_only_when_no_file_is_given() -> None:
    configure_logging(level="INFO", log_file=None)
    kinds = {type(h).__name__ for h in owned_handlers()}
    assert kinds == {"StreamHandler"}


def test_the_level_decides_what_is_written(tmp_path: Path) -> None:
    log_file = tmp_path / "api.log"
    configure_logging(level="INFO", log_file=log_file)
    logging.getLogger("casm.test").debug("quiet detail")
    logging.getLogger("casm.test").info("visible")
    configure_logging(
        level="debug", log_file=log_file
    )  # the level name is case-insensitive
    logging.getLogger("casm.test").debug("loud detail")
    flush()
    text = log_file.read_text(encoding="utf-8")
    assert "quiet detail" not in text and "visible" in text and "loud detail" in text


def test_calling_it_twice_replaces_the_handlers_rather_than_doubling_them(
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "api.log"
    configure_logging(level="INFO", log_file=log_file)
    configure_logging(level="INFO", log_file=log_file)
    assert len(owned_handlers()) == 2  # one console, one file
    logging.getLogger("casm.test").info("once")
    flush()
    assert log_file.read_text(encoding="utf-8").count("once") == 1


def test_an_unknown_level_is_rejected_with_a_clear_message() -> None:
    with pytest.raises(ValueError, match="Unknown log level 'LOUD'"):
        configure_logging(level="LOUD", log_file=None)


def test_records_do_not_propagate_to_the_root_logger() -> None:
    configure_logging(level="INFO", log_file=None)
    assert logging.getLogger(LOGGER_NAME).propagate is False
