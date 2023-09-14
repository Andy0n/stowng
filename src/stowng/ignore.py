import os
import re
import logging
from typing import List, Tuple
from importlib.resources import files

from .utils import join
from . import LOCAL_IGNORE_FILE, GLOBAL_IGNORE_FILE

log = logging.getLogger(__name__)


class Ignore:
    def __init__(self, ignore: List[re.Pattern]) -> None:
        self._ignore = ignore
        self.ignore_file_regexps = {}
        self.default_global_ignore_regexps = self._get_default_global_ignore_regexps()

    def ignore(self, stow_path: str, package: str, target: str) -> bool:
        """
        Determine if a target should be ignored.

        :param stow_path: The path to the stow directory.
        :param package: The name of the package.
        :param target: The target to check.

        :returns: True if the target should be ignored, False otherwise.
        """

        if len(target) < 1:
            log.error(f"::ignore() called with empty target")
            raise Exception(f"::ignore() called with empty target")

        for suffix in self._ignore:
            if suffix.match(target):
                log.debug(f"  Ignoring path {target} due to --ignore={suffix}")
                return True

        package_dir = join(stow_path, package)
        path_regexp, segment_regexp = self.get_ignore_regexps(package_dir)
        log.debug(f"    Ignore list regexp for paths: {path_regexp}")
        log.debug(f"    Ignore list regexp for segments: {segment_regexp}")

        if path_regexp is not None and path_regexp.match(target):
            log.debug(f"  Ignoring path {target}")
            return True

        basename = os.path.basename(target)

        if segment_regexp is not None and segment_regexp.match(basename):
            log.debug(f"  Ignoring path segment {target}")
            return True

        log.debug(f"  Not ignoring {target}")
        return False

    def get_ignore_regexps(self, dir: str) -> Tuple[re.Pattern, re.Pattern]:
        """
        Get the ignore regexps.

        :param dir: The directory to check.

        :returns: The ignore regexps.
        """
        home = os.environ.get("HOME")
        path_regexp = join(dir, LOCAL_IGNORE_FILE)
        segment_regexp = join(home, GLOBAL_IGNORE_FILE) if home is not None else None

        for file in (path_regexp, segment_regexp):
            if file is not None and os.path.exists(file):
                log.debug(f"  Using ignore file: {file}")
                return self.get_ignore_regexps_from_file(file)
            else:
                log.debug(f"  {file} didn't exist")

        log.debug("  Using built-in ignore list")
        return self.default_global_ignore_regexps

    def get_ignore_regexps_from_file(self, file: str) -> Tuple[re.Pattern, re.Pattern]:
        """
        Get ignore regexps from a file.

        :param file: The file to read.

        :returns: The ignore regexps.
        """

        if file in self.ignore_file_regexps:
            log.debug(f"   Using memoized regexps from {file}")
            return self.ignore_file_regexps[file]

        regexps = self.get_ignore_regexps_from_filename(file)

        self.ignore_file_regexps[file] = regexps
        return regexps

    def get_ignore_regexps_from_filename(
        self, filename: str
    ) -> Tuple[re.Pattern, re.Pattern]:
        """
        Get ignore regexps from a filename.

        :param filename: The filename to read.

        :returns: The ignore regexps.

        .. todo:: error handling
        """
        regexps = []

        with open(filename, "r") as f:
            regexps = self.get_ignore_regexps_from_data(f.read())

        return self.compile_ignore_regexps(regexps)

    def get_ignore_regexps_from_data(self, data: str) -> List[str]:
        """
        Get ignore regexps from data.

        :param data: The data to read.

        :returns: The ignore regexps.
        """
        regexps = []

        for line in data.splitlines():
            line = line.strip()

            if line == "" or line.startswith("#"):
                continue

            regexps.append(re.sub("\\s+#.+$", "", line).replace("\\#", "#").strip())

        return regexps

    def compile_ignore_regexps(
        self, regexps: List[str]
    ) -> Tuple[re.Pattern, re.Pattern]:
        """
        Compile ignore regexps.

        :param regexps: The regexps to compile.

        :returns: The compiled regexps.
        """
        path_regexps = []
        segment_regexps = []

        for regexp in regexps:
            if "/" in regexp:
                path_regexps.append(regexp)
            else:
                segment_regexps.append(regexp)

        path_regexp = re.compile("|".join(path_regexps))
        segment_regexp = re.compile("|".join(segment_regexps))

        return path_regexp, segment_regexp

    def _get_default_global_ignore_regexps(self) -> Tuple[re.Pattern, re.Pattern]:
        """
        Get the default global ignore regexps.

        :returns: The default global ignore regexps.
        """
        data = files("stowng.data").joinpath("default-ignore-list").read_text()

        return self.compile_ignore_regexps(self.get_ignore_regexps_from_data(data))
