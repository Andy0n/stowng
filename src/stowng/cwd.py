import os
import logging

log = logging.getLogger(__name__)


def change_cwd(path: str):
    return CurrentWorkingDirectory(path)


class CurrentWorkingDirectory:
    """
    A context manager to change the current working directory.

    :param path: The path to change to.
    """

    def __init__(self, path: str):
        self.path = path

    def __enter__(self):
        self.old_cwd = os.getcwd()
        os.chdir(self.path)
        log.debug(f"cwd now {os.getcwd()}")

    def __exit__(self, type, value, tb):
        os.chdir(self.old_cwd)
        log.debug(f"cwd restored to {os.getcwd()}")
