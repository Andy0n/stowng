# -*- coding: utf-8 -*-
import argparse
import os

from . import __version__


def set_verbosity(verbosity_arg):
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


def parse_options():
    parser = argparse.ArgumentParser(
        prog='StowNG',
        description='StowNG is GNU Stow in Python',
    )
    parser.add_argument('-d', '--dir', metavar='DIR', action='store', help='set stow dir to DIR (default is current dir)', default='.')
    parser.add_argument('-t', '--target', metavar='DIR', action='store', help='set target to DIR (default is parent of stow dir)', default='..')
    parser.add_argument('--ignore', metavar='REGEX', action='store', help='ignore files ending in this Perl regex')
    parser.add_argument('--defer', metavar='REGEX', action='store', help='don\'t stow files beginning with this Perl regex if the file is already stowed to another package')
    parser.add_argument('--override', metavar='REGEX', action='store', help='force stowing files beginning with this Perl regex if the file is already stowed to another package')
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

    print(args)
    print(verbosity)
    print(os.path.relpath(args.dir, args.target))

    return verbosity

def process_options():
    parse_options()

