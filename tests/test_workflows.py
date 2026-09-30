import pathlib
import unittest


REPOSITORY = pathlib.Path(__file__).resolve().parents[1]


class WorkflowInstructionTests(unittest.TestCase):
    def test_context_review_requires_snapshot_validation_and_safe_updates(self):
        agent = (REPOSITORY / "agents" / "context-review.md").read_text(encoding="utf-8")
        command = (REPOSITORY / "commands" / "review-context.md").read_text(encoding="utf-8")
        combined = agent + command
        self.assertIn("take a snapshot", combined)
        self.assertIn("validate-registry.py", combined)
        self.assertIn("merge --target", combined)
        self.assertIn("write --target", combined)
        self.assertIn("--expected-current-sha256", combined)
        self.assertIn("cosw.py check", combined)
        self.assertIn("pending.md", combined)
        self.assertIn("context.md", combined)

    def test_session_log_format_has_seconds_and_session_identity(self):
        agent = (REPOSITORY / "agents" / "chief-of-staff.md").read_text(encoding="utf-8")
        self.assertIn("HH:MM:SS", agent)
        self.assertIn("[session:{COSW_SESSION}]", agent)

    def test_documentation_states_platform_support(self):
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
        self.assertIn("supports macOS and Linux", readme)
        self.assertIn("Native Windows is not supported", readme)


if __name__ == "__main__":
    unittest.main()
