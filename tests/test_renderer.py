import importlib.util
import pathlib
import unittest


REPOSITORY = pathlib.Path(__file__).resolve().parents[1]
RENDERER = REPOSITORY / "skills" / "session-recovery" / "render.py"
SPEC = importlib.util.spec_from_file_location("session_renderer", RENDERER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RendererTests(unittest.TestCase):
    def test_render_preserves_visible_content_and_compaction_marker(self):
        data = {
            "info": {
                "id": "ses_example",
                "title": "Example",
                "agent": "chief-of-staff",
                "model": {"id": "provider/model"},
                "directory": "/private/workspace",
                "time": {"created": 1_700_000_000_000, "updated": 1_700_000_060_000},
            },
            "messages": [
                {
                    "info": {"role": "user", "time": {"created": 1_700_000_000_000}},
                    "parts": [{"type": "text", "text": "Keep this decision."}],
                },
                {
                    "info": {"role": "assistant", "time": {"created": 1_700_000_010_000}},
                    "parts": [
                        {"type": "compaction", "auto": True, "overflow": False},
                        {"type": "text", "text": "Visible response."},
                    ],
                },
            ],
        }
        output = MODULE.render(data)
        self.assertIn("Keep this decision.", output)
        self.assertIn("Visible response.", output)
        self.assertIn("CONTEXT COMPACTED HERE", output)
        self.assertIn("Messages: 2", output)


if __name__ == "__main__":
    unittest.main()
