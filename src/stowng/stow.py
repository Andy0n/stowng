import os
import logging
from typing import List

from .ignore import Ignore
from .filesystem import Filesystem
from .tasks import Tasks
from .utils import adjust_dotfile, join

log = logging.getLogger(__name__)


class Stow:
    def __init__(
        self,
        tasks: Tasks,
        filesystem: Filesystem,
        ignore: Ignore,
        stow_path: str,
        dotfiles: bool = False,
        adopt: bool = False,
        no_folding: bool = False,
    ):
        self._tasks = tasks
        self._filesystem = filesystem
        self._ignore = ignore
        self._stow_path = stow_path
        self._dotfiles = dotfiles
        self._adopt = adopt
        self._no_folding = no_folding

        self._action_count = 0

    def plan_stow(self, packages: List[str]) -> None:
        """
        Plan the stow operation.

        :param stow: The list of packages to stow.

        :raises Exception: If the stow directory does not contain a package named

        .. todo:: testing
        """
        for package in packages:
            path = join(self._stow_path, package)

            if not os.path.isdir(path):
                log.error(
                    f"The stow directory {self._stow_path} does not contain a package named {package}"
                )
                raise Exception(
                    f"The stow directory {self._stow_path} does not contain a package named {package}"
                )

            log.debug(f"Planning stow of package {package}...")

            self._stow_contents(self._stow_path, package, ".", path)

            log.debug(f"Planning stow of package {package}... done")
            self._action_count += 1

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
        path = join(stow_path, package, target)

        if self._filesystem.should_skip_target_which_is_stow_dir(target):
            return

        cwd = os.getcwd()

        log.debug(f"Stowing contents of {path} (cwd={cwd})")
        log.debug(f"  => {source}")

        if not os.path.isdir(path):
            log.error(f"stow_contents() called with non-directory path: {path}")
            raise Exception(f"stow_contents() called with non-directory path: {path}")

        if not self._filesystem.is_a_node(target):
            log.error(f"stow_contents() called with non-directory target: {path}")
            raise Exception(f"stow_contents() called with non-directory target: {path}")

        # TODO: check if dir is readable

        for node in os.listdir(path):
            node_target = join(target, node)

            if self._ignore.ignore(stow_path, package, node_target):
                continue

            if self._dotfiles:
                adj_node_target = adjust_dotfile(node_target)
                log.debug(f"  Adjusting: {node_target} => {adj_node_target}")
                node_target = adj_node_target

            self._stow_node(
                stow_path,
                package,
                node_target,
                join(source, node),
            )

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

        path = join(stow_path, package, target)

        log.debug(f"Stowing {stow_path} / {package} / {target}")
        log.debug(f"  => {source}")

        if os.path.islink(source):
            second_source = self._tasks.read_a_link(source)

            if second_source is None:
                log.error(f"link {source} does not exist, but should")
                raise Exception(f"link {source} does not exist, but should")

            if second_source.startswith("/"):
                self._tasks.conflict(
                    "stow",
                    package,
                    f"source is an absolute symlink {source} => {second_source}",
                )
                log.debug("Absolute symlink cannot be unstowed")
                return

        if self._filesystem.is_a_link(target):
            existing_source = self._tasks.read_a_link(target)

            if existing_source is None:
                log.error(f"Could not read link: {target}")
                raise Exception(f"Could not read link: {target}")

            log.debug(f"  Evaluate existing link: {target} => {existing_source}")

            (
                existing_path,
                existing_stow_path,
                existing_package,
            ) = self._filesystem.find_stowed_path(target, existing_source)

            if existing_path == "":
                self._tasks.conflict(
                    "stow", package, f"existing target is not owned by stow: {target}"
                )
                return

            if self._filesystem.is_a_node(existing_path):
                if existing_source == source:
                    log.debug(f"--- Skipping {target} as it already points to {source}")
                elif self._defer(target):
                    log.debug(f"--- Deferring installation of: {target}")
                elif self._override(target):
                    log.debug(f"--- Overriding installation of: {target}")
                    self._tasks.do_unlink(target)
                    self._tasks.do_link(source, target)
                elif self._filesystem.is_a_dir(
                    os.path.normpath(
                        os.path.join(os.path.dirname(target), existing_source)
                    )
                ) and self._filesystem.is_a_dir(join(os.path.dirname(target), source)):
                    log.debug(
                        f"--- Unfolding {target} which was already owned by {existing_package}"
                    )
                    self._tasks.do_unlink(target)
                    self._tasks.do_mkdir(target)
                    self._stow_contents(
                        existing_stow_path,
                        existing_package,
                        target,
                        join("..", existing_source),
                    )
                    self._stow_contents(
                        stow_path,
                        package,
                        target,
                        join("..", source),
                    )
                else:
                    self._tasks.conflict(
                        "stow",
                        package,
                        f"existing target is stowed to a different package: {target} => {existing_source}",
                    )
            else:
                log.debug(f"--- replacing invalid link: {path}")
                self._tasks.do_unlink(target)
                self._tasks.do_link(source, target)
        elif self._filesystem.is_a_node(target):
            log.debug(f"  Evaluate existing node: {target}")

            if self._filesystem.is_a_dir(target):
                self._stow_contents(
                    self._stow_path,
                    package,
                    target,
                    join("..", source),
                )
            else:
                if self._adopt:
                    self._tasks.do_mv(target, path)
                    self._tasks.do_link(source, target)
                else:
                    self._tasks.conflict(
                        "stow",
                        package,
                        f"existing target is neither a link nor a directory: {target}",
                    )
        elif self._no_folding and os.path.isdir(path) and not os.path.islink(path):
            self._tasks.do_mkdir(target)
            self._stow_contents(
                self._stow_path,
                package,
                target,
                join("..", source),
            )
        else:
            self._tasks.do_link(source, target)
