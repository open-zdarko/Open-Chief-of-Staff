# Agent Memory

<!-- 
This file is the agent's cross session memory. It persists learned preferences,
corrections, environment facts, and approaches that worked across all projects
and sessions. The agent reads this at session start and writes to it during
conversations when it learns something worth remembering.

Rules:
- Maximum 50 entries
- One entry per line, prefixed with the date it was learned
- When full, consolidate related entries before adding new ones
- Never store trivial, obvious, or session specific information
- Never store raw data dumps or large code blocks
-->
