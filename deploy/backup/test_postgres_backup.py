import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from postgres_backup import backup, name, prune, restore, safe_directory, verified_manifest


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, stem="postgres_autoforce_20260101T000000000000Z"):
        archive = self.root / (stem + ".dump")
        archive.write_bytes(b"PGDMP\x00mock")
        data = {"schema": 1, "engine": "postgresql", "database": "autoforce",
                "created_utc": stem.split("_")[-1], "archive": archive.name,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "bytes": archive.stat().st_size, "encrypted": False}
        manifest = self.root / (stem + ".manifest.json")
        manifest.write_text(json.dumps(data), encoding="utf-8")
        return manifest, archive

    def test_reject_invalid_identifiers_and_root(self):
        for bad in ("", "db;drop", "other-db", "test/db", "123foo"):
            with self.assertRaises(ValueError):
                name(bad)
        with self.assertRaises(ValueError):
            safe_directory(Path(self.root.anchor))
        with self.assertRaises(ValueError):
            safe_directory(self.root / "missing")

    def test_checksum_and_manifest_path_verification(self):
        manifest, archive = self.fixture()
        self.assertEqual(verified_manifest(self.root, manifest.name)[0]["database"], "autoforce")
        archive.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum"):
            verified_manifest(self.root, manifest.name)
        with self.assertRaises(ValueError):
            verified_manifest(self.root, "../other.manifest.json")

    def test_symlinks_not_followed(self):
        manifest, archive = self.fixture()
        link = self.root / "postgres_autoforce_link.manifest.json"
        try:
            link.symlink_to(manifest)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):
            verified_manifest(self.root, link.name)
        dir_link = self.root / "linkdir"
        dir_link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            safe_directory(dir_link)

    def test_manifest_binds_db_and_timestamp_before_restore(self):
        manifest, archive = self.fixture()
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["created_utc"] = "not-a-timestamp"
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with patch("postgres_backup.run") as execute:
            with self.assertRaises(ValueError):
                restore(self.root, manifest.name, "qa_rehearsal")
            execute.assert_not_called()
        data["created_utc"] = "20260101T000001000000Z"
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "identifier"):
            verified_manifest(self.root, manifest.name)

    def test_untrusted_report_cannot_overwrite_manifest(self):
        from postgres_backup import json_atomic
        manifest, _ = self.fixture()
        with self.assertRaises(FileExistsError):
            json_atomic(manifest, {"status": "failed"})
        self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["schema"], 1)

    def test_restore_rejects_mismatched_connection_database(self):
        manifest, _ = self.fixture()
        with patch("postgres_backup.query", return_value="wrong_database"), patch("postgres_backup.run") as execute:
            with self.assertRaisesRegex(ValueError, "does not match"):
                restore(self.root, manifest.name, "qa_rehearsal")
            execute.assert_not_called()

    def test_backup_atomic_metadata_and_no_secrets(self):
        calls = []
        def fake_run(args, *, out=None):
            calls.append(args)
            if args[0] == "pg_dump":
                Path(args[args.index("--file") + 1]).write_bytes(b"PGDMP\x00mock")
        with patch("postgres_backup.run", side_effect=fake_run):
            data = backup(self.root, "autoforce")
        self.assertEqual([c[0] for c in calls], ["pg_dump", "pg_restore"])
        self.assertTrue((self.root / data["archive"]).exists())
        self.assertEqual(verified_manifest(self.root, data["archive"].replace(".dump", ".manifest.json"))[0], data)
        self.assertNotIn("password", json.dumps(data))

    def test_restore_requires_rehearsal_and_empty_target(self):
        manifest, _ = self.fixture()
        with self.assertRaises(ValueError):
            restore(self.root, manifest.name, "production")
        with patch("postgres_backup.run") as execute, patch("postgres_backup.query", side_effect=["qa_rehearsal", "1"]):
            with self.assertRaisesRegex(ValueError, "empty"):
                restore(self.root, manifest.name, "qa_rehearsal")
        execute.assert_called_once()

    def test_retention_removes_only_verified_pairs(self):
        old, archive = self.fixture()
        unrelated = self.root / "unrelated.txt"
        unrelated.write_text("keep")
        self.assertEqual(prune(self.root, days=0, max_copies=1), [old.name])
        self.assertFalse(old.exists())
        self.assertFalse(archive.exists())
        self.assertTrue(unrelated.exists())
        with self.assertRaises(ValueError):
            prune(self.root, days=-1, max_copies=1)


if __name__ == "__main__":
    unittest.main()
