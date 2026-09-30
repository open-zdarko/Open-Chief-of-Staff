---
name: cos-safe-writes
description: Prevents lost updates in shared Chief of Staff project data. Use at session start, for writes to shared state, and before session close.
---

# Safe Writes To Shared Project Files

Multiple OpenCode sessions can read the same file and later overwrite each
other. This skill combines locked surgical writes with start and end
verification. It uses only Python 3.9 standard library features.

## Environment

`COS_DATA_DIR` is the project data directory. If absent, the tool uses
`~/chief-of-staff/projects`.

```bash
COSW=${COS_ROOT:-$HOME/chief-of-staff}/tools/cosw.py
export COSW_SESSION=$(python3 "$COSW" snapshot --quiet)
```

When installed as a global skill, `COSW` may instead be
`~/.config/opencode/skills/cos-safe-writes/cosw.py`.

## Required Procedure

1. Take one snapshot before reading shared state.
2. Append memory with `python3 "$COSW" append-memory "YYYY-MM-DD: entry"`.
3. Put a complete session log block in a temporary file and run `python3 "$COSW" insert-log --block /path/to/block.md`.
4. For registry or other whole file updates, prepare a new file and run `python3 "$COSW" merge --target _registry.json --mine /path/to/new.json`.
5. Run `python3 "$COSW" check` before closing the session.

The tool tracks global shared files plus project context, index, and pending
paths declared in the registry. It rejects absolute targets and path traversal.
It also rejects symlinked targets and detects whole file creation or deletion
after the snapshot, including empty files.

## Check Results

* `THEIRS`: another session added content. Keep it.
* `EDITED` or `DELETED`: another session changed existing content. Show the user and ask what to retain.
* `MY WRITE LOST`: run `restore`, then check again.
* `CREATED` or whole file `DELETED`: another process changed file existence. Review it before writing.
* `clean`: no concurrent modification needs attention.

Never restore another session's deletion automatically. `restore` reapplies
only writes journaled by the current session.

## Conflict Workflow

`merge` performs a three way merge against the session snapshot. On conflict,
it leaves the live file untouched, writes an annotated `.conflict` file, and
writes adjacent JSON metadata containing `expected_current_sha256`. It also
prints the digest token. After user review, apply a clean resolution with:

```bash
python3 "$COSW" write --target _registry.json \
  --file /path/to/resolved.json \
  --force \
  --expected-current-sha256 DIGEST_FROM_CONFLICT
```

`write` rejects unresolved conflict markers. `--force` is rejected unless the
conflict generation digest is supplied and matches metadata for the same target
and session. The live file must still match that digest, so a resolution cannot
overwrite changes made after the conflict was generated. If it does not match,
rerun `merge` and resolve the new result. Successful resolution removes the
conflict artifacts.

## Useful Commands

```bash
python3 "$COSW" check --json
python3 "$COSW" diff --target _memory.md
python3 "$COSW" restore --dry-run
```

Snapshots and journals live in `$COS_DATA_DIR/_shared/snapshots/`. They contain
copies of managed state and must remain private.

Session log headings receive `[session:COSW_SESSION]` automatically when the
caller omits it. This prevents two sessions in the same minute from being
deduplicated as one entry.
