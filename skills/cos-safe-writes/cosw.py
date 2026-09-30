#!/usr/bin/env python3
"""Concurrency safe writer for shared Chief of Staff project data."""

import argparse
import difflib
import fcntl
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime


DATA_DIR = os.path.realpath(os.path.abspath(os.path.expanduser(os.environ.get(
    "COS_DATA_DIR", "~/chief-of-staff/projects"
))))
SHARED_DIR = os.path.join(DATA_DIR, "_shared")
SNAPSHOT_DIR = os.path.join(SHARED_DIR, "snapshots")
GLOBAL_FILES = [
    "_memory.md",
    "_session-log.md",
    "_registry.json",
    "_dashboard.md",
]
PROJECT_FILE_FIELDS = ("context_file", "index_file", "pending_file")


def fail(message, code=2):
    sys.stderr.write("cosw: %s\n" % message)
    raise SystemExit(code)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def ensure_private_dir(path):
    if os.path.islink(path):
        fail("refusing symlinked state directory: %s" % path)
    if os.path.isdir(path):
        return
    if os.path.exists(path):
        fail("state directory path is not a directory: %s" % path)
    os.makedirs(path, mode=0o700)
    os.chmod(path, 0o700)


def safe_relative(value):
    value = value.replace("\\", "/")
    normalized = os.path.normpath(value)
    if os.path.isabs(value) or normalized == ".." or normalized.startswith("../"):
        fail("target must stay beneath COS_DATA_DIR: %s" % value)
    return normalized


def data_path(relative):
    relative = safe_relative(relative)
    path = os.path.abspath(os.path.join(DATA_DIR, relative))
    current = DATA_DIR
    for component in relative.split(os.sep):
        current = os.path.join(current, component)
        if os.path.islink(current):
            fail("refusing symlink beneath COS_DATA_DIR: %s" % relative)
    resolved = os.path.realpath(path)
    if os.path.commonpath([DATA_DIR, resolved]) != DATA_DIR:
        fail("target escapes COS_DATA_DIR: %s" % relative)
    return path


