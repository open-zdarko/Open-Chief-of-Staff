---
description: Load a project context for a working session
---

Switch to the `chief-of-staff` agent and load the specified project.

## Workflow

### Step 1: Identify the project

Parse `$ARGUMENTS` to determine which project to load. Match against project keys in `_registry.json` in the projects directory. If no match, search `display_name` fields. If still no match, list available projects and ask the user to pick one.

### Step 2: Load context

1. Read `_identity.md` to understand the user
2. Read `_memory.md` to load cross session memory
3. Read `_registry.json` for the matched project entry
4. Read `{project-slug}/context.md`
5. If `{project-slug}/skills/` exists and contains files, read them to load project specific approaches
6. If the project type is `multi-track`, also read `playbook.md` and `tracks/_overview.md` from the project directory
7. Check if `pending.md` exists with PENDING items

### Step 3: Surface state

Present a brief status:
- Project name and type
- Last updated and last session dates
- Open action items (count and top items)
- Top signals (risks, opportunities, things to watch)
- If pending items exist: "You have N items pending review. Review now or continue?"

### Step 4: Ready for work

The session is now active for this project. The user can ask questions, request meeting prep, draft documents, or do any other project work.

### Step 5: Index new files

After loading, scan the `docs/` subfolder of the project directory for any files not yet in the Reference Documents table of context.md. NEVER scan the `drafts/` folder. If new files are found in `docs/`, announce: "Found N new files in the docs folder that are not yet indexed. Want me to index them?"

<user-request>
$ARGUMENTS
</user-request>
