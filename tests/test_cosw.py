import concurrent.futures
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPOSITORY = pathlib.Path(__file__).resolve().parents[1]
COSW = REPOSITORY / "skills" / "cos-safe-writes" / "cosw.py"


class SafeWriterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.data = pathlib.Path(self.temporary.name)
        (self.data / "_memory.md").write_text("# Agent Memory\n", encoding="utf-8")
        (self.data / "_session-log.md").write_text("# Session Log\n", encoding="utf-8")
        (self.data / "_dashboard.md").write_text("# Dashboard\n", encoding="utf-8")
        (self.data / "_registry.json").write_text(
            json.dumps({"schema_version": 1, "projects": {}}) + "\n",
            encoding="utf-8",
        )
        self.environment = os.environ.copy()
        self.environment["COS_DATA_DIR"] = str(self.data)
        snapshot = self.run_cosw("snapshot", "--quiet")
        self.session = snapshot.stdout.strip()
        self.environment["COSW_SESSION"] = self.session

    def tearDown(self):
        self.temporary.cleanup()

    def run_cosw(self, *arguments, check=True):
        return subprocess.run(
            [sys.executable, str(COSW)] + list(arguments),
            env=self.environment,
            text=True,
            capture_output=True,
            check=check,
        )

    def test_parallel_memory_appends_have_no_loss_or_duplicates(self):
        entries = ["2026-09-30: preference %02d" % value for value in range(24)]

        def append(entry):
            return self.run_cosw("append-memory", entry).returncode

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(append, entries + entries[:4]))

        self.assertEqual(results, [0] * len(results))
        memory = (self.data / "_memory.md").read_text(encoding="utf-8")
        for entry in entries:
            self.assertEqual(memory.count(entry), 1)

        report = json.loads(self.run_cosw("check", "--json").stdout)
        self.assertEqual(len(report["files"]["_memory.md"]["added_by_me"]), 24)
        self.assertFalse(report["files"]["_memory.md"]["my_writes_missing"])

    def test_log_insert_is_first_and_idempotent(self):
        old = "## 2026-09-29 09:00: General\n\n**Topics:** Old\n"
        (self.data / "_session-log.md").write_text("# Session Log\n\n" + old, encoding="utf-8")
        block = self.data / "block.md"
        block.write_text(
            "## 2026-09-30 10:00: Example\n\n**Topics:** New\n",
            encoding="utf-8",
        )
        self.run_cosw("insert-log", "--block", str(block))
        self.run_cosw("insert-log", "--block", str(block))
        content = (self.data / "_session-log.md").read_text(encoding="utf-8")
        self.assertEqual(content.count("## 2026-09-30 10:00: Example"), 1)
        self.assertLess(content.index("10:00: Example"), content.index("09:00: General"))
        self.assertIn("[session:%s]" % self.session, content)
        report = json.loads(self.run_cosw("check", "--json").stdout)
        key = "## 2026-09-30 10:00: Example [session:%s]" % self.session
        self.assertIn(key, report["files"]["_session-log.md"]["added_by_me"])
        self.assertNotIn(key, report["files"]["_session-log.md"]["my_writes_missing"])

    def test_same_heading_from_two_sessions_is_not_deduplicated(self):
        block = self.data / "block.md"
        block.write_text("## 2026-09-30 10:00: Example\n\n**Topics:** Work\n", encoding="utf-8")
        self.run_cosw("insert-log", "--block", str(block))
        second = self.run_cosw("snapshot", "--quiet").stdout.strip()
        self.environment["COSW_SESSION"] = second
        self.run_cosw("insert-log", "--block", str(block))
        content = (self.data / "_session-log.md").read_text(encoding="utf-8")
        self.assertEqual(content.count("## 2026-09-30 10:00: Example"), 2)
        self.assertIn("[session:%s]" % self.session, content)
        self.assertIn("[session:%s]" % second, content)

    def test_check_detects_lost_owned_write_and_restore_recovers_only_it(self):
        mine = "2026-09-30: mine"
        self.run_cosw("append-memory", mine)
        (self.data / "_memory.md").write_text(
            "# Agent Memory\n2026-09-30: another session\n",
            encoding="utf-8",
        )
        report = json.loads(self.run_cosw("check", "--json").stdout)
        memory = report["files"]["_memory.md"]
        self.assertIn(mine, memory["my_writes_missing"])
        self.assertIn("2026-09-30: another session", memory["added_by_others"])

        self.run_cosw("restore")
        restored = (self.data / "_memory.md").read_text(encoding="utf-8")
        self.assertIn(mine, restored)
        self.assertIn("2026-09-30: another session", restored)

    def test_target_path_cannot_escape_data_directory(self):
        block = self.data / "block.md"
        block.write_text("## Example\n", encoding="utf-8")
        result = self.run_cosw(
            "insert-log", "--target", "../outside.md", "--block", str(block), check=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beneath COS_DATA_DIR", result.stderr)

    def test_clobbered_whole_file_write_is_reported_as_mine_lost(self):
        proposed = self.data / "proposed.json"
        proposed.write_text(
            json.dumps({"schema_version": 1, "projects": {"example": {}}}) + "\n",
            encoding="utf-8",
        )
        self.run_cosw("write", "--target", "_registry.json", "--file", str(proposed))
        (self.data / "_registry.json").write_text(
            json.dumps({"schema_version": 1, "projects": {}}) + "\n",
            encoding="utf-8",
        )
        report = json.loads(self.run_cosw("check", "--json").stdout)
        self.assertIn("whole", report["files"]["_registry.json"]["my_writes_missing"])
        restore = self.run_cosw("restore", check=False)
        self.assertEqual(restore.returncode, 1)
        self.assertIn("CANNOT AUTO RESTORE", restore.stdout)

    def test_external_log_overwrite_is_not_attributed_to_this_session(self):
        block = self.data / "block.md"
        block.write_text("## 2026-09-30 10:00: Example\n\nOriginal\n", encoding="utf-8")
        self.run_cosw("insert-log", "--block", str(block))
        path = self.data / "_session-log.md"
        path.write_text(path.read_text(encoding="utf-8").replace("Original", "Externally changed"), encoding="utf-8")
        report = json.loads(self.run_cosw("check", "--json").stdout)
        entry = report["files"]["_session-log.md"]
        expected_key = "## 2026-09-30 10:00: Example [session:%s]" % self.session
        self.assertIn(expected_key, entry["added_by_others"])
        self.assertIn(expected_key, entry["my_writes_missing"])
        self.assertNotIn(expected_key, entry["edited_by_me"])

    def test_intentional_deletion_is_owned_and_later_resurrection_is_lost_write(self):
        path = self.data / "_memory.md"
        path.write_text("# Agent Memory\nremove me\nkeep me\n", encoding="utf-8")
        self.environment["COSW_SESSION"] = self.run_cosw("snapshot", "--quiet").stdout.strip()
        proposed = self.data / "proposed-memory.md"
        proposed.write_text("# Agent Memory\nkeep me\n", encoding="utf-8")
        self.run_cosw("write", "--target", "_memory.md", "--file", str(proposed))

        report = json.loads(self.run_cosw("check", "--json").stdout)
        entry = report["files"]["_memory.md"]
        self.assertIn("remove me", entry["deleted_by_me"])
        self.assertNotIn("remove me", entry["lost_from_base"])

        path.write_text("# Agent Memory\nremove me\nkeep me\n", encoding="utf-8")
        report = json.loads(self.run_cosw("check", "--json").stdout)
        self.assertIn("remove me", report["files"]["_memory.md"]["my_writes_missing"])

    def test_merge_does_not_claim_other_sessions_nonoverlapping_edit(self):
        path = self.data / "_memory.md"
        path.write_text(
            "# Agent Memory\nleft: old\nmiddle\nright: old\n",
            encoding="utf-8",
        )
        self.environment["COSW_SESSION"] = self.run_cosw("snapshot", "--quiet").stdout.strip()
        proposed = self.data / "proposed-memory.md"
        proposed.write_text(
            "# Agent Memory\nleft: old\nmiddle\nright: mine\n",
            encoding="utf-8",
        )
        path.write_text(
            "# Agent Memory\nleft: theirs\nmiddle\nright: old\n",
            encoding="utf-8",
        )
        self.run_cosw("merge", "--target", "_memory.md", "--mine", str(proposed))
        report = json.loads(self.run_cosw("check", "--json").stdout)
        entry = report["files"]["_memory.md"]
        self.assertIn("right: mine", entry["added_by_me"])
        self.assertIn("left: theirs", entry["added_by_others"])
        self.assertNotIn("left: theirs", entry["added_by_me"])
        self.assertIn("right: old", entry["deleted_by_me"])
        self.assertIn("left: old", entry["lost_from_base"])

    def test_conflict_resolution_digest_refuses_later_change(self):
        path = self.data / "_memory.md"
        path.write_text("# Agent Memory\nitem: base\n", encoding="utf-8")
        self.environment["COSW_SESSION"] = self.run_cosw("snapshot", "--quiet").stdout.strip()
        proposed = self.data / "proposed-memory.md"
        proposed.write_text("# Agent Memory\nitem: mine\n", encoding="utf-8")
        path.write_text("# Agent Memory\nitem: theirs\n", encoding="utf-8")

        conflict = self.run_cosw(
            "merge", "--target", "_memory.md", "--mine", str(proposed), check=False
        )
        self.assertEqual(conflict.returncode, 1)
        token_line = next(
            line for line in conflict.stdout.splitlines()
            if line.startswith("expected-current-sha256: ")
        )
        token = token_line.split(": ", 1)[1]
        metadata = self.data / "_memory.md.conflict.json"
        self.assertEqual(json.loads(metadata.read_text(encoding="utf-8"))["expected_current_sha256"], token)

        resolved = self.data / "resolved-memory.md"
        resolved.write_text("# Agent Memory\nitem: resolved\n", encoding="utf-8")
        path.write_text("# Agent Memory\nitem: changed later\n", encoding="utf-8")
        stale = self.run_cosw(
            "write", "--target", "_memory.md", "--file", str(resolved),
            "--force", "--expected-current-sha256", token, check=False,
        )
        self.assertEqual(stale.returncode, 1)
        self.assertIn("changed after conflict generation", stale.stdout)
        self.assertIn("item: changed later", path.read_text(encoding="utf-8"))

        unguarded = self.run_cosw(
            "write", "--target", "_memory.md", "--file", str(resolved), "--force", check=False
        )
        self.assertEqual(unguarded.returncode, 2)
        self.assertIn("requires --expected-current-sha256", unguarded.stderr)

        refreshed = self.run_cosw(
            "merge", "--target", "_memory.md", "--mine", str(proposed), check=False
        )
        refreshed_token = next(
            line for line in refreshed.stdout.splitlines()
            if line.startswith("expected-current-sha256: ")
        ).split(": ", 1)[1]
        applied = self.run_cosw(
            "write", "--target", "_memory.md", "--file", str(resolved),
            "--force", "--expected-current-sha256", refreshed_token, check=False,
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertIn("item: resolved", path.read_text(encoding="utf-8"))
        self.assertFalse((self.data / "_memory.md.conflict").exists())
        self.assertFalse((self.data / "_memory.md.conflict.json").exists())

    def test_concurrent_create_and_delete_refuse_whole_file_write(self):
        proposed = self.data / "proposed.md"
        proposed.write_text("proposed\n", encoding="utf-8")

        created = self.data / "new-state.md"
        created.write_text("", encoding="utf-8")
        create_result = self.run_cosw(
            "write", "--target", "new-state.md", "--file", str(proposed), check=False
        )
        self.assertEqual(create_result.returncode, 1)
        self.assertEqual(created.read_text(encoding="utf-8"), "")

        (self.data / "_dashboard.md").unlink()
        delete_result = self.run_cosw(
            "write", "--target", "_dashboard.md", "--file", str(proposed), check=False
        )
        self.assertEqual(delete_result.returncode, 1)
        self.assertFalse((self.data / "_dashboard.md").exists())

    def test_surgical_writes_refuse_recreating_deleted_shared_files(self):
        (self.data / "_memory.md").unlink()
        memory_result = self.run_cosw(
            "append-memory", "2026-09-30: must not recreate", check=False
        )
        self.assertEqual(memory_result.returncode, 1)
        self.assertFalse((self.data / "_memory.md").exists())

        (self.data / "_session-log.md").unlink()
        block = self.data / "block.md"
        block.write_text("## 2026-09-30 10:00: Example\n", encoding="utf-8")
        log_result = self.run_cosw("insert-log", "--block", str(block), check=False)
        self.assertEqual(log_result.returncode, 1)
        self.assertFalse((self.data / "_session-log.md").exists())

    def test_check_detects_empty_file_create_and_delete(self):
        (self.data / "_dashboard.md").unlink()
        new_session = self.run_cosw("snapshot", "--quiet").stdout.strip()
        self.environment["COSW_SESSION"] = new_session
        (self.data / "_dashboard.md").write_text("", encoding="utf-8")
        report = json.loads(self.run_cosw("check", "--json").stdout)
        self.assertTrue(report["files"]["_dashboard.md"]["file_created"])

        newer_session = self.run_cosw("snapshot", "--quiet").stdout.strip()
        self.environment["COSW_SESSION"] = newer_session
        (self.data / "_dashboard.md").unlink()
        report = json.loads(self.run_cosw("check", "--json").stdout)
        self.assertTrue(report["files"]["_dashboard.md"]["file_deleted"])

    def test_symlink_component_cannot_escape_data_directory(self):
        outside = pathlib.Path(self.temporary.name + "-outside")
        outside.mkdir()
        self.addCleanup(lambda: outside.rmdir())
        os.symlink(str(outside), str(self.data / "linked"))
        proposed = self.data / "proposed.md"
        proposed.write_text("private\n", encoding="utf-8")
        result = self.run_cosw(
            "write", "--target", "linked/escape.md", "--file", str(proposed), check=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing symlink", result.stderr)
        self.assertFalse((outside / "escape.md").exists())

    def test_created_state_uses_private_permissions(self):
        self.run_cosw("append-memory", "2026-09-30: private")
        shared_mode = (self.data / "_shared").stat().st_mode & 0o777
        lock_files = list((self.data / "_shared").glob("*.lock"))
        self.assertEqual(shared_mode, 0o700)
        self.assertTrue(lock_files)
        self.assertTrue(all((path.stat().st_mode & 0o777) == 0o600 for path in lock_files))

        proposed = self.data / "proposed.md"
        proposed.write_text("private context\n", encoding="utf-8")
        self.run_cosw(
            "write", "--target", "new-project/context.md", "--file", str(proposed)
        )
        self.assertEqual((self.data / "new-project").stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.data / "new-project/context.md").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
