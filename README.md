# Open Chief of Staff

A local, persistent Chief of Staff harness for
[OpenCode](https://opencode.ai). It supports cross project planning, focused
project work, source aware context review, safe concurrent sessions, and
recovery of interrupted OpenCode sessions.

The repository contains generic templates and tools. It contains no populated
project data, provider credentials, or organization specific integrations.

## Requirements

1. OpenCode
2. Python 3.9 or newer
3. Git, used locally by the safe writer for three way merges
4. An LLM provider configured in OpenCode

## Supported Platforms

The harness supports macOS and Linux. The safe writer requires POSIX advisory
file locking through Python's `fcntl` module. Native Windows is not supported.
Windows users can run the harness inside WSL on a Linux filesystem.

## Install

```bash
git clone https://github.com/open-zdarko/Open-Chief-of-Staff.git
cd Open-Chief-of-Staff
./setup.sh
```

Defaults:

```text
COS_ROOT=~/chief-of-staff
COS_DATA_DIR=~/chief-of-staff/projects
```

Use other locations without editing repository files:

```bash
COS_ROOT="$HOME/my-cos" \
COS_DATA_DIR="$HOME/private/project-data" \
COS_BIN_DIR="$HOME/.local/bin" \
./setup.sh
```

Setup creates missing data templates but never overwrites files in
`COS_DATA_DIR`. New private data directories use mode `700`; new data files use
mode `600`.

Setup records checksums for installed harness files beneath
`${XDG_CONFIG_HOME:-~/.config}/open-chief-of-staff/managed/`. It updates a file
only when the current checksum matches the version it previously installed.
Unknown or locally modified files are preserved and setup exits with an error.
To deliberately adopt and replace one, rerun with
`COS_REPLACE_UNMANAGED=1`; setup backs it up beneath the same configuration
directory before replacement. Repeated setup with unchanged files creates no
new backup.

Existing `opencode.json`, `opencode.jsonc`, `AGENTS.md`, and optional bundled
skills are preserved. Restart OpenCode after installation so agent, command,
and skill changes take effect.

## Launcher

Ensure `COS_BIN_DIR` is on `PATH`, then use:

```bash
cos
cos project my-project
cos my-project
```

`cos` starts OpenCode at `COS_ROOT` and injects `/cos`. A project name injects
`/project <name>`. Setup stores installation discovery settings at the fixed
location `${XDG_CONFIG_HOME:-~/.config}/open-chief-of-staff/env`, so the
launcher can rediscover a custom `COS_ROOT` without the variable already being
set. `COS_CONFIG_HOME` or `COS_CONFIG_FILE` can select another configuration
location. Exported `COS_ROOT` and `COS_DATA_DIR` values take precedence.

The slash commands also work in an existing OpenCode session:

```text
/cos
/project my-project
/review-context my-project
```

## Modes

### General Mode

`/cos` loads global memory, the project registry, the generated dashboard, and
session history. It supports prioritization, comparisons, and session search.
The dashboard is read only and advisory. General mode never writes project
context.

### Project Mode

`/project <name>` loads General context plus one project's curated context,
activity index, pending candidates, and project skills. The project's
`context.md` is the source of truth. Index, pending, dashboard, and related
project data remain supplementary until the user approves them.

## Data Layout

```text
$COS_DATA_DIR/
  _identity.md
  _memory.md
  _session-log.md
  _registry.json
  _registry.schema.json
  _dashboard.md
  _template.md
  _multi-track-template.md
  _index-template.md
  _pending-template.md
  _shared/
    snapshots/

  my-project/
    context.md
    index.md
    pending.md
    docs/
    drafts/
    skills/
```

`docs/` contains user controlled source material. `drafts/` contains generated
output and is never scanned or treated as factual source material.

## Registry

The registry is described by `_registry.schema.json` and enforced by the
dependency free validator at `$COS_ROOT/tools/validate-registry.py`. Commands
run the validator before following project paths. It rejects absolute paths,
dot components, traversal, unsafe slugs, duplicate managed paths, and invalid
relationships. Each project records relative data paths, relationships, and
optional provider agnostic source descriptors:

```json
{
  "display_name": "Website launch",
  "type": "project",
  "status": "active",
  "path": "website-launch",
  "context_file": "context.md",
  "index_file": "index.md",
  "pending_file": "pending.md",
  "related": [],
  "sources": [
    {
      "id": "planning-notes",
      "provider": "document-system",
      "locator": "stable-page-id",
      "label": "Planning notes",
      "enabled": true
    }
  ]
}
```

Do not put tokens, passwords, raw messages, or document bodies in the registry.

## Attribution And Context Safety

Every external or manually discovered index item records who said it, when it
occurred, where it came from, and which provider supplied it. Unknown fields
remain unknown. The harness does not infer them.

Optional sync tools may write attributed entries to `index.md` and candidates
to `pending.md`. Discovery does not update curated context. `/review-context`
presents each candidate and requires explicit approval before a concise,
attributed update enters `context.md`.

Context review snapshots shared state before reading it. Approved context and
pending status changes are applied with three way merge. A conflict leaves the
live file unchanged until the user reviews a clean resolution.

This prevents three common forms of context pollution:

1. Generated drafts being recycled as source material
2. One project's information leaking into another project
3. An author's opinion being presented as a verified fact

No external sync provider is included. A custom provider only needs to emit the
generic index and pending formats. Keep provider code, credentials, and
organization specific endpoints outside this public harness.

## Concurrent Sessions

The `cos-safe-writes` skill prevents cooperating sessions from overwriting
shared files. It takes a start snapshot, uses file locks for surgical writes,
journals each session's changes, and checks for lost updates at close.
It detects concurrent file creation and deletion, refuses symlinked paths, and
compares journaled expected content with current content so a later external
overwrite is not attributed to the original writer. Session log entries carry
second precision and a safe writer session ID.

Conflicted merges emit a digest of the live file used to generate the conflict.
A forced resolution write requires that digest and refuses if the file changed
again. The merge must be rerun before resolving newer content.

Manual use:

```bash
export COSW_SESSION=$(python3 "$COS_ROOT/tools/cosw.py" snapshot --quiet)
python3 "$COS_ROOT/tools/cosw.py" append-memory "2026-09-30: Example preference"
python3 "$COS_ROOT/tools/cosw.py" check
```

Snapshots contain private project state and stay beneath
`$COS_DATA_DIR/_shared/`.

## Session Recovery

The `session-recovery` skill finds sessions through `opencode db`, exports one
to a private temporary directory, and renders its recoverable messages. It uses
`COS_ROOT` and `COS_DATA_DIR`; it contains no hardcoded development path.

Visible messages, tool calls, patches, and compaction markers can be recovered.
Hidden assistant reasoning cannot. Recovered conversations are read to the end
before any state update because later turns may reverse earlier positions.

## Optional Integrations

OpenCode can connect to calendars, chat systems, document stores, issue
trackers, and other services through user configured tools or MCP servers. This
repository does not install an integration or send data to an endpoint.

Treat every integration as an untrusted discovery source until the user reviews
its output. Use stable source IDs, retain author and event timestamps, and keep
credentials in the provider's supported secret store rather than project files.

## Privacy

Project data is separate from this repository and should never be committed.
OpenCode sends active conversation context to the LLM provider selected by the
user. Optional tools may send data to their configured services. Local storage
does not mean model requests remain local.

Read [PRIVACY.md](PRIVACY.md) before adding real project data or external
integrations.

## Validation

```bash
bash -n setup.sh
python3 -m py_compile skills/cos-safe-writes/cosw.py skills/session-recovery/render.py
python3 scripts/validate_registry.py --registry templates/_registry.json
python3 -m unittest discover -s tests -p 'test_*.py'
bash tests/test_setup.sh
```

## License

MIT. See [LICENSE](LICENSE).
