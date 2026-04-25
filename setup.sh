#!/bin/bash

# Open Chief of Staff - Setup Script
# Creates the project directory structure and installs agent configuration.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCODE_CONFIG="$HOME/.config/opencode"

echo ""
echo "==================================="
echo "  Open Chief of Staff - Setup"
echo "==================================="
echo ""

# Step 1: Check for OpenCode
if ! command -v opencode &> /dev/null; then
    echo "OpenCode is not installed."
    echo ""
    echo "Install it first:"
    echo "  curl -fsSL https://opencode.ai/install | bash"
    echo ""
    echo "Then run this setup script again."
    exit 1
fi

echo "OpenCode found: $(which opencode)"
echo ""

# Step 2: Choose projects directory
DEFAULT_DIR="$HOME/chief-of-staff/projects"
echo "Where should your projects live?"
echo "  Default: $DEFAULT_DIR"
echo ""
read -p "Projects directory [$DEFAULT_DIR]: " PROJECTS_DIR
PROJECTS_DIR="${PROJECTS_DIR:-$DEFAULT_DIR}"

# Expand ~ if present
PROJECTS_DIR="${PROJECTS_DIR/#\~/$HOME}"

echo ""
echo "Using: $PROJECTS_DIR"
echo ""

# Step 3: Create projects directory
if [ -d "$PROJECTS_DIR" ]; then
    echo "Directory already exists. Existing files will not be overwritten."
else
    mkdir -p "$PROJECTS_DIR"
    echo "Created projects directory."
fi

# Step 4: Copy templates (only if they do not already exist)
copy_if_missing() {
    local src="$1"
    local dest="$2"
    if [ ! -f "$dest" ]; then
        cp "$src" "$dest"
        echo "  Created: $(basename "$dest")"
    else
        echo "  Exists:  $(basename "$dest") (skipped)"
    fi
}

echo ""
echo "Setting up project files..."
copy_if_missing "$SCRIPT_DIR/templates/_registry.json" "$PROJECTS_DIR/_registry.json"
copy_if_missing "$SCRIPT_DIR/templates/_memory.md" "$PROJECTS_DIR/_memory.md"
copy_if_missing "$SCRIPT_DIR/templates/_session-log.md" "$PROJECTS_DIR/_session-log.md"
copy_if_missing "$SCRIPT_DIR/templates/_identity.md" "$PROJECTS_DIR/_identity.md"
copy_if_missing "$SCRIPT_DIR/templates/_template.md" "$PROJECTS_DIR/_template.md"
copy_if_missing "$SCRIPT_DIR/templates/_multi-track-template.md" "$PROJECTS_DIR/_multi-track-template.md"

# Step 5: Install OpenCode agents
echo ""
echo "Installing agents..."
mkdir -p "$OPENCODE_CONFIG/agents"

# Update the agent prompt with the correct projects directory
sed "s|~/chief-of-staff/projects/|$PROJECTS_DIR/|g" "$SCRIPT_DIR/agents/chief-of-staff.md" > "$OPENCODE_CONFIG/agents/chief-of-staff.md"
echo "  Installed: chief-of-staff agent"

cp "$SCRIPT_DIR/agents/context-review.md" "$OPENCODE_CONFIG/agents/context-review.md"
echo "  Installed: context-review agent"

# Step 6: Install commands
echo ""
echo "Installing commands..."
mkdir -p "$OPENCODE_CONFIG/commands"

cp "$SCRIPT_DIR/commands/project.md" "$OPENCODE_CONFIG/commands/project.md"
echo "  Installed: /project command"

cp "$SCRIPT_DIR/commands/review-context.md" "$OPENCODE_CONFIG/commands/review-context.md"
echo "  Installed: /review-context command"

# Step 7: Install skills
echo ""
echo "Installing skills..."
mkdir -p "$OPENCODE_CONFIG/skills"

if [ ! -d "$OPENCODE_CONFIG/skills/docx" ]; then
    cp -R "$SCRIPT_DIR/skills/docx" "$OPENCODE_CONFIG/skills/docx"
    echo "  Installed: docx skill"
else
    echo "  Exists:    docx skill (skipped)"
fi

if [ ! -d "$OPENCODE_CONFIG/skills/pm" ]; then
    cp -R "$SCRIPT_DIR/skills/pm" "$OPENCODE_CONFIG/skills/pm"
    echo "  Installed: pm skill"
else
    echo "  Exists:    pm skill (skipped)"
fi

# Step 8: Install config (only if no config exists)
echo ""
if [ ! -f "$OPENCODE_CONFIG/opencode.json" ]; then
    cp "$SCRIPT_DIR/config/opencode.json.example" "$OPENCODE_CONFIG/opencode.json"
    echo "Installed opencode.json config."
else
    echo "opencode.json already exists (not overwritten)."
    echo "  See config/opencode.json.example for recommended settings."
fi

# Step 9: Install writing rules (only if no AGENTS.md exists)
if [ ! -f "$OPENCODE_CONFIG/AGENTS.md" ]; then
    cp "$SCRIPT_DIR/config/AGENTS.md.example" "$OPENCODE_CONFIG/AGENTS.md"
    echo "Installed AGENTS.md writing rules."
else
    echo "AGENTS.md already exists (not overwritten)."
fi

# Step 10: Prompt to fill in identity
echo ""
echo "==================================="
echo "  Setup Complete"
echo "==================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Edit your identity file to tell the Chief of Staff who you are:"
echo "     $PROJECTS_DIR/_identity.md"
echo ""
echo "  2. Open a terminal in any directory and start OpenCode:"
echo "     opencode"
echo ""
echo "  3. Create your first project:"
echo "     /project my-first-project"
echo ""
echo "  4. Or just start talking. The Chief of Staff will help you get set up."
echo ""
echo "Your projects live in: $PROJECTS_DIR"
echo ""
