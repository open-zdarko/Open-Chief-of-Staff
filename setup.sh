#!/bin/bash

# Install the public Chief of Staff harness without replacing user data.

set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCODE_CONFIG="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
COS_CONFIG_HOME="${COS_CONFIG_HOME:-${XDG_CONFIG_HOME:-$HOME/.config}/open-chief-of-staff}"
COS_ENV_FILE="$COS_CONFIG_HOME/env"
MANAGED_DIR="$COS_CONFIG_HOME/managed"
COS_ROOT="${COS_ROOT:-$HOME/chief-of-staff}"
COS_BIN_DIR="${COS_BIN_DIR:-$HOME/.local/bin}"
BACKUP_STAMP="$(date +%Y%m%dT%H%M%S)-$$"
BACKUP_ROOT="$COS_CONFIG_HOME/backups/$BACKUP_STAMP"
BACKUP_USED=0
REFUSALS=0

expand_home() {
    case "$1" in
        "~") printf '%s\n' "$HOME" ;;
        "~/"*) printf '%s/%s\n' "$HOME" "${1#~/}" ;;
        *) printf '%s\n' "$1" ;;
    esac
}

checksum() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | cut -d ' ' -f 1
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d ' ' -f 1
    else
        printf '%s\n' "A SHA-256 utility is required: shasum or sha256sum." >&2
        return 1
    fi
}

text_key() {
    if command -v shasum >/dev/null 2>&1; then
        printf '%s' "$1" | shasum -a 256 | cut -d ' ' -f 1
    else
        printf '%s' "$1" | sha256sum | cut -d ' ' -f 1
    fi
}

shell_quote() {
    local value="${1//\'/\'\\\'\'}"
    printf "'%s'" "$value"
}

private_dir() {
    local directory="$1"
    if [ -L "$directory" ]; then
        printf 'Refusing symlinked private directory: %s\n' "$directory" >&2
        exit 1
    fi
    if [ ! -d "$directory" ]; then
        mkdir -p "$directory"
    fi
    chmod 700 "$directory"
}

COS_ROOT="$(expand_home "$COS_ROOT")"
COS_BIN_DIR="$(expand_home "$COS_BIN_DIR")"
COS_CONFIG_HOME="$(expand_home "$COS_CONFIG_HOME")"

if ! command -v opencode >/dev/null 2>&1; then
    printf '%s\n' "OpenCode is not installed." >&2
    printf '%s\n' "Install it from https://opencode.ai and run setup again." >&2
    exit 1
fi

if [ -z "${COS_DATA_DIR:-}" ]; then
    DEFAULT_DATA_DIR="$COS_ROOT/projects"
    if [ -t 0 ]; then
        printf 'Project data directory [%s]: ' "$DEFAULT_DATA_DIR"
        read -r COS_DATA_DIR
    fi
    COS_DATA_DIR="${COS_DATA_DIR:-$DEFAULT_DATA_DIR}"
fi
COS_DATA_DIR="$(expand_home "$COS_DATA_DIR")"

private_dir "$COS_CONFIG_HOME"
private_dir "$MANAGED_DIR"
private_dir "$COS_ROOT"
private_dir "$COS_ROOT/tools"
private_dir "$COS_DATA_DIR"
private_dir "$COS_BIN_DIR"
mkdir -p "$OPENCODE_CONFIG/agents" "$OPENCODE_CONFIG/commands" "$OPENCODE_CONFIG/skills"

backup_file() {
    local destination="$1"
    local label="$2"
    local backup="$BACKUP_ROOT/$label"
    private_dir "$(dirname "$backup")"
    cp -p "$destination" "$backup"
    BACKUP_USED=1
    printf '  Backed up: %s\n' "$destination"
}

