from __future__ import annotations

import errno
import inspect
import stat
import unittest
from pathlib import Path

from pyfakefs.fake_filesystem import FakeFilesystem, OSType
from pyfakefs.fake_os import FakeOsModule


SUBMITTED_MODULE = Path("/workspace/pyfakefs/fake_os.py")


def make_fake_os() -> tuple[FakeFilesystem, FakeOsModule]:
    filesystem = FakeFilesystem(path_separator="/")
    filesystem.is_windows_fs = False
    return filesystem, FakeOsModule(filesystem)


class MakedirsParentTraversalAcceptance(unittest.TestCase):
    def test_imports_submitted_fake_os_module(self) -> None:
        source = Path(inspect.getsourcefile(FakeOsModule.makedirs) or "").resolve()
        self.assertEqual(SUBMITTED_MODULE.resolve(), source)

    def test_single_parent_component_preserves_both_directories(self) -> None:
        _, fake_os = make_fake_os()

        fake_os.makedirs("/project/cache/../result")

        self.assertTrue(fake_os.path.isdir("/project/cache"))
        self.assertTrue(fake_os.path.isdir("/project/result"))
        self.assertFalse(fake_os.path.exists("/project/cache/result"))

    def test_multiple_parent_components_preserve_each_walked_directory(self) -> None:
        _, fake_os = make_fake_os()

        fake_os.makedirs("/project/build/deep/../../release")

        for path in (
            "/project/build",
            "/project/build/deep",
            "/project/release",
        ):
            self.assertTrue(fake_os.path.isdir(path), path)
        self.assertFalse(fake_os.path.exists("/project/build/deep/release"))

    def test_bytes_path_preserves_traversal_side_effect(self) -> None:
        _, fake_os = make_fake_os()

        fake_os.makedirs(b"/payload/staging/../ready")

        self.assertTrue(fake_os.path.isdir(b"/payload/staging"))
        self.assertTrue(fake_os.path.isdir(b"/payload/ready"))

    def test_trailing_separator_does_not_erase_walked_directory(self) -> None:
        _, fake_os = make_fake_os()

        fake_os.makedirs("/archive/work/../complete/")

        self.assertTrue(fake_os.path.isdir("/archive/work"))
        self.assertTrue(fake_os.path.isdir("/archive/complete"))

    def test_windows_components_are_walked_before_parent_resolution(self) -> None:
        filesystem = FakeFilesystem(path_separator="/")
        filesystem.os = OSType.WINDOWS
        fake_os = FakeOsModule(filesystem)

        fake_os.makedirs(r"C:\workspace\first\..\second\third\..\done")

        for path in (
            r"C:\workspace\first",
            r"C:\workspace\second",
            r"C:\workspace\second\third",
            r"C:\workspace\second\done",
        ):
            self.assertTrue(fake_os.path.isdir(path), path)

    def test_preexisting_ancestor_keeps_component_order(self) -> None:
        _, fake_os = make_fake_os()
        fake_os.makedirs("/data")

        fake_os.makedirs("/data/scratch/../published")

        self.assertTrue(fake_os.path.isdir("/data/scratch"))
        self.assertTrue(fake_os.path.isdir("/data/published"))

    def test_existing_leaf_with_exist_ok_false_still_creates_walked_parent(self) -> None:
        _, fake_os = make_fake_os()
        fake_os.makedirs("/output/final")

        with self.assertRaises(FileExistsError):
            fake_os.makedirs("/output/intermediate/../final", exist_ok=False)

        self.assertTrue(fake_os.path.isdir("/output/intermediate"))

    def test_existing_leaf_with_exist_ok_true_succeeds_after_traversal(self) -> None:
        _, fake_os = make_fake_os()
        fake_os.makedirs("/output/final")

        fake_os.makedirs("/output/intermediate/../final", exist_ok=True)

        self.assertTrue(fake_os.path.isdir("/output/intermediate"))
        self.assertTrue(fake_os.path.isdir("/output/final"))

    def test_existing_file_is_not_accepted_by_exist_ok(self) -> None:
        filesystem, fake_os = make_fake_os()
        filesystem.create_dir("/output")
        filesystem.create_file("/output/final")

        with self.assertRaises(FileExistsError):
            fake_os.makedirs("/output/intermediate/../final", exist_ok=True)

        self.assertTrue(fake_os.path.isdir("/output/intermediate"))
        self.assertTrue(fake_os.path.isfile("/output/final"))

    def test_file_parent_error_is_not_swallowed(self) -> None:
        filesystem, fake_os = make_fake_os()
        filesystem.create_dir("/blocked")
        filesystem.create_file("/blocked/file")

        with self.assertRaises(OSError) as raised:
            fake_os.makedirs("/blocked/file/child/../result", exist_ok=True)

        self.assertEqual(errno.ENOTDIR, raised.exception.errno)
        self.assertFalse(fake_os.path.exists("/blocked/result"))

    def test_requested_mode_is_applied_only_to_leaf(self) -> None:
        _, fake_os = make_fake_os()
        previous_umask = fake_os.umask(0o022)
        self.addCleanup(fake_os.umask, previous_umask)

        fake_os.makedirs("/modes/transient/../leaf", mode=0o700)

        intermediate_mode = stat.S_IMODE(fake_os.stat("/modes/transient").st_mode)
        leaf_mode = stat.S_IMODE(fake_os.stat("/modes/leaf").st_mode)
        self.assertEqual(0o755, intermediate_mode)
        self.assertEqual(0o700, leaf_mode)


if __name__ == "__main__":
    unittest.main()
