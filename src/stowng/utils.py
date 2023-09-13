import logging

log = logging.getLogger(__name__)


def internal_error(message: str) -> None:
    """
    Log an internal error.

    :param message: The message.
    """
    log.error(message)
    raise Exception(message)
