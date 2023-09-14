import pytest
from stowng.farmer import Farmer

from .utils import (
    cat_file,
    dir_exists,
    link_exists,
    make_invalid_link,
    make_link,
    make_path,
    delete_dir,
    path_exists,
    change_dir,
    get_cwd,
    make_file,
    readlink,
)
from . import TEST_DIR


@pytest.fixture(autouse=True)
def test_wrapper():
    new_cwd = f"{TEST_DIR}/target"
    old_cwd = get_cwd()

    make_path(new_cwd)
    assert path_exists(new_cwd)
    change_dir(new_cwd)

    yield

    change_dir(old_cwd)
    delete_dir(TEST_DIR)
    assert not path_exists(TEST_DIR)


def test_stow_a_simple_tree_minimally():
    farmer = Farmer(dir="../stow", target=".", test_mode=True)

    make_path("../stow/pkg1/bin1")
    make_file("../stow/pkg1/bin1/file1")

    farmer.plan_stow(["pkg1"])
    farmer.process_tasks()

    assert farmer.get_conflict_count() == 0

    assert readlink("bin1") == "../stow/pkg1/bin1"


def test_stow_a_simple_tree_into_an_existing_directory():
    farmer = Farmer(dir="../stow", target=".", test_mode=True)

    make_path("../stow/pkg2/lib2")
    make_file("../stow/pkg2/lib2/file2")
    make_path("lib2")

    farmer.plan_stow(["pkg2"])
    farmer.process_tasks()

    assert farmer.get_conflict_count() == 0

    assert readlink("lib2/file2") == "../../stow/pkg2/lib2/file2"


def test_unfold_existing_tree():
    farmer = Farmer(dir="../stow", target=".", test_mode=True)

    make_path("../stow/pkg3a/bin3")
    make_file("../stow/pkg3a/bin3/file3a")
    make_link("bin3", "../stow/pkg3a/bin3")

    make_path("../stow/pkg3b/bin3")
    make_file("../stow/pkg3b/bin3/file3b")

    farmer.plan_stow(["pkg3b"])
    farmer.process_tasks()

    assert dir_exists("bin3")
    assert readlink("bin3/file3a") == "../../stow/pkg3a/bin3/file3a"
    assert readlink("bin3/file3b") == "../../stow/pkg3b/bin3/file3b"


def test_conflict_with_file():
    farmer = Farmer(dir="../stow", target=".", test_mode=True)

    make_file("bin4")
    make_path("../stow/pkg4/bin4")
    make_file("../stow/pkg4/bin4/file4")

    farmer.plan_stow(["pkg4"])

    assert farmer.get_conflict_count() == 1
    assert farmer.get_conflicts()["stow"]["pkg4"][0].startswith(
        "existing target is neither a link nor a directory: "
    )


def test_conflict_with_file_adopt():
    # appears to have same behaviour as upstream, since adopt=True is commented out as well
    # farmer = Farmer(dir="../stow", target=".", test_mode=True, adopt=True)
    farmer = Farmer(dir="../stow", target=".", test_mode=True, adopt=False)

    make_file("bin4a")
    make_path("../stow/pkg4a/bin4a")
    make_file("../stow/pkg4a/bin4a/file4a")

    farmer.plan_stow(["pkg4a"])

    assert farmer.get_conflict_count() == 1
    assert farmer.get_conflicts()["stow"]["pkg4a"][0].startswith(
        "existing target is neither a link nor a directory: "
    )


def test_link_files_conflict_no_adopt():
    farmer = Farmer(dir="../stow", target=".", test_mode=True, adopt=False)

    make_path("bin4b")
    make_file("file4b", "target")
    make_file("bin4b/file4b", "target")

    make_path("../stow/pkg4b/bin4b")
    make_file("../stow/pkg4b/file4b", "stow")
    make_file("../stow/pkg4b/bin4b/file4b", "stow")

    farmer.plan_stow(["pkg4b"])

    assert farmer.get_conflict_count() == 2
    assert farmer.get_conflicts()["stow"]["pkg4b"][0].startswith(
        "existing target is neither a link nor a directory: "
    )
    assert farmer.get_conflicts()["stow"]["pkg4b"][1].startswith(
        "existing target is neither a link nor a directory: "
    )


def test_link_files_no_conflict_adopt():
    farmer = Farmer(dir="../stow", target=".", test_mode=True, adopt=True)

    make_path("bin4c")
    make_file("file4c", "target")
    make_file("bin4c/file4c", "target")

    make_path("../stow/pkg4c/bin4c")
    make_file("../stow/pkg4c/file4c", "stow")
    make_file("../stow/pkg4c/bin4c/file4c", "stow")

    farmer.plan_stow(["pkg4c"])

    assert farmer.get_conflict_count() == 0
    assert farmer.get_task_count() == 4

    farmer.process_tasks()

    assert link_exists("file4c")
    assert link_exists("bin4c/file4c")
    assert readlink("file4c") == "../stow/pkg4c/file4c"
    assert readlink("bin4c/file4c") == "../../stow/pkg4c/bin4c/file4c"
    assert cat_file("file4c") == "target"
    assert cat_file("bin4c/file4c") == "target"


def test_target_exists_not_owned():
    farmer = Farmer(dir="../stow", target=".", test_mode=True)

    make_path("bin5")
    make_invalid_link("bin5/file5", "../../empty")
    make_path("../stow/pkg5/bin5/file5")

    farmer.plan_stow(["pkg5"])

    assert farmer.get_conflict_count() == 1
    assert farmer.get_conflicts()["stow"]["pkg5"][0].startswith(
        "existing target is not owned by stow: "
    )


def test_replace_existing_but_invalid_link():
    farmer = Farmer(dir="../stow", target=".", test_mode=True)

    make_invalid_link("file6", "../stow/path-does-not-exist")
    make_path("../stow/pkg6")
    make_file("../stow/pkg6/file6")

    farmer.plan_stow(["pkg6"])
    farmer.process_tasks()

    assert readlink("file6") == "../stow/pkg6/file6"
