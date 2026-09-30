#!/usr/bin/env python3
"""Render an OpenCode session export as readable Markdown."""

import argparse
import datetime
import json
import sys


def timestamp(milliseconds):
    if not milliseconds:
        return ""
    return datetime.datetime.fromtimestamp(milliseconds / 1000).strftime("%Y-%m-%d %H:%M")


def load_export(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data.get("info"), dict) or not isinstance(data.get("messages"), list):
        raise ValueError("input is not an OpenCode session export")
    return data


def render(data):
    info = data["info"]
    messages = data["messages"]
    model = info.get("model") or {}
    output = [
        "# %s\n" % info.get("title", "(untitled)"),
        "* Session ID: `%s`" % info.get("id", "?"),
        "* Agent: %s" % info.get("agent", "?"),
        "* Model: %s" % model.get("id", "?"),
        "* Directory: %s" % info.get("directory", "?"),
        "* Created: %s" % timestamp(info.get("time", {}).get("created")),
        "* Updated: %s" % timestamp(info.get("time", {}).get("updated")),
        "* Messages: %d\n\n---\n" % len(messages),
    ]

    for message in messages:
        message_info = message.get("info") or {}
        role = message_info.get("role", "?")
        heading = "User" if role == "user" else "Assistant"
        created = timestamp(message_info.get("time", {}).get("created"))
        output.append("\n## %s  _%s_\n" % (heading, created))
        for part in message.get("parts") or []:
            part_type = part.get("type")
            if part_type == "text" and part.get("text", "").strip():
                output.append(part["text"].rstrip() + "\n")
            elif part_type == "tool":
                state = part.get("state") or {}
                tool_input = state.get("input") or {}
                description = (
                    tool_input.get("command")
                    or tool_input.get("filePath")
                    or tool_input.get("pattern")
                    or tool_input.get("description")
                    or ""
                )
                if not isinstance(description, str):
                    description = json.dumps(description, sort_keys=True)
                if len(description) > 300:
                    description = description[:300] + " ...[truncated]"
                suffix = ": %s" % description if description else ""
                output.append("`[tool: %s]` %s%s\n" % (
                    part.get("tool", "?"), state.get("status", ""), suffix
                ))
            elif part_type == "compaction":
                output.append("\n> **CONTEXT COMPACTED HERE**  "
                              "(auto=%s, overflow=%s)\n" % (
                                  part.get("auto"), part.get("overflow")
                              ))
            elif part_type == "patch":
                files = part.get("files") or []
                names = ", ".join(str(item) for item in files)[:300]
                output.append("`[patch]` %d file(s): %s\n" % (len(files), names))
    return "\n".join(output) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", help="path to JSON from opencode export")
    args = parser.parse_args()
    try:
        sys.stdout.write(render(load_export(args.export)))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        sys.stderr.write("render-session: %s\n" % error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