install_managed() {
    local source="$1"
    local destination="$2"
    local label="$3"
    local mode="$4"
    local key state recorded actual temporary
    key="$(text_key "$destination")"
    state="$MANAGED_DIR/$key.sha256"
    mkdir -p "$(dirname "$destination")"

    if [ -L "$state" ]; then
        printf '  Refused symlinked ownership record: %s\n' "$state" >&2
        return 1
    fi
    if [ -L "$destination" ]; then
        printf '  Refused symlink: %s\n' "$destination" >&2
        return 1
    fi
    if [ -f "$destination" ] && cmp -s "$source" "$destination"; then
        checksum "$destination" > "$state"
        chmod 600 "$state"
        printf '  Current:   %s\n' "$destination"
        return 0
    fi
    if [ -e "$destination" ]; then
        if [ ! -f "$destination" ]; then
            printf '  Refused non-file: %s\n' "$destination" >&2
            return 1
        fi
        actual="$(checksum "$destination")"
        recorded=""
        if [ -f "$state" ]; then
            recorded="$(tr -d '[:space:]' < "$state")"
        fi
        if [ "$recorded" != "$actual" ] && [ "${COS_REPLACE_UNMANAGED:-0}" != "1" ]; then
            printf '  Refused unmanaged or modified file: %s\n' "$destination" >&2
            printf '  Preserve it, move it, or rerun with COS_REPLACE_UNMANAGED=1 to back it up and replace it.\n' >&2
            return 1
        fi
        backup_file "$destination" "$label"
    fi

    temporary="$destination.cos-new.$$"
    cp "$source" "$temporary"
    chmod "$mode" "$temporary"
    mv "$temporary" "$destination"
    checksum "$destination" > "$state"
    chmod 600 "$state"
    printf '  Installed: %s\n' "$destination"
    return 0
}

install_harness() {
    if ! install_managed "$@"; then
        REFUSALS=$((REFUSALS + 1))
    fi
}

install_data_if_missing() {
    local source="$1"
    local destination="$2"
    if [ -L "$destination" ]; then
        printf 'Refusing symlinked data file: %s\n' "$destination" >&2
        exit 1
    fi
    if [ -e "$destination" ]; then
        printf '  Preserved: %s\n' "$destination"
        return
    fi
    cp "$source" "$destination"
    chmod 600 "$destination"
    printf '  Created:   %s\n' "$destination"
}

printf '%s\n' "Installing Chief of Staff harness files..."
install_harness "$SCRIPT_DIR/agents/chief-of-staff.md" "$OPENCODE_CONFIG/agents/chief-of-staff.md" "agents/chief-of-staff.md" 600
install_harness "$SCRIPT_DIR/agents/context-review.md" "$OPENCODE_CONFIG/agents/context-review.md" "agents/context-review.md" 600
install_harness "$SCRIPT_DIR/commands/cos.md" "$OPENCODE_CONFIG/commands/cos.md" "commands/cos.md" 600
install_harness "$SCRIPT_DIR/commands/project.md" "$OPENCODE_CONFIG/commands/project.md" "commands/project.md" 600
install_harness "$SCRIPT_DIR/commands/review-context.md" "$OPENCODE_CONFIG/commands/review-context.md" "commands/review-context.md" 600
install_harness "$SCRIPT_DIR/skills/cos-safe-writes/SKILL.md" "$OPENCODE_CONFIG/skills/cos-safe-writes/SKILL.md" "skills/cos-safe-writes/SKILL.md" 600
install_harness "$SCRIPT_DIR/skills/cos-safe-writes/cosw.py" "$OPENCODE_CONFIG/skills/cos-safe-writes/cosw.py" "skills/cos-safe-writes/cosw.py" 700
install_harness "$SCRIPT_DIR/skills/session-recovery/SKILL.md" "$OPENCODE_CONFIG/skills/session-recovery/SKILL.md" "skills/session-recovery/SKILL.md" 600
install_harness "$SCRIPT_DIR/skills/session-recovery/render.py" "$OPENCODE_CONFIG/skills/session-recovery/render.py" "skills/session-recovery/render.py" 700
install_harness "$SCRIPT_DIR/skills/cos-safe-writes/cosw.py" "$COS_ROOT/tools/cosw.py" "root-tools/cosw.py" 700
install_harness "$SCRIPT_DIR/skills/session-recovery/render.py" "$COS_ROOT/tools/render-session.py" "root-tools/render-session.py" 700
install_harness "$SCRIPT_DIR/scripts/validate_registry.py" "$COS_ROOT/tools/validate-registry.py" "root-tools/validate-registry.py" 700
install_harness "$SCRIPT_DIR/bin/cos" "$COS_BIN_DIR/cos" "bin/cos" 700

