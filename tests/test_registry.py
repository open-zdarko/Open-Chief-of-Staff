import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPOSITORY = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR = REPOSITORY / "scripts" / "validate_registry.py"
SPEC = importlib.util.spec_from_file_location("registry_validator", VALIDATOR)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_registry():
    return {
        "$schema": "./_registry.schema.json",
        "schema_version": 1,
        "projects": {
            "example": {
                "display_name": "Example",
                "type": "project",
                "status": "active",
                "path": "example",
                "context_file": "context.md",
                "index_file": "index.md",
                "pending_file": "pending.md",
                "related": [],
                "sources": [],
            }
        },
    }


class RegistryValidatorTests(unittest.TestCase):
    def test_valid_registry_passes_library_and_cli(self):
        registry = valid_registry()
        self.assertEqual(MODULE.validate(registry), [])
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--registry", str(path)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_traversal_and_absolute_paths_are_rejected(self):
        for field, value in (
            ("path", "../outside"),
            ("context_file", "../../context.md"),
            ("index_file", "/tmp/index.md"),
            ("pending_file", "nested/../pending.md"),
        ):
            with self.subTest(field=field):
                registry = valid_registry()
                registry["projects"]["example"][field] = value
                errors = MODULE.validate(registry)
                self.assertTrue(any(field in error for error in errors), errors)

    def test_unsafe_slug_and_unknown_related_project_are_rejected(self):
        registry = valid_registry()
        registry["projects"]["../example"] = registry["projects"].pop("example")
        registry["projects"]["../example"]["related"] = ["missing"]
        errors = MODULE.validate(registry)
        self.assertTrue(any("safe project slug" in error for error in errors))
        self.assertTrue(any("unknown project" in error for error in errors))

    def test_project_files_cannot_point_into_another_project(self):
        registry = valid_registry()
        registry["projects"]["example"]["context_file"] = "other/context.md"
        errors = MODULE.validate(registry)
        self.assertTrue(any("beneath the project path" in error for error in errors), errors)

    def test_project_path_requires_safe_components(self):
        registry = valid_registry()
        registry["projects"]["example"]["path"] = "_shared"
        errors = MODULE.validate(registry)
        self.assertTrue(any("safe lowercase slugs" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
