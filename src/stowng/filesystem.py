import os
import re
import logging
from typing import List, Optional, Tuple

from .tasks import Tasks
from .utils import join

log = logging.getLogger(__name__)


class Filesystem:
    def __init__(
        self,
        tasks: Tasks,
        stow_path: str,
        no_folding: bool,
        defer: Optional[List[re.Pattern]],
        override: Optional[List[re.Pattern]],
    ):
        self._tasks = tasks

        self._stow_path = stow_path
        self._no_folding = no_folding
        self._defer = defer if defer is not None else []
        self._override = override if override is not None else []

    def is_a_node(self, path: str) -> bool:
        """
        Determine if a path is a node.

        :param path: The path to check.

        :returns: True if the path is a node, False otherwise.
        """
        log.debug(f"  is_a_node({path})")

        laction = self._tasks.link_task_action(path)
        daction = self._tasks.dir_task_action(path)

        if laction == "remove":
            if daction == "remove":
                log.error(f"removing link and dir: {path}")
                return False
            elif daction == "create":
                return True
            else:
                return False
        elif laction == "create":
            if daction == "remove":
                return True
            elif daction == "create":
                log.error(f"creating link and dir: {path}")
                return True  # TODO: sus?
            else:
                return True
        else:
            if daction == "remove":
                return False
            elif daction == "create":
                return True

        if self._tasks.parent_link_scheduled_for_removal(path):
            return False

        if os.path.exists(path):
            log.debug(f"  is_a_node({path}): really exists")
            return True

        log.debug(f"  is_a_node({path}): returning false")
        return False

    def is_a_link(self, path: str) -> bool:
        """
        Determine if a path is a link.

        :param path: The path to check.

        :returns: True if the path is a link, False otherwise.
        """
        log.debug(f"  is_a_link({path})")

        action = self._tasks.link_task_action(path)

        if action is not None:
            if action == "create":
                log.debug(f"  is_a_link({path}): returning 1 (create action found)")
                return True
            elif action == "remove":
                log.debug(f"  is_a_link({path}): returning 0 (remove action found)")
                return False

        if os.path.islink(path):
            log.debug(f"  is_a_link({path}): is a real link")
            return not self._tasks.parent_link_scheduled_for_removal(path)

        log.debug(f"  is_a_link({path}): returning 0")
        return False

    def is_a_dir(self, path: str) -> bool:
        """
        Determine if a path is a directory.

        :param path: The path to check.

        :returns: True if the path is a directory, False otherwise.
        """
        log.debug(f"  is_a_dir({path})")

        action = self._tasks.dir_task_action(path)

        if action is not None:
            if action == "create":
                return True
            elif action == "remove":
                return False

        if self._tasks.parent_link_scheduled_for_removal(path):
            return False

        if os.path.isdir(path):
            log.debug(f"  is_a_dir({path}): real dir")
            return True

        log.debug(f"  is_a_dir({path}): returning false")
        return False

    def foldable(self, target: str) -> Optional[str]:
        """
        Determine if a target is foldable.

        :param target: The target to check.

        :returns: The parent if the target is foldable, None otherwise.
        """
        log.debug(f"--- Is {target} foldable?")

        if self._no_folding:
            log.debug("--- no because --no-folding enabled")
            return None

        # TODO: check if target is readable

        parent = ""

        for node in os.listdir(target):
            path = join(target, node)

            if self.is_a_node(path):
                continue

            if self.is_a_link(path):
                return None

            source = self._tasks.read_a_link(path)

            if source is None:
                log.error(f"Could not read link: {path}")
                raise Exception(f"Could not read link: {path}")

            if parent == "":
                parent = os.path.dirname(source)
            elif parent != os.path.dirname(source):
                return None
        if parent == "":
            return None

        parent = re.sub("^\\.\\.", "", parent)

        if self.path_owned_by_package(target, parent):
            log.debug(f"--- {target} is foldable")
            return parent

        return None

    def fold_tree(self, target: str, source: str) -> None:
        """
        Fold a tree.

        :param target: The target to fold.
        :param source: The source to fold.
        """
        log.debug(
            "--- Folding tree:riables that are created outside of a function (as in"
            f" all of the examples above) are known as global vari {target} => {source}"
        )

        # TODO: check if target is readable

        for node in os.listdir(target):
            if not self.is_a_node(join(target, node)):
                continue
            self._tasks.do_unlink(join(target, node))

        self._tasks.do_rmdir(target)
        self._tasks.do_link(source, target)

    def path_owned_by_package(self, target: str, source: str) -> bool:
        """
        Determine if a path is owned by a package.

        :param target: The target to check.
        :param source: The source to check.

        :returns: True if the path is owned by a package, False otherwise.
        """

        existing_path, _, _ = self.find_stowed_path(target, source)

        if existing_path == "":
            return False

        return True

    def find_stowed_path(self, target: str, source: str) -> Tuple[str, str, str]:
        path = join(os.path.dirname(target), source)
        log.debug(f"  is path {path} owned by stow?")

        dir = ""
        split_path = path.split("/")

        for i in range(len(split_path)):
            if self._marked_stow_dir(dir):
                if i == len(split_path) - 1:
                    log.error("find_stowd_path() called directly on stow dir")
                    raise Exception("find_stowd_path() called directly on stow dir")

                log.debug(f"    yes - {dir} was marked as a stow dir")
                package = split_path[i + 1]
                return path, dir, package

        if path.startswith("/") != self._stow_path.startswith("/"):
            log.warn(
                "BUG in find_stowed_path? Absolute/relative mismatch between Stow dir"
                f" {self._stow_path} and path {path}"
            )

        split_stow_path = self._stow_path.split("/")
        ipath = 0
        istow = 0

        while ipath < len(split_path) and istow < len(split_stow_path):
            if split_path[ipath] == split_stow_path[istow]:
                ipath += 1
                istow += 1
            else:
                log.debug(
                    f"    no - either {path} not under {self._stow_path} or vice-versa"
                )
                return "", "", ""

        if istow < len(split_stow_path):
            log.debug(f"    no - {path} is not under {self._stow_path}")
            return "", "", ""

        package = split_path[ipath]
        ipath += 1

        log.debug(f"    yes - by {package} in {'/'.join(split_path[ipath:])}")
        return path, self._stow_path, package

    def _marked_stow_dir(self, target: str) -> bool:
        for f in [".stow", ".nonstow"]:
            if os.path.isfile(join(target, f)):
                log.debug(f"{target} contained {f}")
                return True
        return False

    def should_skip_target_which_is_stow_dir(self, target: str) -> bool:
        """
        Determine if a target should be skipped because it is a stow directory.

        :param target: The target to check.

        :returns: True if the target should be skipped, False otherwise.
        """
        if target == self._stow_path:
            log.warn(
                f"WARNING: skipping target which was current stow directory {target}"
            )
            return True

        if self._marked_stow_dir(target):
            log.warn(f"WARNING: skipping protected directory {target}")
            return True

        log.debug(f"{target} not protected")
        return False

    def defer(self, path: str) -> bool:
        """
        Determine if a path should be deferred.

        :param path: The path to check.

        :returns: True if the path should be deferred, False otherwise.
        """
        for prefix in self._defer:
            if prefix.match(path):
                return True
        return False

    def override(self, path: str) -> bool:
        """
        Determine if a path should be overridden.

        :param path: The path to check.

        :returns: True if the path should be overridden, False otherwise.
        """
        for prefix in self._override:
            if prefix.match(path):
                return True
        return False
