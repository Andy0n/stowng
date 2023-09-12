# -*- coding: utf-8 -*-
import argparse
import re
from typing import Dict, List, Tuple

from . import __version__


def set_verbosity(verbosity_arg: List[str] or None):
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
    >>> set_verbosity(None)
    0
    >>> set_verbosity([])
    0
    >>> set_verbosity(['a'])
    Traceback (most recent call last):
        ...
    ValueError: invalid verbosity level: a
    """
    verbosity = 0

    if verbosity_arg == None:
        verbosity = 0
    elif isinstance(verbosity_arg, list):
        for arg in verbosity_arg:
            if arg.isdigit():
                verbosity += int(arg)
            else:
                verbosity += 1

                for c in arg:
                    if c == 'v':
                        verbosity += 1
                    else: 
                        raise ValueError(f'invalid verbosity level: {arg}')    
    else:
        verbosity = int(verbosity_arg)

    return verbosity


def parse_options() -> Tuple[Dict, List, List]:
    """
    Parse command line options and arguments.

    :return: A tuple containing the options dictionary, the list of packages to delete, and the list of packages to stow.

    .. todo:: Python vs Perl regexes
    .. todo:: make 100% compatible with GNU Stow; e.g. -v before package
    """

    parser = argparse.ArgumentParser(
        prog='StowNG',
        description='StowNG is GNU Stow in Python',
    )
    parser.add_argument('-d', '--dir', metavar='DIR', action='store', help='set stow dir to DIR (default is current dir)', default='.')
    parser.add_argument('-t', '--target', metavar='DIR', action='store', help='set target to DIR (default is parent of stow dir)', default='..')
    parser.add_argument('--ignore', metavar='REGEX', action='store', help='ignore files ending in this Python regex')
    parser.add_argument('--defer', metavar='REGEX', action='store', help='don\'t stow files beginning with this Python regex if the file is already stowed to another package')
    parser.add_argument('--override', metavar='REGEX', action='store', help='force stowing files beginning with this Python regex if the file is already stowed to another package')
    parser.add_argument('--adopt', action='store_true', help='(Use with care!) Import existing files into stow package from target. Please read docs before using.')
    parser.add_argument('-p', '--compat', action='store_true', help='use legacy algorithm for unstowing')
    parser.add_argument('-n', '--simulate', '--no', action='store_true', help='do not actually make any filesystem changes')
    parser.add_argument('-v', '--verbose', metavar='N', action='append', help='increase verbosity (levels are from 0 to 5; -v or --verbose adds 1; --verbose=N sets level)', nargs='?', const='1')
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('-S', '--stow', metavar='PACKAGE', action='append', help='stow the package names that follow this option', nargs='+')
    parser.add_argument('-D', '--delete', metavar='PACKAGE', action='append', help='unstow the package names that follow this option', nargs='+')
    parser.add_argument('-R', '--restow', metavar='PACKAGE', action='append', help='restow (like stow -D followed by stow -S)', nargs='+')
    parser.add_argument('packages', metavar='PACKAGE', action='append', nargs='*')

    args = parser.parse_args()

    if not (args.stow or args.delete or args.restow or any(args.packages)):
        parser.error('no packages specified')

    try:
        verbosity = set_verbosity(args.verbose)
    except ValueError as e:
        parser.error(e.args[0])

    stow = [pkg for pkgs in args.stow for pkg in pkgs] if args.stow else []
    delete = [pkg for pkgs in args.delete for pkg in pkgs] if args.delete else []
    restow = [pkg for pkgs in args.restow for pkg in pkgs] if args.restow else []
    packages = [pkg for pkgs in args.packages for pkg in pkgs] if args.packages else []

    options = {
        'dir': args.dir,
        'target': args.target,
        'ignore': re.compile(args.ignore) if args.ignore else None,
        'defer': re.compile(args.defer) if args.defer else None,
        'override': re.compile(args.override) if args.override else None,
        'adopt': args.adopt,
        'compat': args.compat,
        'simulate': args.simulate,
        'verbosity': verbosity,
    }

    return options, delete + restow, packages + stow + restow


def process_options():
    """
    Process command line options and arguments.
    """
    options, stow, delete = parse_options()


if __name__ == "__main__":
    import doctest
    doctest.testmod()
