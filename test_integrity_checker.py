import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import integrity_checker


class IntegrityCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "folder with spaces"
        self.root.mkdir()
        (self.root / "alpha.txt").write_text("alpha", encoding="utf-8")
        (self.root / "nested").mkdir()
        (self.root / "nested" / "beta.bin").write_bytes(b"beta")
        self.manifest_path = Path(self.temporary.name) / "manifest.json"

    def tearDown(self):
        self.temporary.cleanup()

    def create_manifest(self):
        manifest = integrity_checker.build_manifest(self.root, self.manifest_path)
        integrity_checker.write_json_atomic(self.manifest_path, manifest)
        return manifest

    def test_manifest_records_relative_paths_and_hashes(self):
        manifest = self.create_manifest()
        self.assertEqual(set(manifest["files"]), {"alpha.txt", "nested/beta.bin"})
        self.assertEqual(len(manifest["files"]["alpha.txt"]["sha256"]), 64)

    def test_unchanged_directory_is_clean(self):
        self.create_manifest()
        report = integrity_checker.verify_manifest(self.root, self.manifest_path)
        self.assertTrue(report["clean"])

    def test_changed_file_is_reported(self):
        self.create_manifest()
        (self.root / "alpha.txt").write_text("changed", encoding="utf-8")
        report = integrity_checker.verify_manifest(self.root, self.manifest_path)
        self.assertEqual(report["changed"], ["alpha.txt"])

    def test_missing_and_added_files_are_reported(self):
        self.create_manifest()
        (self.root / "alpha.txt").unlink()
        (self.root / "new.txt").write_text("new", encoding="utf-8")
        report = integrity_checker.verify_manifest(self.root, self.manifest_path)
        self.assertEqual(report["missing"], ["alpha.txt"])
        self.assertEqual(report["added"], ["new.txt"])

    def test_manifest_inside_root_is_excluded(self):
        inside = self.root / "integrity-manifest.json"
        manifest = integrity_checker.build_manifest(self.root, inside)
        integrity_checker.write_json_atomic(inside, manifest)
        report = integrity_checker.verify_manifest(self.root, inside)
        self.assertTrue(report["clean"])

    def test_corrupt_manifest_raises_clear_error(self):
        self.manifest_path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(integrity_checker.IntegrityError):
            integrity_checker.load_manifest(self.manifest_path)

    def test_unreadable_file_is_reported(self):
        self.create_manifest()
        original = integrity_checker.sha256_file

        def fail_for_alpha(path):
            if path.name == "alpha.txt":
                raise PermissionError("denied")
            return original(path)

        with mock.patch("integrity_checker.sha256_file", side_effect=fail_for_alpha):
            report = integrity_checker.verify_manifest(self.root, self.manifest_path)
        self.assertFalse(report["clean"])
        self.assertEqual(report["unreadable"][0]["path"], "alpha.txt")

    def test_cli_returns_one_when_changes_exist(self):
        self.create_manifest()
        (self.root / "new.txt").write_text("new", encoding="utf-8")
        code = integrity_checker.main(
            ["check", str(self.root), "--manifest", str(self.manifest_path), "--json"]
        )
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
