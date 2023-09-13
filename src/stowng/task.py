import os
import shutil

class Task:
    def __init__(self, action, type_, link, path, source, dest) -> None:
        self.action = action
        self.type_ = type_
        self.link = link
        self.path = path
        self.source = source
        self.dest = dest

    def process(self) -> None:
        """
        Process the task.

        .. todo:: match case? prbly not
        .. todo:: error handling
        .. todo:: testing
        """
        if self.action == 'create':
            if self.type_ == 'dir':
                os.mkdir(self.path)
            elif self.type_ == 'link':
                os.symlink(self.source, self.path)

        elif self.action == 'remove':
            if self.type_ == 'dir':
                os.rmdir(self.path)
            elif self.type_ == 'link':
                os.unlink(self.path)

        elif self.action == 'move':
            if self.type_ == 'file':
                shutil.move(self.source, self.dest)

