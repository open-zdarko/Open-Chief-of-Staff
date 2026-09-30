---
description: Review attributed pending context for one project or all projects
agent: context-review
---

Review pending context for `$ARGUMENTS`. Accept one project name or `all`.
Resolve projects through `COS_DATA_DIR/_registry.json` and use each registry
entry's `pending_file`.

Before reading shared state, load `cos-safe-writes` and take a snapshot unless
the current session already has `COSW_SESSION`. Validate the registry with
`$COS_ROOT/tools/validate-registry.py` and stop on any error.

Present candidates one at a time with author, date range, provider, stable
source ID, source location, collector, summary, and confidence. Allow approval,
rejection, retained source inspection, or editing of the proposed update.

Merge only explicitly approved information into the matching project's
`context.md`. Preserve attribution and uncertainty, deduplicate existing
content, and ask separately before updating structured fields. Never use one
project's candidate in another project. Never treat `drafts/` as a source.

Do not edit context or pending files directly. Build each proposed full file in
a private temporary location and apply it with `cosw.py merge --target ...
--mine ...`. On conflict, leave the live file unchanged and ask the user to
resolve it. Apply a reviewed clean resolution with `cosw.py write --target ...
--file ... --force --expected-current-sha256 {token-from-merge}`. If the token
no longer matches, rerun merge and review the new conflict. Never bypass the
digest check. Run `cosw.py check` before completing review.

At completion, report approved, rejected, and remaining counts and suggest
`/project {name}` to view curated state.

<user-request>
$ARGUMENTS
</user-request>
