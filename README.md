# Open Chief of Staff

A personal AI chief of staff that helps you manage projects, prepare for meetings, draft documents, and track action items. It remembers context across sessions, learns your preferences over time, and adapts to whatever you are working on: professional, personal, or entrepreneurial.

Built on [OpenCode](https://opencode.ai). Works with Claude, GPT, or any LLM provider that OpenCode supports.

## What It Does

**Persistent project context.** Each project has a living context file that tracks goals, status, key people, action items, signals, and history. The agent reads this at the start of every session so you never have to re-explain where things stand.

**Cross session memory.** The agent remembers your preferences, corrections, and working patterns across all projects. If you tell it once that you prefer tables over prose, it remembers.

**Session logging.** Every conversation is summarized and logged. You can ask "what did we discuss about X last month?" and get an answer.

**Document management.** Store reference documents (contracts, meeting notes, research) in a project's `docs/` folder. The agent indexes them and can answer questions from them on demand. Agent generated output goes to `drafts/` and is never confused with source material.

**Self improving skills.** When the agent works through a complex process, it offers to save the approach as a reusable skill. Next time, it follows the proven path.

**Meeting prep, document drafting, strategic advice.** Ask it to prepare for a meeting, draft a proposal, summarize a situation, or think through a decision. It uses everything it knows about the project.

## Requirements

1. [OpenCode](https://opencode.ai) installed
2. An API key for an LLM (Claude, GPT, etc.), configured in OpenCode

That's it. No servers, no databases, no accounts beyond your LLM provider.

## Install

```bash
git clone https://github.com/YOUR_USERNAME/Open-Chief-of-Staff.git
cd Open-Chief-of-Staff
./setup.sh
```

The setup script will:
1. Ask where you want your projects directory (default: `~/chief-of-staff/projects/`)
2. Create the directory with starter files
3. Install the agents, commands, and skills into your OpenCode config
4. Not overwrite anything that already exists

## Getting Started

After setup, open any terminal and run:

```bash
opencode
```

### Fill in your identity

Edit `~/chief-of-staff/projects/_identity.md` to tell the agent who you are. This helps it adapt its tone and advice to your context. You can be as brief or detailed as you want.

### Create your first project

```
/project my-startup
```

If the project does not exist, the agent will create it from the template and ask you to describe it.

### Work on an existing project

```
/project my-startup
```

The agent loads the project context, checks for pending items, and tells you where things stand. Then ask it anything:

- "Help me prepare for tomorrow's meeting with the investors"
- "Draft an email to the contractor about the timeline slip"
- "What are the open action items?"
- "What did we discuss last week?"

### Review pending context

If you have added files to a project's `docs/` folder or have pending review items:

```
/review-context my-startup
```

## Project Structure

Your projects directory looks like this after setup:

```
~/chief-of-staff/projects/
  _identity.md          # Who you are (read by the agent every session)
  _memory.md            # Agent's learned preferences (auto-managed)
  _session-log.md       # Log of every session (auto-managed)
  _registry.json        # Master list of all projects
  _template.md          # Template for new projects
  _multi-track-template.md  # Template for multi-track projects

  my-startup/
    context.md          # Living project state
    docs/               # Your reference documents (contracts, notes, etc.)
    drafts/             # Agent generated output (briefs, proposals, etc.)
    skills/             # Learned approaches specific to this project
```

## Project Types

### Standard Project

A single focus area: a client engagement, a business idea, a home renovation, a job search, a personal goal. One context file tracking everything.

### Multi-Track Project

An umbrella with multiple sub-tracks: a consulting practice with several clients, a startup with multiple product lines, an investment portfolio. Includes a playbook and a track overview table. Sub-tracks can graduate to standalone projects.

## How Memory Works

The agent maintains two layers of memory:

1. **Project context** (`context.md`): Everything about a specific project. Goals, status, people, history, signals. Updated during sessions when you approve changes.

2. **Global memory** (`_memory.md`): Your preferences and patterns across all projects. The agent writes here proactively when it learns something useful. Maximum 50 entries, automatically consolidated.

Both persist across sessions. When you start a conversation, the agent reads both to pick up where you left off.

## Skills

Skills are reusable approaches the agent has learned. Two kinds:

- **Project skills** (stored in `{project}/skills/`): Loaded only when that project is active. Example: "How to prep for the quarterly investor call."
- **Global skills** (stored in `~/.config/opencode/skills/`): Available across all projects. Example: "How to structure an executive brief."

The agent offers to create skills after complex workflows. You can also ask it to save an approach at any time.

### Included Skills

- **docx**: Create, edit, and analyze Word documents. Handles formatting, tables, tracked changes, and more.
- **pm**: Project management expertise for planning, task breakdown, and sprint management.

## Customization

### Writing style

Edit `~/.config/opencode/AGENTS.md` to change the agent's writing style across all interactions. The default keeps things brief and direct. Add your own rules.

### Templates

Edit the templates in your projects directory to match your workflow. Add sections, remove sections, change the structure. The agent adapts to whatever sections exist in a project's context.md.

### MCP Integrations

OpenCode supports MCP (Model Context Protocol) servers for connecting to external services. You can add integrations in `~/.config/opencode/opencode.json`. Examples:

- Google Calendar for meeting awareness
- Slack or Teams for message context
- A CRM for customer data
- GitHub or GitLab for code project tracking

These are optional. The Chief of Staff works with just local files.

## Privacy

All data stays on your machine. Project files are plain markdown and JSON in a directory you control. Nothing is sent anywhere except to your chosen LLM provider (through OpenCode) during active conversations.

The `.gitignore` in this repo excludes the projects directory so you never accidentally commit personal data if you fork the repo.

## License

MIT. See [LICENSE](LICENSE).
