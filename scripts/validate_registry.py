#!/usr/bin/env python3
"""Validate an Open Chief of Staff registry without third party packages."""

import argparse
import json
import os
import re
import sys


SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PROJECT_TYPES = {"project", "multi-track"}
PROJECT_KEYS = {
    "display_name", "type", "status", "path", "context_file",
    "index_file", "pending_file", "related", "sources",
}
SOURCE_KEYS = {"id", "provider", "locator", "label", "enabled", "notes"}


def relative_path(value, label, errors):
    if not isinstance(value, str) or not value:
        errors.append("%s must be a nonempty relative path" % label)
        return None
    if "\\" in value or os.path.isabs(value):
        errors.append("%s must use a relative POSIX path" % label)
        return None
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        errors.append("%s contains an empty, dot, or traversal component" % label)
        return None
    return value


def validate(data):
    errors = []
    if not isinstance(data, dict):
        return ["registry root must be an object"]
    unknown_root = set(data) - {"$schema", "schema_version", "projects"}
    if unknown_root:
        errors.append("registry has unknown keys: %s" % ", ".join(sorted(unknown_root)))
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    projects = data.get("projects")
    if not isinstance(projects, dict):
        errors.append("projects must be an object")
        return errors

    resolved_files = {}
    for slug, project in projects.items():
        prefix = "projects.%s" % slug
        if not isinstance(slug, str) or not SLUG.fullmatch(slug):
            errors.append("%s is not a safe project slug" % prefix)
        if not isinstance(project, dict):
            errors.append("%s must be an object" % prefix)
            continue
        missing = PROJECT_KEYS - set(project)
        unknown = set(project) - PROJECT_KEYS
        if missing:
            errors.append("%s is missing: %s" % (prefix, ", ".join(sorted(missing))))
        if unknown:
            errors.append("%s has unknown keys: %s" % (prefix, ", ".join(sorted(unknown))))
        for field in ("display_name", "status"):
            if not isinstance(project.get(field), str) or not project.get(field):
                errors.append("%s.%s must be a nonempty string" % (prefix, field))
        if project.get("type") not in PROJECT_TYPES:
            errors.append("%s.type must be project or multi-track" % prefix)

        project_path = relative_path(project.get("path"), "%s.path" % prefix, errors)
        if project_path and any(not SLUG.fullmatch(part) for part in project_path.split("/")):
            errors.append("%s.path components must use safe lowercase slugs" % prefix)
        for field in ("context_file", "index_file", "pending_file"):
            value = relative_path(project.get(field), "%s.%s" % (prefix, field), errors)
            if value and project_path:
                resolved = value if "/" in value else "%s/%s" % (project_path, value)
                if resolved != project_path and not resolved.startswith(project_path + "/"):
                    errors.append("%s.%s must resolve beneath the project path" % (prefix, field))
                    continue
                collision_key = resolved.casefold()
                owner = resolved_files.get(collision_key)
                if owner:
                    errors.append("%s.%s duplicates path used by %s" % (prefix, field, owner))
                else:
                    resolved_files[collision_key] = "%s.%s" % (prefix, field)

        related = project.get("related")
        if not isinstance(related, list) or any(not isinstance(item, str) for item in related):
            errors.append("%s.related must be an array of project slugs" % prefix)
        elif len(related) != len(set(related)):
            errors.append("%s.related contains duplicates" % prefix)

        sources = project.get("sources")
        if not isinstance(sources, list):
            errors.append("%s.sources must be an array" % prefix)
            continue
        source_ids = set()
        for index, source in enumerate(sources):
            source_prefix = "%s.sources[%d]" % (prefix, index)
            if not isinstance(source, dict):
                errors.append("%s must be an object" % source_prefix)
                continue
            missing_source = {"id", "provider", "locator", "label", "enabled"} - set(source)
            unknown_source = set(source) - SOURCE_KEYS
            if missing_source:
                errors.append("%s is missing: %s" % (source_prefix, ", ".join(sorted(missing_source))))
            if unknown_source:
                errors.append("%s has unknown keys: %s" % (source_prefix, ", ".join(sorted(unknown_source))))
            for field in ("id", "provider", "locator", "label"):
                if not isinstance(source.get(field), str) or not source.get(field):
                    errors.append("%s.%s must be a nonempty string" % (source_prefix, field))
            if not isinstance(source.get("enabled"), bool):
                errors.append("%s.enabled must be a boolean" % source_prefix)
            source_id = source.get("id")
            if source_id in source_ids:
                errors.append("%s.id is duplicated within the project" % source_prefix)
            source_ids.add(source_id)

    for slug, project in projects.items():
        if isinstance(project, dict) and isinstance(project.get("related"), list):
            for related in project["related"]:
                if related not in projects:
                    errors.append("projects.%s.related references unknown project %s" % (slug, related))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.environ.get("COS_DATA_DIR", "~/chief-of-staff/projects"))
    parser.add_argument("--registry")
    args = parser.parse_args()
    data_dir = os.path.realpath(os.path.expanduser(args.data_dir))
    registry = args.registry or os.path.join(data_dir, "_registry.json")
    try:
        with open(registry, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        sys.stderr.write("registry validation failed: %s\n" % error)
        return 1
    errors = validate(data)
    if errors:
        for error in errors:
            sys.stderr.write("registry validation failed: %s\n" % error)
        return 1
    print("registry valid: %s" % registry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
