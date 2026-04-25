---
description: Review and approve pending context items for a project
---

Use the `context-review` subagent to review pending content for the specified project.

## Workflow

### Step 1: Parse target

Parse `$ARGUMENTS` to determine the target:
- If a specific project name, review that project only
- If "all", review all projects with pending items

### Step 2: Invoke context-review

The context-review agent will:
1. Read `{project-slug}/pending.md`
2. Present each item with summary and key signals
3. Ask for approval: Yes / No / Show full content / Edit before adding
4. Merge approved items into `context.md` under Context History
5. Update pending.md status markers

### Step 3: Summary

After review is complete, show what was added and suggest `/project {name}` to see the updated context.

<user-request>
$ARGUMENTS
</user-request>
