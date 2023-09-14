# -*- coding: utf-8 -*-
import argparse
import re
import os
from typing import Dict, List, Tuple

from . import __version__


CONFIG_FILES = ["~/.stowrc", ".stowrc"]


def set_verbosity(verbosity_arg: List[str] or str):
    """
    Set the verbosity level.

    :param verbosity_arg: The verbosity argument.
    :return: The verbosity level.

    :raises ValueError: If the verbosity argument is invalid.

    :Example:
    >>> set_verbosity(['1'])
    1
    >>> set_verbosity(['v'])
    2
    >>> set_verbosity(['vv', 'v'])
    5
    >>> set_verbosity(['v', 'v', '1'])
    5
    >>> set_verbosity(['3', '1'])
    4
    >>> set_verbosity([])
    0
    >>> set_verbosity(['a'])
    Traceback (most recent call last):
        ...
    ValueError: invalid verbosity level: a
    """
    verbosity = 0

    if isinstance(verbosity_arg, list):
        for arg in verbosity_arg:
            if arg.isdigit():
                verbosity += int(arg)
            else:
                verbosity += 1

                for c in arg:
                    if c == "v":
                        verbosity += 1
                    else:
                        raise ValueError(f"invalid verbosity level: {arg}")
    else:
        verbosity = int(verbosity_arg)

    return verbosity


def expand_filepath(filepath: str) -> str:
    """
    Expand a file path.

    :param filepath: The file path to expand.
    :return: The expanded file path.

    :Example:
    #>>> expand_filepath('~/test')
    #'/home/username/test'
    #>>> expand_filepath('$HOME/test')
    #'/home/username/test'

    .. todo:: testing
    """
    filepath = os.path.expanduser(filepath)
    filepath = os.path.expandvars(filepath)
    return filepath


def sanitize_path(path: str) -> str:
    """
    Sanitize a path.

    :param path: The path to sanitize.
    :return: The sanitized path.

    :Example:
    >>> sanitize_path('/../test')
    '/test'
    >>> sanitize_path('/home/username/test')
    '/home/username/test'
    >>> sanitize_path('////etc/.././test')
    '/test'

    .. todo:: testing
    """
    path = expand_filepath(path)
    path = os.path.normpath(path)
    path = os.path.abspath(path)
    return path


def sanitize_path_options(options: Dict) -> Dict:
    """
    Sanitize the paths in the options dictionary.

    :param options: The options dictionary.
    :return: The sanitized options dictionary.

    :Example:
    >>> sanitize_path_options({'dir': '/../test', 'target': '/home/username/test'})
    {'dir': '/test', 'target': '/home/username/test'}
    >>> sanitize_path_options({'dir': '/home/username/test', 'target': None})
    {'dir': '/home/username/test', 'target': '/home/username'}

    .. todo:: testing
    """
    if options["dir"]:
        options["dir"] = sanitize_path(options["dir"])
    else:
        options["dir"] = os.getcwd()

    if options["target"]:
        options["target"] = sanitize_path(options["target"])
    else:
        options["target"] = os.path.dirname(options["dir"])

    return options


