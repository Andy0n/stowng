import logging

from .parser import process_options
from .farmer import Farmer
from .cwd import change_cwd

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

    farmer = Farmer(options)

    with change_cwd(options["target"]):
        farmer.plan_unstow(pkgs_to_delete)
        farmer.plan_stow(pkgs_to_stow)

        conflicts = farmer.get_conflicts()

        if len(conflicts) > 0:
            for action in ("stow", "unstow"):
                if action in conflicts:
                    for package in conflicts[action]:
                        log.warn(
                            f"WARNING! {action}ing {package} would cause conflicts:"
                        )

                        for message in conflicts[action][package]:
                            log.warn(f"  * {message}")

            log.warn("All operations aborted.")
            raise Exception("conflicts detected")
        else:
            if options["simulate"]:
                log.info(f"WARNING: in simulation mode so not modifying filesystem.")
                return

            farmer.process_tasks()


if __name__ == "__main__":
    main()
