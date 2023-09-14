# -*- coding: utf-8 -*-

import os
import logging
from typing import Dict, List

from .stow import Stow
from .unstow import Unstow
from .tasks import Tasks
from .filesystem import Filesystem
from .ignore import Ignore

log = logging.getLogger(__name__)


class Farmer:
    def __init__(self, options: Dict) -> None:
        self._action_count = 0

        stow_path = os.path.relpath(options["dir"], options["target"])
        log.debug(f"stow dir is {options['dir']}")
        log.debug(
            f"stow dir path relative to target {options['target']} is {stow_path}"
        )

        self._tasks = Tasks()
        filesystem = Filesystem(
            self._tasks,
            stow_path,
            options["no_folding"],
            options["defer"],
            options["override"],
        )
        ignore = Ignore(options["ignore"])

        self._tasks.set_filesystem(filesystem)
        self._stow = Stow(
            self._tasks,
            filesystem,
            ignore,
            stow_path,
            options["dotfiles"],
            options["adopt"],
            options["no_folding"],
        )
        self._unstow = Unstow(
            self._tasks,
            filesystem,
            ignore,
            stow_path,
            options["dotfiles"],
            options["adopt"],
            options["compat"],
        )

    def plan_stow(self, pkgs_to_stow: List[str]) -> None:
        """
        Plan the stow operation.

        :param pkgs_to_stow: The packages to stow.
        """
        self._stow.plan_stow(pkgs_to_stow)

    def plan_unstow(self, pkgs_to_delete: List[str]) -> None:
        """
        Plan the unstow operation.

        :param pkgs_to_delete: The packages to unstow.
        """
        self._unstow.plan_unstow(pkgs_to_delete)

    def process_tasks(self) -> None:
        """
        Process the tasks.
        """
        self._tasks.process_tasks()

    def get_conflicts(self) -> Dict:
        """
        Get the conflicts.

        :return: The conflicts.
        """
        return self._tasks.get_conflicts()
