import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "codex_model_adapter.py"
SPEC = importlib.util.spec_from_file_location("default_floor_codex_model", ADAPTER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CodexModelBoundaryTests(unittest.TestCase):
    def test_extracts_single_source_message(self):
        stream = "\n".join(
            (
                '{"type":"thread.started","thread_id":"t"}',
                '{"type":"turn.started"}',
                '{"type":"item.completed","item":{"type":"agent_message","text":"fn x () {}"}}',
                '{"type":"turn.completed","usage":{}}',
            )
        )
        self.assertEqual(MODULE.extract_source(stream), "fn x () {}")

    def test_preserves_message_whitespace(self):
        stream = "\n".join(
            (
                '{"type":"thread.started","thread_id":"t"}',
                '{"type":"turn.started"}',
                '{"type":"item.completed","item":{"type":"agent_message","text":"  fn x () {}\\r\\n\\n"}}',
                '{"type":"turn.completed","usage":{}}',
            )
        )
        self.assertEqual(MODULE.extract_source(stream), "  fn x () {}\r\n\n")

    def test_rejects_tool_item(self):
        stream = "\n".join(
            (
                '{"type":"thread.started","thread_id":"t"}',
                '{"type":"turn.started"}',
                '{"type":"item.completed","item":{"type":"command_execution","command":"pwd"}}',
                '{"type":"turn.completed","usage":{}}',
            )
        )
        with self.assertRaises(MODULE.ModelBoundaryError):
            MODULE.extract_source(stream)

    def test_rejects_multiple_messages(self):
        stream = "\n".join(
            (
                '{"type":"thread.started","thread_id":"t"}',
                '{"type":"item.completed","item":{"type":"agent_message","text":"one"}}',
                '{"type":"item.completed","item":{"type":"agent_message","text":"two"}}',
                '{"type":"turn.completed","usage":{}}',
            )
        )
        with self.assertRaises(MODULE.ModelBoundaryError):
            MODULE.extract_source(stream)

    def test_rejects_message_after_completion(self):
        stream = "\n".join(
            (
                '{"type":"thread.started","thread_id":"t"}',
                '{"type":"turn.started"}',
                '{"type":"item.completed","item":{"type":"agent_message","text":"one"}}',
                '{"type":"turn.completed","usage":{}}',
                '{"type":"item.completed","item":{"type":"agent_message","text":"two"}}',
            )
        )
        with self.assertRaises(MODULE.ModelBoundaryError):
            MODULE.extract_source(stream)

    def test_rejects_out_of_order_stream(self):
        stream = "\n".join(
            (
                '{"type":"turn.started"}',
                '{"type":"thread.started","thread_id":"t"}',
                '{"type":"item.completed","item":{"type":"agent_message","text":"one"}}',
                '{"type":"turn.completed","usage":{}}',
            )
        )
        with self.assertRaises(MODULE.ModelBoundaryError):
            MODULE.extract_source(stream)


if __name__ == "__main__":
    unittest.main()
