# -*- coding: utf-8 -*-

import os
import re
import logging
from typing import Dict, List, Optional

from .stow import Stow
from .unstow import Unstow
from .tasks import Tasks
from .filesystem import Filesystem
from .ignore import Ignore

log = logging.getLogger(__name__)


class Farmer:
    def __init__(
        self,
        dir: str,
        target: str,
        ignore: Optional[List[re.Pattern]] = None,
        defer: Optional[List[re.Pattern]] = None,
        override: Optional[List[re.Pattern]] = None,
        adopt: bool = False,
        compat: bool = False,
        simulate: bool = False,
        dotfiles: bool = False,
        no_folding: bool = False,
        paranoid: bool = False,
        test_mode: bool = False,
    ) -> None:
        self._action_count = 0

        stow_path = os.path.relpath(dir, target)
        log.debug(f"stow dir is {dir}")
        log.debug(f"stow dir path relative to target {target} is {stow_path}")

        self._tasks = Tasks()
        filesystem = Filesystem(
            self._tasks,
            stow_path,
            no_folding,
            defer,
            override,
        )
        ignore_manager = Ignore(ignore)

        self._tasks.set_filesystem(filesystem)
        self._stow = Stow(
            self._tasks,
            filesystem,
            ignore_manager,
            stow_path,
            dotfiles,
            adopt,
            no_folding,
        )
        self._unstow = Unstow(
            self._tasks,
            filesystem,
            ignore_manager,
            stow_path,
            dotfiles,
            adopt,
            compat,
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

    def get_conflict_count(self) -> int:
        """
        Get the number of conflicts.

        :return: The number of conflicts.
        """
        return self._tasks.get_conflict_count()

    def get_task_count(self) -> int:
        """
        Get the number of tasks.

        :return: The number of tasks.
        """
        return self._tasks.get_task_count()
