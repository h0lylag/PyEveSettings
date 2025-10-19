import zipfile
import unittest
import tempfile
from pathlib import Path
from typing import cast

from utils.backup_manager import BackupManager


class BackupManagerTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base_path = Path(self._tmpdir.name)

        # Create a fake profile directory with nested content
        self.profile_name = "settings_Default"
        self.profile_dir = self.base_path / self.profile_name
        self.profile_dir.mkdir(parents=True)

        # Populate profile with files and subdirectories
        (self.profile_dir / "core_user_123.dat").write_text("user-data", encoding="utf-8")
        nested_dir = self.profile_dir / "subdir"
        nested_dir.mkdir()
        (nested_dir / "core_char_456.dat").write_text("char-data", encoding="utf-8")

        self.manager = BackupManager(self.base_path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_create_backup_includes_profile_root(self):
        success, message, backup_path = self.manager.create_backup(self.profile_dir)

        self.assertTrue(success, message)
        self.assertIsNotNone(backup_path)
        backup_path = cast(Path, backup_path)
        self.assertTrue(backup_path.exists(), "Backup file was not created")

        with zipfile.ZipFile(backup_path, "r") as zipf:
            namelist = zipf.namelist()

        self.assertIn(
            f"{self.profile_name}/core_user_123.dat",
            namelist,
            "Profile root was not preserved in archive",
        )

    def test_restore_overwrite_removes_nested_folder(self):
        success, _, backup_path = self.manager.create_backup(self.profile_dir)
        self.assertTrue(success, "Failed to create backup for restore test")
        self.assertIsNotNone(backup_path)
        backup_path = cast(Path, backup_path)

        # Modify existing profile folder to ensure it gets replaced
        extra_file = self.profile_dir / "stale.txt"
        extra_file.write_text("stale", encoding="utf-8")

        # Restore into the same profile folder (overwrite scenario)
        restore_success, restore_message = self.manager.restore_backup(backup_path, self.profile_dir)
        self.assertTrue(restore_success, restore_message)

        # Ensure stale file was removed during restore
        self.assertFalse(extra_file.exists(), "Restore did not remove existing files")

        # Ensure restored files exist at root without nesting
        restored_file = self.profile_dir / "core_user_123.dat"
        nested_folder = self.profile_dir / self.profile_name

        self.assertTrue(restored_file.exists(), "Restored file missing at expected location")
        self.assertEqual(
            "user-data",
            restored_file.read_text(encoding="utf-8"),
            "Restored file content mismatch",
        )
        self.assertFalse(
            nested_folder.exists(),
            "Nested profile folder detected after restore",
        )


if __name__ == "__main__":
    unittest.main()
