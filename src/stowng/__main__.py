import logging
import os

from .parser import process_options
from .stow import Stow

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def main():
    """
    The main function.

    .. todo:: testing
    .. todo:: documentation
    .. todo:: logging levels correct?
    """
    options, pkgs_to_delete, pkgs_to_stow = process_options()

    logging.getLogger().setLevel(10 * options["verbosity"])

    # log.debug(f"Options:")
    # for key, value in options.items():
    #     log.debug(f"    {key}: {value}")

    stow = Stow(options, pkgs_to_stow, pkgs_to_delete)

    cwd = os.getcwd()

    os.chdir(options["target"])
    log.debug(f"cwd now {os.getcwd()}")
    stow.plan_unstow(pkgs_to_delete)
    os.chdir(cwd)
    log.debug(f"cwd restored to {os.getcwd()}")

    os.chdir(options["target"])
    log.debug(f"cwd now {os.getcwd()}")
    stow.plan_stow(pkgs_to_stow)
    os.chdir(cwd)
    log.debug(f"cwd restored to {os.getcwd()}")

    if len(stow.conflicts) > 0:
        for action in ("stow", "unstow"):
            if action in stow.conflicts:
                for package in stow.conflicts[action]:
                    log.warn(f"WARNING! {action}ing {package} would cause conflicts:")

                    for message in stow.conflicts[action][package]:
                        log.warn(f"  * {message}")

        log.warn("All operations aborted.")
        raise Exception("conflicts detected")
    else:
        if options["simulate"]:
            log.info(f"WARNING: in simulation mode so not modifying filesystem.")
            return

        os.chdir(options["target"])
        stow.process_tasks()
        os.chdir(cwd)


if __name__ == "__main__":
    main()