def parse_arguments(arguments: List[str], ignore_pkgs: bool) -> Tuple[Dict, List, List]:
    """
    Parse command line options and arguments.

    :param arguments: The command line arguments.
    :return: A tuple containing the options dictionary, the list of packages to delete, and the list of packages to stow.

    .. todo:: Python vs Perl regexes
    .. todo:: make 100% compatible with GNU Stow; e.g. -v before package
    .. todo:: package names with slashes - better check for validity?
    """

    parser = argparse.ArgumentParser(
        prog="StowNG",
        description="StowNG is GNU Stow in Python",
    )
    parser.add_argument(
        "-d",
        "--dir",
        metavar="DIR",
        action="store",
        help="set stow dir to DIR (default is current dir)",
    )
    parser.add_argument(
        "-t",
        "--target",
        metavar="DIR",
        action="store",
        help="set target to DIR (default is parent of stow dir)",
    )
    parser.add_argument(
        "--ignore",
        metavar="REGEX",
        action="append",
        help="ignore files ending in this Python regex",
    )
    parser.add_argument(
        "--defer",
        metavar="REGEX",
        action="append",
        help="don't stow files beginning with this Python regex if the file is already stowed to another package",
    )
    parser.add_argument(
        "--override",
        metavar="REGEX",
        action="append",
        help="force stowing files beginning with this Python regex if the file is already stowed to another package",
    )
    parser.add_argument(
        "--adopt",
        action="store_true",
        help="(Use with care!) Import existing files into stow package from target. Please read docs before using.",
    )
    parser.add_argument(
        "--no-folding",
        action="store_true",
        help="",
    )
    parser.add_argument(
        "--dotfiles",
        action="store_true",
        help="",
    )
    parser.add_argument(
        "--paranoid",
        action="store_true",
        help="",
    )
    parser.add_argument(
        "--test_mode",
        action="store_true",
        help="",
    )
    parser.add_argument(
        "-p", "--compat", action="store_true", help="use legacy algorithm for unstowing"
    )
    parser.add_argument(
        "-n",
        "--simulate",
        "--no",
        action="store_true",
        help="do not actually make any filesystem changes",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        metavar="N",
        action="append",
        help="increase verbosity (levels are from 0 to 5; -v or --verbose adds 1; --verbose=N sets level)",
        nargs="?",
        const="1",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-S",
        "--stow",
        metavar="PACKAGE",
        action="append",
        help="stow the package names that follow this option",
        nargs="+",
    )
    parser.add_argument(
        "-D",
        "--delete",
        metavar="PACKAGE",
        action="append",
        help="unstow the package names that follow this option",
        nargs="+",
    )
    parser.add_argument(
        "-R",
        "--restow",
        metavar="PACKAGE",
        action="append",
        help="restow (like stow -D followed by stow -S)",
        nargs="+",
    )
    parser.add_argument("packages", metavar="PACKAGE", action="append", nargs="*")

    args = parser.parse_args(arguments)

    if not ignore_pkgs:
        if not (args.stow or args.delete or args.restow or any(args.packages)):
            parser.error("no packages to stow or unstow")

    if args.verbose:
        try:
            verbosity = set_verbosity(args.verbose)
        except ValueError as e:
            parser.error(e.args[0])
    else:
        verbosity = None

    stow = [pkg for pkgs in args.stow for pkg in pkgs] if args.stow else []
    delete = [pkg for pkgs in args.delete for pkg in pkgs] if args.delete else []

    stow += [pkg for pkgs in args.packages for pkg in pkgs] if args.packages else []
    stow += [pkg for pkgs in args.restow for pkg in pkgs] if args.restow else []
    delete += [pkg for pkgs in args.restow for pkg in pkgs] if args.restow else []

    for pkg in stow + delete:
        pkg = pkg.rstrip("/")

        if "/" in pkg:
            parser.error(f"slashes are not permited in package names: {pkg}")

    options = {
        "dir": args.dir,
        "target": args.target,
        "ignore": [re.compile(i) for i in args.ignore] if args.ignore else [],
        "defer": [re.compile(d) for d in args.defer] if args.defer else [],
        "override": [re.compile(o) for o in args.override] if args.override else [],
        "adopt": args.adopt,
        "compat": args.compat,
        "simulate": args.simulate,
        "verbosity": verbosity,
        "dotfiles": args.dotfiles,
        "no_folding": args.no_folding,
        "paranoid": args.paranoid,
        "test_mode": args.test_mode,
    }

    return options, delete, stow


def get_config_file_options() -> Tuple[Dict, List, List]:
    """
    Get options from config files.

    :return: A tuple containing the options dictionary, the list of packages to delete, and the list of packages to stow.
    """
    options = {}
    stow = []
    delete = []

    for config in CONFIG_FILES:
        config = expand_filepath(config)

        if os.path.exists(config) and os.path.isfile(config):
            with open(config, "r") as f:
                args = []

                for line in f:
                    args += line.strip().split(" ")

                o, d, s = parse_arguments(args, True)

                if not options:
                    options.update(o)
                else:
                    options.update((k, v) for k, v in o.items() if v)

                stow += s
                delete += d

    return options, delete, stow


def process_options(args: List[str]):
    """
    Process command line options and arguments.
    Preference: command line > local config file > user config file > defaults.
        If boolean option is specified in any config file, it is set to True.

    :return: A tuple containing the options dictionary, the list of packages to delete, and the list of packages to stow.

    .. todo:: Check if this is 100% compatible with GNU Stow.
    """
    options, delete, stow = parse_arguments(args, False)
    rc_options, _, _ = get_config_file_options()

    for opt in options:
        if not options[opt] and rc_options[opt]:
            options[opt] = rc_options[opt]

    options = sanitize_path_options(options)
    print(options)
    # no check, since already checked in parse_options()

    return options, delete, stow
