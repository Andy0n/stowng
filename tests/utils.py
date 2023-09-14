import os
import shutil


def path_exists(path: str):
    return os.path.exists(path)


def dir_exists(dir: str):
    return os.path.isdir(dir)


def link_exists(link: str):
    return os.path.islink(link)


def make_path(path: str):
    os.makedirs(path)


def make_file(path: str, content: str = ""):
    with open(path, "w") as f:
        f.write(content)


def make_link(link: str, target: str, invalid: bool = False):
    if not path_exists(target):
        if invalid:
            os.symlink(target, link)
        else:
            raise Exception(f"target does not exist: {target}")
    else:
        os.symlink(target, link)


def make_invalid_link(link: str, target: str):
    make_link(link, target, True)


def delete_dir(path: str):
    shutil.rmtree(path)


def change_dir(path: str):
    os.chdir(path)


def get_cwd():
    return os.getcwd()


def readlink(link: str):
    return os.readlink(link)


def cat_file(file: str):
    with open(file, "r") as f:
        return f.read()
