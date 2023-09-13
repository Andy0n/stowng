import logging
import os

from .parser import process_options
from .stow import Stow 

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def main():
    """
    The main function.

    .. todo:: testing
    .. todo:: documentation
    .. todo:: logging levels correct?
    """
    options, pkgs_to_delete, pkgs_to_stow = process_options()

    logging.getLogger().setLevel(10*options['verbosity'])

    log.debug(f'Options:')
    for key, value in options.items():
        log.debug(f'    {key}: {value}')

    stow = Stow(options, pkgs_to_stow, pkgs_to_delete) 

    cwd = os.getcwd()
    os.chdir(options['target'])
    stow.plan_unstow(pkgs_to_delete)
    stow.plan_stow(pkgs_to_stow)
    os.chdir(cwd)

    print('Hello, StowNG!')

if __name__ == '__main__':
    main()
