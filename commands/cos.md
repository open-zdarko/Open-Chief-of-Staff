---
description: Start General mode with cross project awareness
agent: chief-of-staff
---

Activate General mode. Resolve all data beneath `COS_DATA_DIR`, falling back to
`~/chief-of-staff/projects` only when the variable is absent.

Load the safe writes skill and take a session snapshot first. Then read
`_identity.md`, `_memory.md`, `_registry.json`, `_dashboard.md`, and
`_session-log.md` in that order.

Validate `_registry.json` with `$COS_ROOT/tools/validate-registry.py` before
using project paths. Stop and report validation errors.

Treat `_dashboard.md` as a read only generated summary. Report its generation
date and warn when it is more than three days old. Present a concise overview
of active projects, time sensitive items, pending reviews, and useful next
actions. Attribute every dashboard claim to its project and source date.

Do not load full project files or write project context until the user enters
focused Project mode. If `$ARGUMENTS` names a project, offer to load it with the
Project mode workflow after the General overview.

<user-request>
$ARGUMENTS
</user-request>
