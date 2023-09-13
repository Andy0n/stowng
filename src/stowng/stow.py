# -*- coding: utf-8 -*-

import os
import logging
from typing import Dict, List

log = logging.getLogger(__name__)

class Stow:
    def __init__(self, options: Dict, stow: List[str], unstow: List[str]) -> None:
        self.action_count = 0
        self.dir = options['dir']
        self.target = options['target']
        self.verbosity = options['verbosity']
        self.simulate = options['simulate']
        self.compatibility = options['compat']
        self.stow = stow
        self.unstow = unstow
        self.conflicts = []
        self.pkgs_to_stow = []
        self.pkgs_to_delete = []
        self.tasks = []
        self.dir_task_for = {}
        self.link_task_for = {}
        self.stow_path = os.path.relpath(self.dir, self.target)
        log.debug(f'stow dir is {self.dir}')
        log.debug(f'target dir is {self.target}')
        log.debug(f'stow dir path relative to target {self.target} is {self.stow_path}')


    def plan_stow(self, stow: List[str]) -> None:
        """
        Plan the stow operation.

        :param stow: The list of packages to stow.

        :raises Exception: If the stow directory does not contain a package named

        .. todo:: testing
        """
        for package in stow:
            path = os.path.join(self.stow_path, package)

            if not os.path.isdir(path):
                log.error(f'the stow directory {self.stow_path} does not contain a package named {package}')
                raise Exception(f'the stow directory {self.stow_path} does not contain a package named {package}')

            log.debug(f'planning stow of {package}')

            self._plan_stow_contents(package, path)

            log.debug(f'planning stow of {package} done')
            self.action_count += 1


    def plan_unstow(self, unstow: List[str]) -> None:
        """
        Plan the unstow operation.

        :param unstow: The list of packages to unstow.

        :raises Exception: If the stow directory does not contain a package named

        .. todo:: testing
        """
        for package in unstow:
            path = os.path.join(self.stow_path, package)

            if not os.path.isdir(path):
                log.error(f'the stow directory {self.stow_path} does not contain a package named {package}')
                raise Exception(f'the stow directory {self.stow_path} does not contain a package named {package}')

            log.debug(f'planning unstow of {package}')

            if self.compatibility:
                self._unstow_contents_orig(package)
            else:
                self._unstow_contents(package)

            log.debug(f'planning unstow of {package} done')
            self.action_count += 1


    def _plan_stow_contents(self, package: str, path: str) -> None:
        """
        Plan the stow of the contents of a package.

        :param package: The name of the package to stow.
        :param path: The path to the package.
        """
        pass


    def _unstow_contents(self, package: str) -> None:
        """
        Unstow the contents of a package.

        :param package: The name of the package to unstow.
        """
        pass


    def _unstow_contents_orig(self, package: str) -> None:
        """
        Unstow the contents of a package.

        :param package: The name of the package to unstow.
        """
        path = os.path.join(self.stow_path, package)