printf '%s\n' "Installing optional bundled skills..."
if [ ! -e "$OPENCODE_CONFIG/skills/docx" ]; then
    cp -R "$SCRIPT_DIR/skills/docx" "$OPENCODE_CONFIG/skills/docx"
    printf '  Installed: docx\n'
else
    printf '  Preserved: docx\n'
fi
if [ ! -e "$OPENCODE_CONFIG/skills/pm" ]; then
    cp -R "$SCRIPT_DIR/skills/pm" "$OPENCODE_CONFIG/skills/pm"
    printf '  Installed: pm\n'
else
    printf '  Preserved: pm\n'
fi

printf '%s\n' "Creating missing project data templates..."
install_data_if_missing "$SCRIPT_DIR/templates/_registry.json" "$COS_DATA_DIR/_registry.json"
install_data_if_missing "$SCRIPT_DIR/templates/_registry.schema.json" "$COS_DATA_DIR/_registry.schema.json"
install_data_if_missing "$SCRIPT_DIR/templates/_dashboard.md" "$COS_DATA_DIR/_dashboard.md"
install_data_if_missing "$SCRIPT_DIR/templates/_memory.md" "$COS_DATA_DIR/_memory.md"
install_data_if_missing "$SCRIPT_DIR/templates/_session-log.md" "$COS_DATA_DIR/_session-log.md"
install_data_if_missing "$SCRIPT_DIR/templates/_identity.md" "$COS_DATA_DIR/_identity.md"
install_data_if_missing "$SCRIPT_DIR/templates/_template.md" "$COS_DATA_DIR/_template.md"
install_data_if_missing "$SCRIPT_DIR/templates/_multi-track-template.md" "$COS_DATA_DIR/_multi-track-template.md"
install_data_if_missing "$SCRIPT_DIR/templates/_index.md" "$COS_DATA_DIR/_index-template.md"
install_data_if_missing "$SCRIPT_DIR/templates/_pending.md" "$COS_DATA_DIR/_pending-template.md"

ENV_SOURCE="$COS_CONFIG_HOME/.env-source.$$"
{
    printf 'COS_ROOT=%s\n' "$(shell_quote "$COS_ROOT")"
    printf 'COS_DATA_DIR=%s\n' "$(shell_quote "$COS_DATA_DIR")"
} > "$ENV_SOURCE"
chmod 600 "$ENV_SOURCE"
install_harness "$ENV_SOURCE" "$COS_ENV_FILE" "config/env" 600
rm -f "$ENV_SOURCE"

if [ ! -f "$OPENCODE_CONFIG/opencode.json" ] && [ ! -f "$OPENCODE_CONFIG/opencode.jsonc" ]; then
    cp "$SCRIPT_DIR/config/opencode.json.example" "$OPENCODE_CONFIG/opencode.json"
    chmod 600 "$OPENCODE_CONFIG/opencode.json"
    printf '  Created:   %s\n' "$OPENCODE_CONFIG/opencode.json"
else
    printf '%s\n' "  Preserved existing OpenCode configuration."
fi
if [ ! -f "$OPENCODE_CONFIG/AGENTS.md" ]; then
    cp "$SCRIPT_DIR/config/AGENTS.md.example" "$OPENCODE_CONFIG/AGENTS.md"
    chmod 600 "$OPENCODE_CONFIG/AGENTS.md"
    printf '  Created:   %s\n' "$OPENCODE_CONFIG/AGENTS.md"
else
    printf '%s\n' "  Preserved existing AGENTS.md."
fi

python3 "$SCRIPT_DIR/scripts/validate_registry.py" --data-dir "$COS_DATA_DIR"

if [ "$BACKUP_USED" -eq 1 ]; then
    printf 'Replaced harness files were backed up under %s\n' "$BACKUP_ROOT"
fi
if [ "$REFUSALS" -gt 0 ]; then
    printf '\nSetup stopped with %d unmanaged, modified, or unsafe harness file(s) preserved.\n' "$REFUSALS" >&2
    exit 1
fi

printf '\nSetup complete.\n'
printf 'COS_ROOT: %s\n' "$COS_ROOT"
printf 'COS_DATA_DIR: %s\n' "$COS_DATA_DIR"
printf 'Configuration: %s\n' "$COS_ENV_FILE"
printf 'Launcher: %s\n' "$COS_BIN_DIR/cos"
printf 'Restart OpenCode, then run: cos\n'
