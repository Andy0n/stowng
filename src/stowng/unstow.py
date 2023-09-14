import os
import logging
from typing import List

from .tasks import Tasks
from .filesystem import Filesystem
from .utils import adjust_dotfile, join
from .ignore import Ignore

log = logging.getLogger(__name__)


class Unstow:
    def __init__(
        self,
        tasks: Tasks,
        filesystem: Filesystem,
        ignore: Ignore,
        stow_path: str,
        dotfiles: bool = False,
        adopt: bool = False,
        compat: bool = False,
    ):
        self._tasks = tasks
        self._filesystem = filesystem
        self._ignore = ignore
        self._stow_path = stow_path
        self._compat = compat
        self._dotfiles = dotfiles
        self._adopt = adopt

        self._action_count = 0

    def plan_unstow(self, packages: List[str]) -> None:
        """
        Plan the unstow operation.

        :param unstow: The list of packages to unstow.

        :raises Exception: If the stow directory does not contain a package named

        .. todo:: testing
        """
        for package in packages:
            path = join(self._stow_path, package)

            if not os.path.isdir(path):
                log.error(
                    f"The stow directory {self._stow_path} does not contain package {package}"
                )
                raise Exception(
                    f"the stow directory {self._stow_path} does not contain package {package}"
                )

            log.debug(f"Planning unstow of package {package}...")

            if self._compat:
                self._unstow_contents_orig(self._stow_path, package, ".")
            else:
                self._unstow_contents(self._stow_path, package, ".")

            log.debug(f"Planning unstow of package {package}... done")
            self._action_count += 1

    def _unstow_contents(self, stow_path: str, package: str, target: str) -> None:
        """
        Unstow the contents of a package.

        :param package: The name of the package to unstow.
        """
        path = join(stow_path, package, target)

        if self._filesystem.should_skip_target_which_is_stow_dir(target):
            return

        cwd = os.getcwd()
        msg = f"Unstowing from {target} (cwd={cwd}, stow dir={stow_path})"  # NOTE: GNU Stow: uses self.stow_path here
        msg = msg.replace(f"{os.environ['HOME']}/", "~/")

        log.debug(msg)
        log.debug(f"  source path is {path}")

        if not os.path.isdir(path):
            log.error(f"unstow_contents() called with non-directory path: {path}")
            raise Exception(f"unstow_contents() called with non-directory path: {path}")

        if not self._filesystem.is_a_node(target):
            log.error(f"unstow_contents() called with invalid target: {path}")
            raise Exception(f"unstow_contents() called with invalid target: {path}")

        # TODO: check if dir is readable

        for node in os.listdir(path):
            node_target = join(target, node)

            if self._ignore.ignore(stow_path, package, node_target):
                continue

            if self._dotfiles:
                adj_node_target = adjust_dotfile(node_target)
                log.debug(f"  Adjusting: {node_target} => {adj_node_target}")
                node_target = adj_node_target

            self._unstow_node(
                stow_path,
                package,
                node_target,
            )

        if self._filesystem.is_a_dir(target):
            self._tasks.cleanup_invalid_links(target)

    def _unstow_node(self, stow_path: str, package: str, target: str) -> None:
        """
        Unstow a node.

        :param stow_path: The path to the stow directory.
        :param package: The name of the package.
        :param target: The target to unstow.
        """
        path = join(stow_path, package, target)

        log.debug(f"Unstowing {path}")
        log.debug(f"  target is {target}")

        if self._filesystem.is_a_link(target):
            log.debug(f"  Evaluate existing link: {target}")

            existing_source = self._tasks.read_a_link(target)

            if existing_source is None:
                log.error(f"Could not read link: {target}")
                raise Exception(f"Could not read link: {target}")

            if existing_source.startswith("/"):
                log.warn(f"Ignoring an absolute symlink: {target} => {existing_source}")
                return

            existing_path, _, _ = self._filesystem.find_stowed_path(
                target, existing_source
            )

            if existing_path == "":
                self._tasks.conflict(
                    "unstow",
                    package,
                    f"existing target is not owned by stow: {target} => {existing_source}",
                )
                return

            if os.path.exists(existing_path):
                if self._dotfiles:
                    existing_path = adjust_dotfile(existing_path)

                if existing_path == path:
                    self._tasks.do_unlink(target)
            else:
                log.debug(f"--- removing invalid link into a stow directory: {path}")
                self._tasks.do_unlink(target)
        elif os.path.exists(target):
            log.debug(f"  Evaluate existing node: {target}")

            if os.path.isdir(target):
                self._unstow_contents(
                    self._stow_path,
                    package,
                    target,
                )

                parent = self._filesystem.foldable(target)

                if parent is not None:
                    self._filesystem.fold_tree(target, parent)

            else:
                self._tasks.conflict(
                    "unstow",
                    package,
                    f"existing target is neither a link nor a directory: {target}",
                )
        else:
            log.debug(f"{target} did not exist to be unstowed")

    def _unstow_contents_orig(self, stow_path: str, package: str, target: str) -> None:
        """
        Unstow the contents of a package.

        :param package: The name of the package to unstow.
        """
        path = join(stow_path, package, target)

        log.debug(f"Unstowing {target} (compat mode)")
        log.debug(f"  source path is {path}")

        if self._filesystem.is_a_link(target):
            log.debug(f"  Evaluate existing link: {target}")

            existing_source = self._tasks.read_a_link(target)

            if existing_source is None:
                log.error(f"Could not read link: {target}")
                raise Exception(f"Could not read link: {target}")

            existing_path, _, _ = self._filesystem.find_stowed_path(
                target, existing_source
            )

            if existing_path == "":
                return

            if os.path.exists(existing_path):
                if existing_path == path:
                    self._tasks.do_unlink(target)
                elif self._override(target):
                    log.debug(f"--- overriding installation of: {target}")
                    self._tasks.do_unlink(target)
            else:
                log.debug(f"--- removing invalid link into stow directory: {path}")
                self._tasks.do_unlink(target)
        elif os.path.isdir(target):
            self._unstow_contents_orig(
                stow_path,
                package,
                target,
            )

            parent = self._filesystem.foldable(target)

            if parent is not None:
                self._filesystem.fold_tree(target, parent)

        elif os.path.exists(target):
            self._tasks.conflict(
                "unstow",
                package,
                f"existing target is neither a link nor a directory: {target}",
            )
        else:
            log.debug(f"{target} did not exist to be unstowed")
