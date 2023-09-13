# -*- coding: utf-8 -*-

import os
import re
import logging
from typing import Dict, List, Optional, Tuple

from .task import Task
from .utils import internal_error

log = logging.getLogger(__name__)


class Stow:
    def __init__(self, options: Dict, stow: List[str], unstow: List[str]) -> None:
        self.action_count = 0

        self.dir = options["dir"]
        self.target = options["target"]

        self.simulate = options["simulate"]
        self.verbose = options["verbosity"]
        self.paranoid = False
        self.compat = options["compat"]
        self.test_mode = False
        self.dotfiles = False
        self.adopt = options["adopt"]
        self.no_folding = False
        self.ignore = options["ignore"]
        self.override = options["override"]
        self.defer = options["defer"]

        self.stow = stow
        self.unstow = unstow

        self.conflicts = {}
        self.conflict_count = 0

        self.pkgs_to_stow = []
        self.pkgs_to_delete = []

        self.tasks = []
        self.dir_task_for = {}
        self.link_task_for = {}

        self.stow_path = os.path.relpath(self.dir, self.target)
        log.debug(f"stow dir is {self.dir}")
        log.debug(f"stow dir path relative to target {self.target} is {self.stow_path}")

    def plan_stow(self, packages: List[str]) -> None:
        """
        Plan the stow operation.

        :param stow: The list of packages to stow.

        :raises Exception: If the stow directory does not contain a package named

        .. todo:: testing
        """
        for package in packages:
            path = os.path.join(self.stow_path, package)

            if not os.path.isdir(path):
                log.error(
                    f"The stow directory {self.stow_path} does not contain a package named {package}"
                )
                raise Exception(
                    f"The stow directory {self.stow_path} does not contain a package named {package}"
                )

            log.debug(f"Planning stow of package {package}...")

            self._stow_contents(self.stow_path, package, ".", path)

            log.debug(f"Planning stow of package {package}... done")
            self.action_count += 1

    def plan_unstow(self, packages: List[str]) -> None:
        """
        Plan the unstow operation.

        :param unstow: The list of packages to unstow.

        :raises Exception: If the stow directory does not contain a package named

        .. todo:: testing
        """
        for package in packages:
            path = os.path.join(self.stow_path, package)

            if not os.path.isdir(path):
                log.error(
                    f"The stow directory {self.stow_path} does not contain package {package}"
                )
                raise Exception(
                    f"the stow directory {self.stow_path} does not contain package {package}"
                )

            log.debug(f"Planning unstow of package {package}...")

            if self.compat:
                self._unstow_contents_orig(self.stow_path, package, ".")
            else:
                self._unstow_contents(self.stow_path, package, ".")

            log.debug(f"Planning unstow of package {package}... done")
            self.action_count += 1

    def process_tasks(self) -> None:
        """
        Process the tasks.
        """
        log.debug(f"Processing tasks...")

        for task in self.tasks:
            if task.action != "skip":
                task.process()

        log.debug(f"Processing tasks... done")

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

        log.debug(f"Stowing contents of {path} (cwd is {cwd})")
        log.debug(f"  => {source}")

        if not os.path.isdir(path):
            log.error(f"stow_contents() called with non-directory path: {path}")
            raise Exception(f"stow_contents() called with non-directory path: {path}")

        if not self._is_a_node(target):
            log.error(f"stow_contents() called with non-directory target: {path}")
            raise Exception(f"stow_contents() called with non-directory target: {path}")

        # TODO: check if dir is readable

        for node in os.listdir(path):
            print(f"node is {node}")
            node_target = os.path.join(target, node)

            if self._ignore(stow_path, package, node_target):
                continue

            if self.dotfiles:
                adj_node_target = (
                    node_target  # self._adjust_dotfile(node_target) # TODO: implement
                )
                log.debug(f"  Adjusting: {node_target} => {adj_node_target}")
                node_target = adj_node_target

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

        log.debug(f"Stowing {stow_path} / {package} / {target}")
        log.debug(f"  => {source}")

        if os.path.islink(source):
            second_source = self._read_a_link(source)

            if second_source is None:
                log.error(f"link {source} does not exist, but should")
                raise Exception(f"link {source} does not exist, but should")

            if second_source.startswith("/"):
                self._conflict(
                    "stow",
                    package,
                    f"source is an absolute symlink {source} => {second_source}",
                )
                log.debug("Absolute symlink cannot be unstowed")
                return

        if self._is_a_link(target):
            existing_source = self._read_a_link(target)

            if existing_source is None:
                log.error(f"Could not read link: {target}")
                raise Exception(f"Could not read link: {target}")

            log.debug(f"  Evaluate existing link: {target} => {existing_source}")

            (
                existing_path,
                existing_stow_path,
                existing_package,
            ) = self._find_stowed_path(target, existing_source)

            if existing_path == "":
                self._conflict(
                    "stow", package, f"existing target is not owned by stow: {target}"
                )
                return

            if self._is_a_node(existing_path):
                if existing_source == source:
                    log.debug(f"--- Skipping {target} as it already points to {source}")
                elif self._defer(target):
                    log.debug(f"--- Deferring installation of: {target}")
                elif self._override(target):
                    log.debug(f"--- Overriding installation of: {target}")
                    self._do_unlink(target)
                    self._do_link(source, target)
                elif self._is_a_dir(
                    os.path.join(os.path.dirname(target), existing_source)
                ) and self._is_a_dir(os.path.join(os.path.dirname(target), source)):
                    log.debug(
                        f"--- Unfolding {target} which was already owned by {existing_package}"
                    )
                    self._do_unlink(target)
                    self._do_mkdir(target)
                    self._stow_contents(
                        existing_stow_path,
                        existing_package,
                        target,
                        os.path.join("..", existing_source),
                    )
                    self._stow_contents(
                        stow_path, package, target, os.path.join("..", source)
                    )
                else:
                    self._conflict(
                        "stow",
                        package,
                        f"existing target is stowed to a different package: {target} => {existing_source}",
                    )
            else:
                log.debug(f"--- replacing invalid link: {path}")
                self._do_unlink(target)
                self._do_link(source, target)
        elif self._is_a_node(target):
            log.debug(f"  Evaluate existing node: {target}")

            if self._is_a_dir(target):
                self._stow_contents(
                    self.stow_path, package, target, os.path.join("..", source)
                )
            else:
                if self.adopt:
                    self._do_mv(target, path)
                    self._do_link(source, target)
                else:
                    self._conflict(
                        "stow",
                        package,
                        f"existing target is neither a link nor a directory: {target}",
                    )
        elif self.no_folding and os.path.isdir(path) and not os.path.islink(path):
            self._do_mkdir(target)
            self._stow_contents(
                self.stow_path, package, target, os.path.join("..", source)
            )
        else:
            self._do_link(source, target)

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
            log.debug(f"  read_a_link({path}): task exists with action {action}")

            if action == "create":
                return self.link_task_for[path].source
            elif action == "remove":
                internal_error(f"link {path}: task exists with action {action}")

        elif os.path.islink(path):
            log.debug(f"  read_a_lin({path}): real link")
            target = os.readlink(path)

            if target is None or target == "":
                log.error(f"Could not read link: {path} ()")  # TODO: error code?
                raise Exception(f"Could not read link: {path} ()")

            return target

        internal_error(f"read_a_link() passed a non link path: {path}")

    def _link_task_action(self, path) -> Optional[str]:
        """
        Determine the action for a link task.

        :param path: The path to the link.

        :returns: The action.
        """
        if path not in self.link_task_for:
            log.debug(f"  link_task_action({path}): no task")
            return None

        action = self.link_task_for[path].action

        if action not in ["create", "remove"]:
            internal_error(f"bad task action: {action}")

        log.debug(f"  link_task_action({path}): link task exists with action {action}")
        return action

    def _dir_task_action(self, path: str) -> Optional[str]:
        """
        Determine the action for a dir task.

        :param path: The path to the dir.

        :returns: The action.
        """
        if path not in self.dir_task_for:
            log.debug(f"  dir_task_action({path}): no task")
            return None

        action = self.dir_task_for[path].action

        if action not in ["create", "remove"]:
            internal_error(f"bad task action: {action}")

        log.debug(f"  dir_task_action({path}): dir task exists with action {action}")
        return action

    def _defer(self, path: str) -> bool:
        """
        Determine if a path should be deferred.

        :param path: The path to check.

        :returns: True if the path should be deferred, False otherwise.
        """
        for prefix in self.defer:
            if prefix.match(path):
                return True
        return False

    def _override(self, path: str) -> bool:
        """
        Determine if a path should be overridden.

        :param path: The path to check.

        :returns: True if the path should be overridden, False otherwise.
        """
        for prefix in self.override:
            if prefix.match(path):
                return True
        return False

    def _parent_link_scheduled_for_removal(self, path: str) -> bool:
        """
        Determine if a parent link is scheduled for removal.

        :param path: The path to check.

        :returns: True if a parent link is scheduled for removal, False otherwise.
        """
        prefix = ""

        for part in path.split("/"):  # NOTE: Hopefully this is correct
            prefix = os.path.join(prefix, part)
            log.debug(f"    parent_link_scheduled_for_removal({path}): prefix {prefix}")

            if (
                prefix in self.link_task_for
                and self.link_task_for[prefix].action == "remove"
            ):
                log.debug(
                    f"    parent_link_scheduled_for_removal({path}): link scheduled for removal"
                )
                return True

        log.debug(f"   parent_link_scheduled_for_removal({path}): returning false")
        return False

    def _find_stowed_path(self, target: str, source: str) -> Tuple[str, str, str]:
        path = os.path.normpath(os.path.join(os.path.dirname(target), source))
        log.debug(f"  is path {path} owned by stow?")

        dir = ""
        split_path = path.split("/")

        for i in range(len(split_path)):
            if self._marked_stow_dir(dir):
                if i == len(split_path) - 1:
                    log.error(f"find_stowd_path() called directly on stow dir")
                    raise Exception(f"find_stowd_path() called directly on stow dir")

                log.debug(f"    yes - {dir} was marked as a stow dir")
                package = split_path[i + 1]
                return path, dir, package

        if path.startswith("/") != self.stow_path.startswith("/"):
            log.warn(
                f"BUG in find_stowed_path? Absolute/relative mismatch between Stow dir {self.stow_path} and path {path}"
            )

        split_stow_path = self.stow_path.split("/")
        ipath = 0
        istow = 0

        while ipath < len(split_path) and istow < len(split_stow_path):
            if split_path[ipath] == split_stow_path[istow]:
                ipath += 1
                istow += 1
            else:
                log.debug(
                    f"    no - either {path} not under {self.stow_path} or vice-versa"
                )
                return "", "", ""

        if istow < len(split_stow_path):
            log.debug(f"    no - {path} is not under {self.stow_path}")
            return "", "", ""

        package = split_path[ipath]
        ipath += 1

        log.debug(f"    yes - by {package} in {'/'.join(split_path[ipath:])}")
        return path, self.stow_path, package

    def _marked_stow_dir(self, target: str) -> bool:
        for f in [".stow", ".nonstow"]:
            if os.path.isfile(os.path.join(target, f)):
                log.debug(f"{target} contained {f}")
                return True
        return False

    def _should_skip_target_which_is_stow_dir(self, target: str) -> bool:
        """
        Determine if a target should be skipped because it is a stow directory.

        :param target: The target to check.

        :returns: True if the target should be skipped, False otherwise.
        """
        if target == self.stow_path:
            log.warn(
                f"WARNING: skipping target which was current stow directory {target}"
            )
            return True

        if self._marked_stow_dir(target):
            log.warn(f"WARNING: skipping protected directory {target}")
            return True

        log.debug(f"{target} not protected")
        return False

    def _conflict(self, action: str, package: str, message: str) -> None:
        """
        Add a conflict.

        :param action: The action.
        :param package: The package.
        :param message: The message.
        """

        log.debug(f"CONFLICT when {action}ing {package}: {message}")
        # self.conflicts.append({"action": action, "package": package, "message": message})
        if action not in self.conflicts:
            self.conflicts[action] = {}
        if package not in self.conflicts[action]:
            self.conflicts[action][package] = []
        self.conflicts[action][package].append(message)
        self.conflict_count += 1

    def _is_a_node(self, path: str) -> bool:
        """
        Determine if a path is a node.

        :param path: The path to check.

        :returns: True if the path is a node, False otherwise.
        """
        log.debug(f"  is_a_node({path})")

        laction = self._link_task_action(path)
        daction = self._dir_task_action(path)

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

        if self._parent_link_scheduled_for_removal(path):
            return False

        if os.path.exists(path):
            log.debug(f"  is_a_node({path}): really exists")
            return True

        log.debug(f"  is_a_node({path}): returning false")
        return False

    def _is_a_link(self, path: str) -> bool:
        """
        Determine if a path is a link.

        :param path: The path to check.

        :returns: True if the path is a link, False otherwise.
        """
        log.debug(f"  is_a_link({path})")

        action = self._link_task_action(path)

        if action is not None:
            if action == "create":
                log.debug(f"  is_a_link({path}): returning 1 (create action found)")
                return True
            elif action == "remove":
                log.debug(f"  is_a_link({path}): returning 0 (remove action found)")
                return False

        if os.path.islink(path):
            log.debug(f"  is_a_link({path}): is a real link")
            return not self._parent_link_scheduled_for_removal(path)

        log.debug(f"  is_a_link({path}): returning 0")
        return False

    def _is_a_dir(self, path: str) -> bool:
        """
        Determine if a path is a directory.

        :param path: The path to check.

        :returns: True if the path is a directory, False otherwise.
        """
        log.debug(f"  is_a_dir({path})")

        action = self._dir_task_action(path)

        if action is not None:
            if action == "create":
                return True
            elif action == "remove":
                return False

        if self._parent_link_scheduled_for_removal(path):
            return False

        if os.path.isdir(path):
            log.debug(f"  is_a_dir({path}): real dir")
            return True

        log.debug(f"  is_a_dir({path}): returning false")
        return False

    def _do_link(self, oldfile: str, newfile: str) -> None:
        """
        Create a link.

        :param oldfile: The source of the link.
        :param newfile: The destination of the link.
        """
        if newfile in self.dir_task_for:
            task_ref = self.dir_task_for[newfile]

            if task_ref.action == "create":
                if task_ref.type_ == "dir":
                    internal_error(
                        f"new link ({newfile} => {oldfile}) clashes with planned new directory"
                    )
            elif task_ref.action == "remove":
                pass  # TODO: see GNU Stow
            else:
                internal_error(f"bad task action: {task_ref.action}")

        if newfile in self.link_task_for:
            task_ref = self.link_task_for[newfile]

            if task_ref.action == "create":
                if task_ref.source == oldfile:
                    internal_error(
                        f"new link clashes with planned new link: {task_ref.path} => {task_ref.source}"
                    )
                else:
                    log.debug(
                        f"LINK: {newfile} => {oldfile} (duplicates previous action)"
                    )
                    return
            elif task_ref.action == "remove":
                if task_ref.source == oldfile:
                    log.debug(f"LINK: {newfile} => {oldfile} (reverts previous action)")
                    self.link_task_for[newfile].action = "skip"
                    self.link_task_for.pop(newfile)
                    return
            else:
                internal_error(f"bad task action: {task_ref.action}")

        log.debug(f"LINK: {newfile} => {oldfile}")
        task = Task("create", "link", path=newfile, source=oldfile)
        self.tasks.append(task)
        self.link_task_for[newfile] = task

    def _do_unlink(self, file: str) -> None:
        """
        Remove a link.

        :param file: The link to remove.
        """
        if file in self.link_task_for:
            task_ref = self.link_task_for[file]

            if task_ref.action == "remove":
                log.debug(f"UNLINK: {file} (duplicates previous action)")
                return
            elif task_ref.action == "create":
                log.debug(f"UNLINK: {file} (reverts previous action)")
                self.link_task_for[file].action = "skip"
                self.link_task_for.pop(file)
                return
            else:
                internal_error(f"bad task action: {task_ref.action}")

        if file in self.dir_task_for and self.dir_task_for[file].action == "create":
            internal_error(
                f"new unlink operation clashes with planned operation: {self.dir_task_for[file].action} dir {file}"
            )

        log.debug(f"UNLINK: {file}")

        source = os.readlink(file)

        if source is None:
            log.error(f"could not read link: {file}")
            raise Exception(f"could not read link: {file}")

        task = Task("remove", "link", path=file, source=source)
        self.tasks.append(task)
        self.link_task_for[file] = task

    def _do_mkdir(self, dir: str) -> None:
        """
        Create a directory.

        :param dir: The directory to create.
        """
        if dir in self.link_task_for:
            task_ref = self.link_task_for[dir]

            if task_ref.action == "create":
                if task_ref.type_ == "link":
                    internal_error(
                        f"new dir clashes with planned new link ({task_ref.path} => {task_ref.source})"
                    )
            elif task_ref.action == "remove":
                pass  # TODO: see GNU Stow
            else:
                internal_error(f"bad task action: {task_ref.action}")

        if dir in self.dir_task_for:
            task_ref = self.dir_task_for[dir]

            if task_ref.action == "create":
                log.debug(f"MKDIR: {dir} (duplicates previous action)")
                return
            elif task_ref.action == "remove":
                log.debug(f"MKDIR: {dir} (reverts previous action)")
                self.dir_task_for[dir].action = "skip"
                self.dir_task_for.pop(dir)
                return
            else:
                internal_error(f"bad task action: {task_ref.action}")

        log.debug(f"MKDIR: {dir}")
        task = Task("create", "dir", path=dir)
        self.tasks.append(task)
        self.dir_task_for[dir] = task

    def _do_rmdir(self, dir: str) -> None:
        """
        Remove a directory.

        :param dir: The directory to remove.
        """
        if dir in self.link_task_for:
            task_ref = self.link_task_for[dir]
            internal_error(
                f"rmdir clashes with planned operation: {task_ref.action} link {task_ref.path} => {task_ref.source}"
            )

        if dir in self.dir_task_for:
            task_ref = self.dir_task_for[dir]

            if task_ref.action == "remove":
                log.debug(f"RMDIR: {dir} (duplicates previous action)")
                return
            elif task_ref.action == "create":
                log.debug(f"RMDIR: {dir} (reverts previous action)")
                self.dir_task_for[
                    dir
                ].action = "skip"  # NOTE: GNU Stow has link_task_for here
                self.dir_task_for.pop(dir)
                return
            else:
                internal_error(f"bad task action: {task_ref.action}")

        log.debug(f"RMDIR: {dir}")
        task = Task("remove", "dir", path=dir)
        self.tasks.append(task)
        self.dir_task_for[dir] = task

    def _do_mv(self, src: str, dst: str) -> None:
        """
        Move a file.

        :param src: The source.
        :param dst: The destination.
        """
        if src in self.link_task_for:
            # NOTE: GNU Stow: Should not ever happen, but not 100% sure
            task_ref = self.link_task_for[src]
            internal_error(
                f"do_mv: pre-existing link task for {src}; action: {task_ref.action}; source: {task_ref.source}"
            )
        elif src in self.dir_task_for:
            task_ref = self.dir_task_for[src]
            internal_error(
                f"do_mv: pre-existing dir task for {src}?!; action: {task_ref.action}"
            )

        log.debug(f"MV: {src} => {dst}")

        task = Task("move", "file", path=src, dest=dst)
        self.tasks.append(task)
        # FIXME: GNU Stow: do we need this for anything?
        # self.mv_task_for[src] = task

    def _ignore(self, stow_path: str, package: str, target: str) -> bool:
        """
        Determine if a target should be ignored.

        :param stow_path: The path to the stow directory.
        :param package: The name of the package.
        :param target: The target to check.

        :returns: True if the target should be ignored, False otherwise.
        """

        if len(target) < 1:
            log.error(f"::ignore() called with empty target")
            raise Exception(f"::ignore() called with empty target")

        for suffix in self.ignore:
            if suffix.match(target):
                log.debug(f"  Ignoring path {target} due to --ignore={suffix}")
                return True

        package_dir = os.path.join(stow_path, package)
        path_regexp, segment_regexp = self._get_ignore_regexps(package_dir)
        log.debug(f"    Ignore list regexp for paths: {path_regexp}")
        log.debug(f"    Ignore list regexp for segments: {segment_regexp}")

        if path_regexp is not None and path_regexp.match(target):
            log.debug(f"  Ignoring path {target}")
            return True

        basename = os.path.basename(target)

        if segment_regexp is not None and segment_regexp.match(basename):
            log.debug(f"  Ignoring path segment {target}")
            return True

        log.debug(f"  Not ignoring path {target}")
        return False

    def _get_ignore_regexps(
        self, dir: str
    ) -> Tuple[Optional[re.Pattern], Optional[re.Pattern]]:
        """
        Get the ignore regexps.

        :param dir: The directory to check.

        :returns: The ignore regexps.
        """
        path_regexp = None
        segment_regexp = None

        return path_regexp, segment_regexp
