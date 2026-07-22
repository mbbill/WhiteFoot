import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
GENERATE = ROOT / "generate.py"
MODEL = TESTS / "mock_model.py"
EVALUATOR = TESTS / "mock_evaluator.py"
CODEX_ADAPTER = ROOT / "codex_model_adapter.py"
MOCK_CODEX = TESTS / "mock_codex_cli.py"


class DefaultFloorTests(unittest.TestCase):
    def invoke(
        self,
        root: Path,
        model_mode: str,
        evaluator_mode: str,
        budget: int,
        run_name: str = "run",
        state_name: str = "model-state.json",
    ):
        prompt = root / "prompt.txt"
        if not prompt.exists():
            prompt.write_text("Implement the frozen target contract.\n", encoding="utf-8")
        state = root / f"{run_name}-{state_name}"
        run_dir = root / run_name
        model_argv = [sys.executable, str(MODEL), model_mode, str(state)]
        evaluator_argv = [sys.executable, str(EVALUATOR), evaluator_mode]
        command = [
            sys.executable,
            str(GENERATE),
            "--run-dir",
            str(run_dir),
            "--prompt-file",
            str(prompt),
            "--model-argv-json",
            json.dumps(model_argv),
            "--evaluator-argv-json",
            json.dumps(evaluator_argv),
            "--repair-budget",
            str(budget),
            "--source-name",
            "source.xl",
        ]
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        return completed, run_dir, state, command

    def assert_frozen(self, run_dir: Path, expected_source: bytes, expected_round: int, expected_rounds: int):
        frozen_source = run_dir / "frozen" / "source.xl"
        self.assertEqual(frozen_source.read_bytes(), expected_source)
        expected_hash = hashlib.sha256(expected_source).hexdigest()
        self.assertEqual(
            (run_dir / "frozen" / "source.sha256").read_text(encoding="ascii"),
            f"{expected_hash}  source.xl\n",
        )
        manifest = json.loads((run_dir / "frozen" / "trace-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "frozen")
        self.assertEqual(manifest["frozen_round"], expected_round)
        self.assertEqual(manifest["source"]["sha256"], expected_hash)
        config_bytes = (run_dir / "config.json").read_bytes()
        self.assertEqual(manifest["config"]["sha256"], hashlib.sha256(config_bytes).hexdigest())
        trace = (run_dir / "trace.jsonl").read_bytes()
        self.assertEqual(manifest["trace"]["sha256"], hashlib.sha256(trace).hexdigest())
        lines = [json.loads(line) for line in trace.decode("utf-8").splitlines()]
        self.assertEqual(len(lines), expected_rounds)
        self.assertEqual(len(manifest["trace"]["rounds"]), expected_rounds)
        for index, record in enumerate(lines):
            self.assertEqual(record["round"], index)
            for artifact in (
                "prompt",
                "raw",
                "source",
                "model_stderr",
                "model_process",
                "evaluator_raw",
                "evaluator_stderr",
                "evaluator_process",
                "evaluator",
            ):
                item = record["artifacts"][artifact]
                artifact_path = run_dir / item["path"]
                self.assertTrue(artifact_path.is_file())
                self.assertEqual(item["sha256"], hashlib.sha256(artifact_path.read_bytes()).hexdigest())

    def test_first_shot_freezes_and_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed, run_dir, state, _ = self.invoke(root, "first-shot", "normal", 3)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(state.read_text(encoding="utf-8"))["calls"], 1)
            self.assert_frozen(run_dir, b"GOOD first shot\n", expected_round=0, expected_rounds=1)
            self.assertFalse((run_dir / "rounds" / "001").exists())
            archived_prompt = (run_dir / "rounds" / "000" / "prompt.txt").read_bytes()
            self.assertTrue(archived_prompt.startswith(b"Implement the frozen target contract.\n\n\n"))
            config_text = (run_dir / "config.json").read_text(encoding="utf-8")
            self.assertNotIn(str(state), config_text)
            config = json.loads(config_text)
            self.assertNotIn("model_argv", config)
            self.assertEqual(len(config["model_invocation"]["argv_sha256"]), 64)

    def test_one_repair_then_freezes_and_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed, run_dir, state, _ = self.invoke(root, "repair", "normal", 3)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            state_value = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(state_value["calls"], 2)
            self.assertIn("BAD needs repair", state_value["last_prompt"])
            self.assertIn("MOCK_WRONG", state_value["last_prompt"])
            self.assert_frozen(run_dir, b"GOOD repaired\n", expected_round=1, expected_rounds=2)
            self.assertFalse((run_dir / "rounds" / "002").exists())

    def test_forbidden_performance_feedback_is_protocol_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, mode in enumerate(("forbidden-perf", "forbidden-wall-ns", "forbidden-perf-text")):
                completed, run_dir, _, _ = self.invoke(
                    root, "first-shot", mode, 0, run_name=f"run-{index}"
                )
                self.assertEqual(completed.returncode, 2)
                self.assertIn("forbidden benchmark/performance", completed.stderr)
                self.assertFalse((run_dir / "frozen").exists())
                trace = [json.loads(line) for line in (run_dir / "trace.jsonl").read_text().splitlines()]
                self.assertEqual(len(trace), 1)
                self.assertEqual(trace[0]["status"], "protocol_error")
                self.assertEqual(trace[0]["phase"], "evaluator_schema")

    def test_failed_model_invocation_is_recorded_in_jsonl(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed, run_dir, state, _ = self.invoke(root, "fail", "normal", 0)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(json.loads(state.read_text(encoding="utf-8"))["calls"], 1)
            trace = [json.loads(line) for line in (run_dir / "trace.jsonl").read_text().splitlines()]
            self.assertEqual(len(trace), 1)
            self.assertEqual(trace[0]["status"], "protocol_error")
            self.assertEqual(trace[0]["phase"], "model")
            self.assertIn("source", trace[0]["artifacts"])

    def test_existing_run_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first, run_dir, state, command = self.invoke(root, "first-shot", "normal", 0)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = (run_dir / "frozen" / "source.xl").read_bytes()
            calls_before = json.loads(state.read_text(encoding="utf-8"))["calls"]
            second = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            self.assertEqual(second.returncode, 2)
            self.assertIn("refusing to overwrite", second.stderr)
            self.assertEqual((run_dir / "frozen" / "source.xl").read_bytes(), before)
            self.assertEqual(json.loads(state.read_text(encoding="utf-8"))["calls"], calls_before)

    def test_codex_adapter_exposes_only_agent_message(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prompt = root / "prompt.txt"
            prompt.write_text("Implement the frozen target contract.", encoding="utf-8")
            mock_codex = root / "mock-codex"
            shutil.copyfile(MOCK_CODEX, mock_codex)
            mock_codex.chmod(0o755)
            run_dir = root / "codex-run"
            model_argv = [
                sys.executable,
                str(CODEX_ADAPTER),
                "--codex",
                str(mock_codex),
                "--model",
                "mock-model",
            ]
            evaluator_argv = [sys.executable, str(EVALUATOR), "normal"]
            command = [
                sys.executable,
                str(GENERATE),
                "--run-dir",
                str(run_dir),
                "--prompt-file",
                str(prompt),
                "--model-argv-json",
                json.dumps(model_argv),
                "--evaluator-argv-json",
                json.dumps(evaluator_argv),
                "--public-model-metadata-json",
                json.dumps({"surface": "codex-cli", "model": "mock-model"}),
                "--repair-budget",
                "0",
            ]
            completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                (run_dir / "frozen" / "source.xl").read_text(encoding="utf-8"),
                "GOOD codex final message\n",
            )
            raw = (run_dir / "rounds" / "000" / "model.raw.txt").read_text(encoding="utf-8")
            stderr = (run_dir / "rounds" / "000" / "model.stderr.txt").read_text(encoding="utf-8")
            self.assertNotIn("thread.started", raw)
            self.assertIn("thread.started", stderr)


if __name__ == "__main__":
    unittest.main()
