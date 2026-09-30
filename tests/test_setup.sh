#!/bin/bash

set -euo pipefail

REPOSITORY="$(cd "$(dirname "$0")/.." && pwd)"
TEMPORARY="$(mktemp -d "${TMPDIR:-/tmp}/open-cos-test.XXXXXX")"
trap 'rm -rf "$TEMPORARY"' EXIT

export HOME="$TEMPORARY/home"
export XDG_CONFIG_HOME="$TEMPORARY/xdg"
export COS_ROOT="$TEMPORARY/custom-root"
export COS_DATA_DIR="$TEMPORARY/private-data"
export COS_BIN_DIR="$TEMPORARY/bin"
export OPENCODE_CONFIG_DIR="$TEMPORARY/opencode-config"
mkdir -p "$HOME" "$COS_DATA_DIR" "$TEMPORARY/fake-bin" "$OPENCODE_CONFIG_DIR/agents"
chmod 777 "$COS_DATA_DIR"
test -x "$REPOSITORY/setup.sh"

printf '%s\n' '#!/bin/sh' 'printf "%s|%s|%s\n" "$*" "$COS_ROOT" "$COS_DATA_DIR" > "$HOME/opencode-args"' > "$TEMPORARY/fake-bin/opencode"
chmod +x "$TEMPORARY/fake-bin/opencode"
export PATH="$TEMPORARY/fake-bin:$PATH"

printf '%s\n' '{"$schema":"./_registry.schema.json","schema_version":1,"projects":{}}' > "$COS_DATA_DIR/_registry.json"
printf '%s\n' 'unrelated custom agent' > "$OPENCODE_CONFIG_DIR/agents/chief-of-staff.md"

if "$REPOSITORY/setup.sh" > "$TEMPORARY/refused.log" 2>&1; then
    printf '%s\n' "setup unexpectedly replaced an unmanaged file" >&2
    exit 1
fi
test "$(cat "$OPENCODE_CONFIG_DIR/agents/chief-of-staff.md")" = "unrelated custom agent"

COS_REPLACE_UNMANAGED=1 "$REPOSITORY/setup.sh" > "$TEMPORARY/first.log"

REGISTRY_AFTER_FIRST="$(cksum "$COS_DATA_DIR/_registry.json")"
BACKUPS_AFTER_FIRST="$(find "$XDG_CONFIG_HOME/open-chief-of-staff/backups" -type f | wc -l | tr -d ' ')"
test "$BACKUPS_AFTER_FIRST" -ge 1
test -x "$COS_BIN_DIR/cos"
test -x "$COS_ROOT/tools/cosw.py"
test -x "$COS_ROOT/tools/validate-registry.py"
test -f "$COS_DATA_DIR/_dashboard.md"
test -f "$XDG_CONFIG_HOME/open-chief-of-staff/env"

mode() {
    if stat -f '%Lp' "$1" >/dev/null 2>&1; then
        stat -f '%Lp' "$1"
    else
        stat -c '%a' "$1"
    fi
}

test "$(mode "$COS_DATA_DIR")" = "700"
test "$(mode "$COS_DATA_DIR/_dashboard.md")" = "600"
test "$(mode "$XDG_CONFIG_HOME/open-chief-of-staff/env")" = "600"

"$REPOSITORY/setup.sh" > "$TEMPORARY/second.log"

REGISTRY_AFTER_SECOND="$(cksum "$COS_DATA_DIR/_registry.json")"
BACKUPS_AFTER_SECOND="$(find "$XDG_CONFIG_HOME/open-chief-of-staff/backups" -type f | wc -l | tr -d ' ')"
test "$REGISTRY_AFTER_FIRST" = "$REGISTRY_AFTER_SECOND"
test "$BACKUPS_AFTER_FIRST" = "$BACKUPS_AFTER_SECOND"

printf '%s\n' 'local command customization' > "$OPENCODE_CONFIG_DIR/commands/cos.md"
if "$REPOSITORY/setup.sh" > "$TEMPORARY/modified-refused.log" 2>&1; then
    printf '%s\n' "setup unexpectedly replaced a modified managed file" >&2
    exit 1
fi
test "$(cat "$OPENCODE_CONFIG_DIR/commands/cos.md")" = "local command customization"

unset COS_ROOT COS_DATA_DIR
"$COS_BIN_DIR/cos" project alpha
IFS='|' read -r LAUNCH_ARGS DISCOVERED_ROOT DISCOVERED_DATA < "$HOME/opencode-args"
case "$LAUNCH_ARGS" in
    *"$TEMPORARY/custom-root"*"--agent chief-of-staff"*"--prompt /project alpha"*) ;;
    *)
        printf 'Unexpected launcher arguments: %s\n' "$LAUNCH_ARGS" >&2
        exit 1
        ;;
esac
test "$DISCOVERED_ROOT" = "$TEMPORARY/custom-root"
test "$DISCOVERED_DATA" = "$TEMPORARY/private-data"

COS_DATA_DIR="$TEMPORARY/override-data" "$COS_BIN_DIR/cos" general
IFS='|' read -r LAUNCH_ARGS DISCOVERED_ROOT DISCOVERED_DATA < "$HOME/opencode-args"
case "$LAUNCH_ARGS" in
    *"--prompt /cos"*) ;;
    *)
        printf 'Unexpected General mode arguments: %s\n' "$LAUNCH_ARGS" >&2
        exit 1
        ;;
esac
test "$DISCOVERED_DATA" = "$TEMPORARY/override-data"

printf '%s\n' "setup test passed"
