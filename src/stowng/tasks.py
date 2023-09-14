import os
import logging
from typing import Dict, Optional

from .utils import internal_error, join
from .task import Task

log = logging.getLogger(__name__)


class Tasks:
    def __init__(self):
        self.tasks = []
        self.dir_task_for = {}
        self.link_task_for = {}
        self.mv_task_for = {}

        self.conflicts = {}
        self.conflict_count = 0

    def set_filesystem(self, filesystem) -> None:
        """
        Set the filesystem.

        :param filesystem: The filesystem.
        """
        self.filesystem = filesystem

    def get_conflicts(self) -> Dict:
        """
        Get the conflicts.

        :returns: The conflicts.
        """
        return self.conflicts

    def process_tasks(self) -> None:
        """
        Process the tasks.
        """
        log.debug(f"Processing tasks...")

        for task in self.tasks:
            if task.action != "skip":
                task.process()

        log.debug(f"Processing tasks... done")

    def do_link(self, oldfile: str, newfile: str) -> None:
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

    def do_unlink(self, file: str) -> None:
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

    def do_mkdir(self, dir: str) -> None:
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

    def do_rmdir(self, dir: str) -> None:
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

    def do_mv(self, src: str, dst: str) -> None:
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

    def link_task_action(self, path) -> Optional[str]:
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

    def dir_task_action(self, path: str) -> Optional[str]:
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

    def read_a_link(self, path: str) -> Optional[str]:
        """
        Read a link.

        :param path: The path to the link.

        :returns: The link target.
        """

        action = self.link_task_action(path)

        if action is not None:
            log.debug(f"  read_a_link({path}): task exists with action {action}")

            if action == "create":
                return self.link_task_for[path].source
            elif action == "remove":
                internal_error(f"link {path}: task exists with action {action}")

        elif os.path.islink(path):
            log.debug(f"  read_a_link({path}): real link")
            target = os.readlink(path)

            if target is None or target == "":
                log.error(f"Could not read link: {path} ()")  # TODO: error code?
                raise Exception(f"Could not read link: {path} ()")

            return target

        internal_error(f"read_a_link() passed a non link path: {path}")

    def parent_link_scheduled_for_removal(self, path: str) -> bool:
        """
        Determine if a parent link is scheduled for removal.

        :param path: The path to check.

        :returns: True if a parent link is scheduled for removal, False otherwise.
        """
        prefix = ""

        for part in path.split("/"):  # NOTE: Hopefully this is correct
            prefix = join(prefix, part)
            log.debug(f"    parent_link_scheduled_for_removal({path}): prefix {prefix}")

            if (
                prefix in self.link_task_for
                and self.link_task_for[prefix].action == "remove"
            ):
                log.debug(
                    f"    parent_link_scheduled_for_removal({path}): link scheduled for removal"
                )
                return True

        log.debug(f"    parent_link_scheduled_for_removal({path}): returning false")
        return False

    def cleanup_invalid_links(self, dir: str) -> None:
        """
        Cleanup invalid links.

        :param dir: The directory to clean up.
        """
        if not os.path.isdir(dir):
            log.error(f"cleanup_invalid_links() called with a non-directory: {dir}")
            raise Exception(
                f"cleanup_invalid_links() called with a non-directory: {dir}"
            )

        # TODO: check if dir is readable

        for node in os.listdir(dir):
            node_path = join(dir, node)

            if os.path.islink(node_path) and not node_path in self.link_task_for:
                source = self.read_a_link(node_path)

                if source is None:
                    log.error(f"Could not read link: {node_path}")
                    raise Exception(f"Could not read link: {node_path}")

                if not os.path.exists(
                    join(dir, source)
                ) and self.filesystem.path_owned_by_package(node_path, source):
                    log.debug(
                        f"--- removing stale link: {node_path} => {join(dir, source)}"
                    )
                    self.do_unlink(node_path)

    def conflict(self, action: str, package: str, message: str) -> None:
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
