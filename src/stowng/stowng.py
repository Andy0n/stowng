# -*- coding: utf-8 -*-
from . import __version__
import argparse

def main():
    parser = argparse.ArgumentParser(
        prog='StowNG',
        description='StowNG is GNU Stow in Python',
    )
    parser.add_argument('-d', '--dir', metavar='DIR', action='store', help='set stow dir to DIR (default is current dir)', default='.')
    parser.add_argument('-t', '--target', metavar='DIR', action='store', help='set target to DIR (default is parent of stow dir)', default='..')
    parser.add_argument('-S', '--stow', metavar='PACKAGE', action='append', help='stow the package names that follow this option', nargs='+')
    parser.add_argument('-D', '--delete', metavar='PACKAGE', action='append', help='unstow the package names that follow this option', nargs='+')
    parser.add_argument('-R', '--restow', metavar='PACKAGE', action='append', help='restow (like stow -D followed by stow -S)', nargs='+')
    parser.add_argument('--ignore', metavar='REGEX', action='store', help='ignore files ending in this Perl regex')
    parser.add_argument('--defer', metavar='REGEX', action='store', help='don\'t stow files beginning with this Perl regex if the file is already stowed to another package')
    parser.add_argument('--override', metavar='REGEX', action='store', help='force stowing files beginning with this Perl regex if the file is already stowed to another package')
    parser.add_argument('--adopt', action='store_true', help='(Use with care!) Import existing files into stow package from target. Please read docs before using.')
    parser.add_argument('-p', '--compat', action='store_true', help='use legacy algorithm for unstowing')
    parser.add_argument('-n', '--no', '--simulate', action='store_true', help='do not actually make any filesystem changes')
    parser.add_argument('-v', '--verbose', metavar='N', action='append', help='increase verbosity (levels are from 0 to 5; -v or --verbose adds 1; --verbose=N sets level)', nargs='?', const='1')
    # TODO: -vv.. does not work: add all values in list, and count number of v's
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    print('Hello, StowNG!')
    print(args)
