import logging

from .parser import process_options

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def main():
    """
    The main function.

    .. todo:: testing
    .. todo:: documentation
    .. todo:: logging levels correct?
    """
    options, delete, stow = process_options()

    logging.getLogger().setLevel(10*options['verbosity'])

    log.debug(f'Options:')
    for key, value in options.items():
        log.debug(f'    {key}: {value}')

    print('Hello, StowNG!')

if __name__ == '__main__':
    main()
