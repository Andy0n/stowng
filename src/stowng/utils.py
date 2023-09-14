import logging
import os
import re

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


def adjust_dotfile(target: str) -> str:
    """
    Adjust a dotfile.

    :param target: The target to adjust.

    :returns: The adjusted target.
    """
    result = []

    for part in target.split("/"):
        if part not in ("dot-", "dot-."):
            part = re.sub("^dot-", ".", part)

        result.append(part)

    return "/".join(result)