def atomic_write(path, text):
    parent = os.path.dirname(path) or "."
    parent_created = not os.path.isdir(parent)
    os.makedirs(parent, mode=0o700, exist_ok=True)
    if parent_created:
        resolved_parent = os.path.realpath(parent)
        if os.path.commonpath([DATA_DIR, resolved_parent]) == DATA_DIR:
            os.chmod(parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".cosw-", dir=parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if os.path.exists(path):
            shutil.copymode(path, temporary)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


class Lock(object):
    def __init__(self, key, timeout=30):
        os.makedirs(SHARED_DIR, exist_ok=True)
        lock_name = ".%s.lock" % hashlib.sha256(key.encode("utf-8")).hexdigest()
        self.path = os.path.join(SHARED_DIR, lock_name)
        self.timeout = timeout
        self.handle = None

    def __enter__(self):
        ensure_private_dir(SHARED_DIR)
        descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        self.handle = os.fdopen(descriptor, "a+")
        deadline = time.time() + self.timeout
        while True:
            try:
                fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (IOError, OSError):
                if time.time() >= deadline:
                    self.handle.close()
                    fail("timed out waiting for lock")
                time.sleep(0.05 + random.random() * 0.05)

    def __exit__(self, *unused):
        try:
            fcntl.flock(self.handle, fcntl.LOCK_UN)
        finally:
            self.handle.close()


def tracked_files(registry_text=None):
    paths = list(GLOBAL_FILES)
    raw = registry_text
    if raw is None:
        raw = read_text(data_path("_registry.json"))
    if not raw:
        return paths
    try:
        registry = json.loads(raw)
    except (TypeError, ValueError):
        return paths
    for slug, project in registry.get("projects", {}).items():
        if not isinstance(project, dict):
            continue
        base = project.get("path", slug)
        for field in PROJECT_FILE_FIELDS:
            value = project.get(field)
            if value:
                candidate = value if "/" in value else os.path.join(base, value)
                candidate = safe_relative(candidate)
                if candidate not in paths:
                    paths.append(candidate)
    return paths


def unit_mode(name):
    base = os.path.basename(name)
    if base == "_memory.md":
        return "line"
    if base == "_session-log.md":
        return "block"
    if base in ("_registry.json", "_dashboard.md"):
        return "whole"
    return "line"


def units(name, text):
    if text is None:
        return []
    mode = unit_mode(name)
    if mode == "whole":
        return [("whole", text)]
    if mode == "line":
        return [(line.strip(), line.strip()) for line in text.splitlines() if line.strip()]
    result = []
    key = None
    block = []
    for line in text.splitlines():
        if line.startswith("## "):
            if key is not None:
                result.append((key, "\n".join(block).rstrip()))
            key = line.strip()
            block = [line]
        elif key is not None:
            block.append(line)
    if key is not None:
        result.append((key, "\n".join(block).rstrip()))
    return result


def session_path(session_id):
    return os.path.join(SNAPSHOT_DIR, safe_relative(session_id))


def resolve_session(value):
    value = value or os.environ.get("COSW_SESSION")
    if value:
        return safe_relative(value)
    if not os.path.isdir(SNAPSHOT_DIR):
        fail("no snapshot exists, run snapshot first")
    candidates = sorted(
        item for item in os.listdir(SNAPSHOT_DIR)
        if os.path.isdir(os.path.join(SNAPSHOT_DIR, item))
    )
    if not candidates:
        fail("no snapshot exists, run snapshot first")
    return candidates[-1]


def journal_file(session_id):
    return os.path.join(session_path(session_id), "journal.json")


def load_journal(session_id):
    raw = read_text(journal_file(session_id))
    return json.loads(raw) if raw else {"writes": []}


def add_journal(session_id, name, kind, key, text, expected_present=True):
    path = journal_file(session_id)
    with Lock("journal:%s" % session_id):
        journal = load_journal(session_id)
        journal["writes"].append({
            "file": name,
            "kind": kind,
            "key": key,
            "text": text,
            "expected_present": expected_present,
            "at": datetime.now().isoformat(timespec="seconds"),
        })
        atomic_write(path, json.dumps(journal, indent=2) + "\n")


def base_file(session_id, name):
    return os.path.join(session_path(session_id), "base", safe_relative(name))


def existed_at_snapshot(session_id, name):
    metadata = json.loads(read_text(os.path.join(session_path(session_id), "meta.json")) or "{}")
    return metadata.get("files", {}).get(name, {}).get("exists", False)


def snapshot(args):
    session_id = args.session or "%s-%04d" % (
        datetime.now().strftime("%Y%m%dT%H%M%S"), random.randint(0, 9999)
    )
    root = session_path(session_id)
    ensure_private_dir(DATA_DIR)
    ensure_private_dir(SHARED_DIR)
    ensure_private_dir(SNAPSHOT_DIR)
    ensure_private_dir(root)
    ensure_private_dir(os.path.join(root, "base"))
    metadata = {
        "session": session_id,
        "created": datetime.now().isoformat(timespec="seconds"),
        "data_dir": DATA_DIR,
        "files": {},
    }
    registry_name = "_registry.json"
    with Lock(registry_name):
        registry_source = data_path(registry_name)
        registry_exists = os.path.exists(registry_source)
        registry_text = read_text(registry_source) if registry_exists else None
    names = tracked_files(registry_text)
    for name in names:
        if name == registry_name:
            text = registry_text
        else:
            with Lock(name):
                source = data_path(name)
                exists = os.path.exists(source)
                text = read_text(source) if exists else None
        metadata["files"][name] = {"exists": text is not None}
        if text is None:
            continue
        destination = base_file(session_id, name)
        ensure_private_dir(os.path.dirname(destination))
        atomic_write(destination, text)
        metadata["files"][name].update({
            "sha256": digest(text),
            "units": len(units(name, text)),
        })
    atomic_write(os.path.join(root, "meta.json"), json.dumps(metadata, indent=2) + "\n")
    atomic_write(journal_file(session_id), json.dumps({"writes": []}, indent=2) + "\n")
    print(session_id)
    if not args.quiet:
        sys.stderr.write("snapshot saved\nexport COSW_SESSION=%s\n" % session_id)
    return 0


def append_memory(args):
    session_id = resolve_session(args.session)
    name = "_memory.md"
    target = data_path(name)
    entry = args.entry.strip()
    if not entry:
        fail("memory entry is empty")
    with Lock(name):
        if existed_at_snapshot(session_id, name) and not os.path.exists(target):
            print("REFUSED: %s was deleted after the snapshot" % name)
            return 1
        current = read_text(target) or ""
        if entry in set(key for key, unused in units(name, current)):
            print("SKIP duplicate: %s" % entry[:80])
            return 0
        ensure_private_dir(os.path.dirname(target))
        descriptor = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            if current and not current.endswith("\n"):
                handle.write("\n")
            handle.write(entry + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    add_journal(session_id, name, "append", entry, entry)
    print("OK %s" % entry[:80])
    return 0


def insert_log(args):
    session_id = resolve_session(args.session)
    name = safe_relative(args.target)
    target = data_path(name)
    block = read_text(args.block)
    if block is None:
        fail("block file not found: %s" % args.block)
    block = block.strip("\n")
    if not block.startswith("## "):
        fail("block must start with a level two heading")
    block_lines = block.splitlines()
    if "[session:" not in block_lines[0]:
        block_lines[0] = "%s [session:%s]" % (block_lines[0].rstrip(), session_id)
    block = "\n".join(block_lines)
    key = block_lines[0].strip()
    with Lock(name):
        if existed_at_snapshot(session_id, name) and not os.path.exists(target):
            print("REFUSED: %s was deleted after the snapshot" % name)
            return 1
        current = read_text(target) or ""
        if key in set(item for item, unused in units(name, current)):
            print("SKIP entry already present: %s" % key[:80])
            return 0
        lines = current.splitlines()
        position = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
        merged = lines[:position] + block.splitlines() + [""] + lines[position:]
        atomic_write(target, "\n".join(merged).rstrip() + "\n")
    add_journal(session_id, name, "insert", key, block)
    print("OK %s" % key[:80])
    return 0


def build_report(session_id):
    metadata = json.loads(read_text(os.path.join(session_path(session_id), "meta.json")) or "{}")
    journal = load_journal(session_id)
    mine = {}
    for write in journal.get("writes", []):
        mine.setdefault(write["file"], {})[write["key"]] = {
            "text": write.get("text"),
            "present": write.get("expected_present", True),
        }
    names = set(metadata.get("files", {}).keys())
    names.update(write["file"] for write in journal.get("writes", []))
    report = {"session": session_id, "clean": True, "files": {}}
    for name in sorted(names):
        base_exists = metadata.get("files", {}).get(name, {}).get("exists", False)
        before_text = read_text(base_file(session_id, name)) if base_exists else None
        with Lock(name):
            target = data_path(name)
            disk_exists = os.path.exists(target)
            after_text = read_text(target) if disk_exists else None
        before = dict(units(name, before_text))
        after = dict(units(name, after_text))
        owned = mine.get(name, {})
        deleted = [key for key in before if key not in after]
        added = [key for key in after if key not in before]
        changed_all = [key for key in before if key in after and before[key] != after[key]]
        present_as_written = [
            key for key, expected in owned.items()
            if expected["present"] and key in after and after[key] == expected["text"]
        ]
        deleted_as_written = [
            key for key, expected in owned.items()
            if not expected["present"] and key not in after
        ]
        entry = {
            "unit": unit_mode(name),
            "lost_from_base": [key for key in deleted if key not in deleted_as_written],
            "changed_in_place": [key for key in changed_all if key not in present_as_written],
            "added_by_others": [key for key in added if key not in present_as_written],
            "added_by_me": [key for key in added if key in present_as_written],
            "edited_by_me": [key for key in changed_all if key in present_as_written],
            "deleted_by_me": deleted_as_written,
            "my_writes_missing": [
                key for key, expected in owned.items()
                if (expected["present"] and after.get(key) != expected["text"])
                or (not expected["present"] and key in after)
            ],
            "file_created": not base_exists and disk_exists,
            "file_deleted": base_exists and not disk_exists,
        }
        if any(entry[field] for field in (
            "lost_from_base", "changed_in_place", "added_by_others", "my_writes_missing"
        )) or entry["file_created"] or entry["file_deleted"]:
            report["clean"] = False
        report["files"][name] = entry
    return report


def check(args):
    session_id = resolve_session(args.session)
    report = build_report(session_id)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print("cosw check session=%s" % session_id)
    review = False
    activity = False
    for name, entry in report["files"].items():
        if not any(entry[field] for field in entry if isinstance(entry[field], list)) and not entry["file_created"] and not entry["file_deleted"]:
            continue
        activity = True
        print("\n%s" % name)
        if entry["file_created"]:
            print("  CREATED + file did not exist at snapshot")
        if entry["file_deleted"]:
            print("  DELETED - entire file")
            review = True
        for key in entry["added_by_me"]:
            print("  mine, present + %s" % key[:100])
        for key in entry["edited_by_me"]:
            print("  mine, edited ~ %s" % key[:100])
        for key in entry["deleted_by_me"]:
            print("  mine, deleted - %s" % key[:100])
        for key in entry["added_by_others"]:
            print("  THEIRS + %s" % key[:100])
        for key in entry["changed_in_place"]:
            print("  EDITED ~ %s" % key[:100])
            review = True
        for key in entry["lost_from_base"]:
            print("  DELETED - %s" % key[:100])
            review = True
        for key in entry["my_writes_missing"]:
            print("  MY WRITE LOST - %s" % key[:100])
            review = True
    if review:
        print("\nACTION REQUIRED: review edits or deletions before closing.")
    elif activity:
        print("\nNo content was lost. Concurrent additions remain present.")
    else:
        print("clean. no concurrent modification detected.")
    return 0


def restore(args):
    session_id = resolve_session(args.session)
    pending = []
    for write in load_journal(session_id).get("writes", []):
        current = dict(units(write["file"], read_text(data_path(write["file"]))))
        expected_present = write.get("expected_present", True)
        if ((expected_present and current.get(write["key"]) != write.get("text"))
                or (not expected_present and write["key"] in current)):
            pending.append((write, write["key"] in current))
    if not pending:
        print("nothing to restore")
        return 0
    if args.dry_run:
        for write, unused in pending:
            print("WOULD RESTORE %s %s" % (write["file"], write["key"][:80]))
        return 0
    for write, key_still_exists in pending:
        if write["kind"] in ("edit", "delete") or key_still_exists:
            print("CANNOT AUTO RESTORE %s %s" % (write["file"], write["key"][:80]))
            print("Review the changed content and reapply it with merge or write.")
            return 1
        target = data_path(write["file"])
        with Lock(write["file"]):
            current = read_text(target) or ""
            current_units = dict(units(write["file"], current))
            if write["key"] in current_units:
                print("CANNOT AUTO RESTORE %s %s" % (write["file"], write["key"][:80]))
                return 1
            if write["kind"] == "append":
                suffix = "" if not current or current.endswith("\n") else "\n"
                atomic_write(target, current + suffix + write["text"].strip() + "\n")
            else:
                lines = current.splitlines()
                position = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
                merged = lines[:position] + write["text"].splitlines() + [""] + lines[position:]
                atomic_write(target, "\n".join(merged).rstrip() + "\n")
        print("RESTORED %s %s" % (write["file"], write["key"][:80]))
    return 0


def merge(args):
    session_id = resolve_session(args.session)
    name = safe_relative(args.target)
    base = base_file(session_id, name)
    target = data_path(name)
    if not os.path.exists(base):
        fail("no snapshot base for %s" % name)
    mine = read_text(args.mine)
    if mine is None:
        fail("proposed file not found: %s" % args.mine)
    with Lock(name):
        target = data_path(name)
        if not os.path.exists(target):
            print("REFUSED: %s was deleted after the snapshot" % name)
            return 1
        disk_before = read_text(target)
        descriptor, output = tempfile.mkstemp(prefix=".cosw-merge-")
        os.close(descriptor)
        atomic_write(output, mine)
        process = subprocess.run(
            ["git", "merge-file", "-L", "mine", "-L", "base", "-L", "on-disk", output, base, target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        merged = read_text(output)
        os.unlink(output)
        if process.returncode < 0:
            fail("git merge-file failed")
        if process.returncode > 0:
            conflict = target + ".conflict"
            conflict_metadata = conflict + ".json"
            expected_digest = digest(disk_before)
            atomic_write(conflict, merged)
            atomic_write(conflict_metadata, json.dumps({
                "session": session_id,
                "target": name,
                "expected_current_sha256": expected_digest,
                "generated": datetime.now().isoformat(timespec="seconds"),
            }, indent=2) + "\n")
            print("%d conflict(s), live file unchanged" % process.returncode)
            print(conflict)
            print("expected-current-sha256: %s" % expected_digest)
            print("metadata: %s" % conflict_metadata)
            return 1
        atomic_write(target, merged)
    old_units = dict(units(name, disk_before))
    new_units = dict(units(name, merged))
    for key, text in new_units.items():
        if key not in old_units or old_units[key] != text:
            add_journal(session_id, name, "edit", key, text)
    for key in old_units:
        if key not in new_units:
            add_journal(session_id, name, "delete", key, None, expected_present=False)
    print("MERGED %s" % name)
    return 0


def write_file(args):
    session_id = resolve_session(args.session)
    name = safe_relative(args.target)
    proposed = read_text(args.file)
    if proposed is None:
        fail("proposed file not found: %s" % args.file)
    if any(marker in proposed for marker in ("<<<<<<< ", ">>>>>>> ", "\n=======\n")):
        fail("refusing to write unresolved conflict markers")
    expected_digest = args.expected_current_sha256
    if args.force and not expected_digest:
        fail("--force requires --expected-current-sha256 from conflict generation")
    if expected_digest and (
            len(expected_digest) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in expected_digest)):
        fail("expected current digest must be a SHA-256 hex value")
    conflict_metadata_path = data_path(name) + ".conflict.json"
    if expected_digest:
        try:
            conflict_metadata = json.loads(read_text(conflict_metadata_path) or "{}")
        except ValueError:
            fail("conflict metadata is invalid, rerun merge")
        if (conflict_metadata.get("session") != session_id
                or conflict_metadata.get("target") != name
                or conflict_metadata.get("expected_current_sha256") != expected_digest.lower()):
            fail("digest token does not match conflict metadata, rerun merge")
    metadata = json.loads(read_text(os.path.join(session_path(session_id), "meta.json")) or "{}")
    base_exists = metadata.get("files", {}).get(name, {}).get("exists", False)
    before = read_text(base_file(session_id, name)) if base_exists else None
    target = data_path(name)
    with Lock(name):
        target = data_path(name)
        current_exists = os.path.exists(target)
        current = read_text(target) if current_exists else None
        existence_changed = base_exists != current_exists
        content_changed = base_exists and current_exists and digest(before) != digest(current)
        if expected_digest:
            if not current_exists or digest(current) != expected_digest.lower():
                print("REFUSED: %s changed after conflict generation" % name)
                print("Run merge again against the current file before resolving.")
                return 1
        elif existence_changed or content_changed:
            print("REFUSED: %s changed since snapshot" % name)
            return 1
        atomic_write(target, proposed)
        if expected_digest:
            for artifact in (target + ".conflict", conflict_metadata_path):
                if os.path.exists(artifact):
                    os.unlink(artifact)
    old_units = dict(units(name, current))
    new_units = dict(units(name, proposed))
    for key, text in new_units.items():
        if key not in old_units or old_units[key] != text:
            add_journal(session_id, name, "edit", key, text)
    for key in old_units:
        if key not in new_units:
            add_journal(session_id, name, "delete", key, None, expected_present=False)
    print("WROTE %s" % name)
    return 0


def diff_file(args):
    session_id = resolve_session(args.session)
    name = safe_relative(args.target)
    before = read_text(base_file(session_id, name)) or ""
    current = read_text(data_path(name)) or ""
    lines = list(difflib.unified_diff(
        before.splitlines(), current.splitlines(),
        fromfile="%s@snapshot" % name, tofile="%s@now" % name, lineterm=""
    ))
    print("\n".join(lines) if lines else "identical")
    return 0


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--session", help="session ID, then COSW_SESSION, then newest")
    commands = root.add_subparsers(dest="command", required=True)

    command = commands.add_parser("snapshot")
    command.add_argument("--quiet", action="store_true")
    command.set_defaults(action=snapshot)

    command = commands.add_parser("append-memory")
    command.add_argument("entry")
    command.set_defaults(action=append_memory)

    command = commands.add_parser("insert-log")
    command.add_argument("--target", default="_session-log.md")
    command.add_argument("--block", required=True)
    command.set_defaults(action=insert_log)

    command = commands.add_parser("check")
    command.add_argument("--json", action="store_true")
    command.set_defaults(action=check)

    command = commands.add_parser("restore")
    command.add_argument("--dry-run", action="store_true")
    command.set_defaults(action=restore)

    command = commands.add_parser("merge")
    command.add_argument("--target", required=True)
    command.add_argument("--mine", required=True)
    command.set_defaults(action=merge)

    command = commands.add_parser("write")
    command.add_argument("--target", required=True)
    command.add_argument("--file", required=True)
    command.add_argument("--force", action="store_true")
    command.add_argument("--expected-current-sha256")
    command.set_defaults(action=write_file)

    command = commands.add_parser("diff")
    command.add_argument("--target", required=True)
    command.set_defaults(action=diff_file)
    return root


def main():
    args = parser().parse_args()
    return args.action(args)


if __name__ == "__main__":
    sys.exit(main())
