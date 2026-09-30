---
description: Load focused Project mode on top of General context
agent: chief-of-staff
---

Activate focused Project mode for `$ARGUMENTS`. Resolve all paths beneath
`COS_DATA_DIR`, falling back to `~/chief-of-staff/projects` only when absent.

Take a safe writes snapshot if this session does not already have one. Load the
General foundation: identity, memory, registry, and read only dashboard. Match
the requested slug first, then an exact case insensitive `display_name`. Ask
the user if the match is ambiguous. Never guess.

Validate `_registry.json` with `$COS_ROOT/tools/validate-registry.py` before
using any project path. Stop and report validation errors rather than following
an invalid or traversing path.

Load the matched project's `context_file`, `index_file`, `pending_file`, and
project skills. For `multi-track`, also load `playbook.md` and
`tracks/_overview.md` when present. Note related projects without loading their
full context.

Present current status, open action items, key dates, pending review count, and
newer unvalidated index activity. Clearly label index and dashboard information
as supplementary. Include author, date, provider, and source location whenever
surfacing it.

Scan `docs/` only for files absent from the context reference table and offer
to index them. Never scan `drafts/`.

If the project is missing, offer to create it from the templates. Use the safe
writer merge workflow for the registry update.

<user-request>
$ARGUMENTS
</user-request>
