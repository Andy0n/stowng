import logging
import os

log = logging.getLogger(__name__)


def internal_error(message: str) -> None:
    """
    Log an internal error.

    :param message: The message.
    """
    log.error(message)
    raise Exception(message)


def join(*args: str) -> str:
    """
    Join the arguments with a slash.

    :param args: The arguments.
    :return: The joined arguments.
    """
    return os.path.normpath(os.path.join(*args))
