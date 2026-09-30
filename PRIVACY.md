# Privacy Guide

## Data Boundaries

Keep private project data beneath `COS_DATA_DIR`, outside this repository. The
setup script never replaces existing files there. Do not copy populated project
files into templates, examples, tests, issues, or pull requests.

The following locations can contain sensitive content:

* `$COS_DATA_DIR`
* `$COS_DATA_DIR/_shared/snapshots`
* `$COS_DATA_DIR/_session-exports`
* OpenCode's local session database
* Temporary recovery exports
* Setup backups of customized harness prompts

Apply filesystem permissions appropriate for the device and its backup system.
Delete temporary recovery directories when reconciliation is complete.
Setup creates private data directories with mode `700` and private data files
with mode `600`. It refuses symlinked data files and the runtime safe writer
refuses symlink components beneath `COS_DATA_DIR`.

Harness ownership records and the fixed launcher environment file live beneath
`${XDG_CONFIG_HOME:-~/.config}/open-chief-of-staff/`. The environment file
contains paths, not credentials, and is created with mode `600`.

## Network Disclosure

OpenCode sends prompts and selected context to the configured LLM provider.
External tools and MCP servers can send data to their own services. Review each
provider's retention, training, residency, and access policies before enabling
it.

This repository includes no external sync implementation, credentials, private
endpoints, or organization specific skills. Keep integration secrets in the
provider's supported environment or secret store. Never place them in the
registry, Markdown project files, launcher environment file, or source control.

## Source Minimization

Index files should contain lightweight references and neutral summaries rather
than full messages or documents. Pending files should retain only enough source
detail for informed review. Prefer a stable private locator over copied raw
content.

Every discovered claim should retain:

* Author or explicit unknown value
* Event date or explicit unknown value
* Provider
* Stable source ID
* Source location
* Confidence and validation state

Approval does not convert opinion into fact. Curated context should preserve
who made a claim and any uncertainty that affects its use.

## Publication Checklist

Before publishing a fork or sharing diagnostics:

1. Confirm `COS_DATA_DIR` is outside the repository.
2. Run `git status` and inspect every untracked file.
3. Search tracked files for names, email addresses, tokens, internal hostnames, and local absolute paths.
4. Do not attach session exports, snapshots, setup backups, or populated registry files.
5. Replace real source IDs and URLs with synthetic examples.

If private data enters Git history, removing the current file is insufficient.
Rotate exposed credentials and rewrite the affected history before publishing.
