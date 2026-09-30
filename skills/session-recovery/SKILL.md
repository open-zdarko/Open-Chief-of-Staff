---
name: session-recovery
description: Recovers interrupted, lost, or compacted OpenCode sessions and reconciles them with Chief of Staff project state.
---

# Session Recovery

OpenCode stores sessions in its local database. This workflow exports a session,
renders the recoverable messages, and reconciles final conclusions with project
state. Assistant reasoning is not recoverable.

## Find A Session

Confirm the database is available:

```bash
opencode db path
```

List recent sessions using the configured workspace rather than a hardcoded
directory:

```bash
ROOT=${COS_ROOT:-$HOME/chief-of-staff}
opencode db --format json "SELECT id, title, agent, directory,
  datetime(time_created/1000,'unixepoch','localtime') AS created,
  datetime(time_updated/1000,'unixepoch','localtime') AS updated
  FROM session WHERE directory LIKE '%' || '$ROOT' || '%'
  ORDER BY time_updated DESC LIMIT 20"
```

If several sessions match, ask the user to choose based on title, directory,
and date.

## Export And Render

Use a private temporary directory and verify the JSON is not empty before
rendering:

```bash
RECOVERY_DIR=$(mktemp -d "${TMPDIR:-/tmp}/cos-recovery.XXXXXX")
opencode export SESSION_ID > "$RECOVERY_DIR/session.json"
test -s "$RECOVERY_DIR/session.json"
python3 "${COS_ROOT:-$HOME/chief-of-staff}/tools/render-session.py" \
  "$RECOVERY_DIR/session.json" > "$RECOVERY_DIR/session.md"
```

When installed as a global skill, the renderer may instead be
`~/.config/opencode/skills/session-recovery/render.py`.

The renderer includes user text, visible assistant text, tool calls, patches,
and compaction markers. It does not expose hidden reasoning.

## Reconcile

1. Read every user turn and the final portion of the transcript.
2. Read the full transcript before proposing any write. Later turns can reverse earlier positions.
3. Compare candidate facts with the current project's `context.md`.
4. Skip information already recorded consistently.
5. Ask the user before adding missing information or resolving conflicts.
6. Preserve source attribution. Transcript statements are not automatically verified facts.
7. Log the recovery using the original session date range and mark it as recovered retroactively.

Use the `cos-safe-writes` skill for global memory, session log, and registry
writes. Project context changes still require user approval.

## Private Backup

If the user requests a durable export, store the JSON beneath:

```text
$COS_DATA_DIR/_session-exports/
```

That directory contains conversation content. Keep it out of source control and
external sync unless the user deliberately chooses a trusted destination.

## Verification

Compare the rendered `Messages` count with the export. Confirm every user turn
appears. After reconciliation, verify session log ordering and run the safe
writer check.
