import sys

from . import stowng


def main():
    """
    The main function.

    .. todo:: testing
    .. todo:: documentation
    .. todo:: logging levels correct?
    """
    stowng.main(sys.argv[1:])


if __name__ == "__main__":
    main()
