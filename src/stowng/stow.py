# -*- coding: utf-8 -*-

import os
import logging
from typing import Dict, List, Optional

from .task import Task

log = logging.getLogger(__name__)


class Stow:
    def __init__(self, options: Dict, stow: List[str], unstow: List[str]) -> None:
        self.action_count = 0
        self.dir = options["dir"]
        self.target = options["target"]
        self.verbosity = options["verbosity"]
        self.simulate = options["simulate"]
        self.compatibility = options["compat"]
        self.stow = stow
        self.unstow = unstow
        self.conflicts = []
        self.pkgs_to_stow = []
        self.pkgs_to_delete = []
        self.tasks = []
        self.dir_task_for = {}
        self.link_task_for = {}
        self.stow_path = os.path.relpath(self.dir, self.target)
        log.debug(f"stow dir is {self.dir}")
        log.debug(f"target dir is {self.target}")
        log.debug(f"stow dir path relative to target {self.target} is {self.stow_path}")

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
                log.error(
                    f"the stow directory {self.stow_path} does not contain a package named {package}"
                )
                raise Exception(
                    f"the stow directory {self.stow_path} does not contain a package named {package}"
                )

            log.debug(f"planning stow of {package}")

            self._stow_contents(self.stow_path, package, ".", path)

            log.debug(f"planning stow of {package} done")
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
                log.error(
                    f"the stow directory {self.stow_path} does not contain a package named {package}"
                )
                raise Exception(
                    f"the stow directory {self.stow_path} does not contain a package named {package}"
                )

            log.debug(f"planning unstow of {package}")

            if self.compatibility:
                self._unstow_contents_orig(self.stow_path, package, ".")
            else:
                self._unstow_contents(self.stow_path, package, ".")

            log.debug(f"planning unstow of {package} done")
            self.action_count += 1

    def process_tasks(self) -> None:
        """
        Process the tasks.
        """
        log.debug(f"processing {len(self.tasks)} tasks")

        for task in self.tasks:
            if not task.skipped():
                log.debug(f"processing task {task}")
                task.process()
                log.debug(f"processing task {task} done")

        log.debug(f"processing {len(self.tasks)} tasks done")

    def _stow_contents(
        self, stow_path: str, package: str, target: str, source: str
    ) -> None:
        """
        Plan the stow of the contents of a package.

        :param stow_path: The path to the stow directory.
        :param package: The name of the package to stow.
        :param target: The target to stow.
        :param source: The source to stow.
        """
        path = os.path.join(stow_path, package, target)

        if self._should_skip_target_which_is_stow_dir(target):
            return

        cwd = os.getcwd()

        log.debug(f"stowing contents of {path} (cwd is {cwd})")
        log.debug(f"    => {source}")

        if not os.path.isdir(path):
            log.error(f"path {path} is not a directory")
            raise Exception(f"path {path} is not a directory")

        if self._is_a_node(target):
            log.error(f"target {target} is a node")
            raise Exception(f"target {target} is a node")

        # TODO: check if dir is readable

        for node in os.listdir(path):
            print(f"node is {node}")
            node_target = os.path.join(target, node)

            if self._ignore(stow_path, package, node_target):
                continue

            # TODO: dotfiles????

            self._stow_node(stow_path, package, node_target, os.path.join(source, node))

    def _stow_node(
        self, stow_path: str, package: str, target: str, source: str
    ) -> None:
        """
        Stow a node.

        :param stow_path: The path to the stow directory.
        :param package: The name of the package.
        :param target: The target to stow.
        :param source: The source to stow.
        """

        path = os.path.join(stow_path, package, target)

        log.debug(f"stowing {stow_path}/{package}/{target}")
        log.debug(f"    => {source}")

        if os.path.islink(source):
            second_source = self._read_a_link(source)

            if second_source is None:
                log.error(f"link {source} does not exist, but should")
                raise Exception(f"link {source} does not exist, but should")

            if second_source.startswith("/"):
                self.conflicts.append(
                    {
                        "action": "stow",
                        "package": package,
                        "messages": [
                            f"{source} is an absolute symlink to {second_source}"
                        ],
                    }
                )
                log.debug("absolute symlink cannot be unstowed")
                return

        # if self._is_a_link(target):

    def _unstow_contents(self, stow_path: str, package: str, target: str) -> None:
        """
        Unstow the contents of a package.

        :param package: The name of the package to unstow.
        """
        pass

    def _unstow_contents_orig(self, stow_path: str, package: str, target: str) -> None:
        """
        Unstow the contents of a package.

        :param package: The name of the package to unstow.
        """
        pass

    def _read_a_link(self, path: str) -> Optional[str]:
        """
        Read a link.

        :param path: The path to the link.

        :returns: The link target.
        """

        action = self._link_task_action(path)

        if action is not None:
            log.debug(f"link {path}: task exists with action {action}")

            if action == "create":
                return self.link_task_for[path].source
            elif action == "remove":
                raise Exception(f"link {path}: task exists with action {action}")

        elif os.path.islink(path):
            log.debug(f"link {path}: link exists")
            return os.readlink(path)

    def _link_task_action(self, path) -> Optional[str]:
        """
        Determine the action for a link task.

        :param path: The path to the link.

        :returns: The action.
        """
        if path not in self.link_task_for:
            log.debug(f"link {path}: no task exists")
            return None

        action = self.link_task_for[path].action

        if action not in ["create", "remove"]:
            log.error(f"link {path}: invalid action {action}")
            raise Exception(f"link {path}: invalid action {action}")

        log.debug(f"link {path}: task exists with action {action}")
        return action

    # TODO: not implemented yet:
    def _should_skip_target_which_is_stow_dir(self, target: str) -> bool:
        """
        Determine if a target should be skipped because it is a stow directory.

        :param target: The target to check.

        :returns: True if the target should be skipped, False otherwise.
        """
        return False

    def _is_a_node(self, path: str) -> bool:
        """
        Determine if a path is a node.

        :param path: The path to check.

        :returns: True if the path is a node, False otherwise.
        """
        return False

    def _ignore(self, stow_path: str, package: str, target: str) -> bool:
        """
        Determine if a target should be ignored.

        :param stow_path: The path to the stow directory.
        :param package: The name of the package.
        :param target: The target to check.

        :returns: True if the target should be ignored, False otherwise.
        """
        return False
