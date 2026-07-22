import json
from pathlib import Path
import subprocess
import unittest


REPOSITORY = Path(__file__).resolve().parents[3]
MANIFEST = (
    REPOSITORY
    / "optimizer-language-research"
    / "implementation"
    / "phase5-resource-profile"
    / "frontend-observer"
    / "Cargo.toml"
)


class FrontendObserverTests(unittest.TestCase):
    def test_observer_dependencies_and_sources_never_read_archive(self) -> None:
        observer = MANIFEST.parent
        manifest = MANIFEST.read_text(encoding="utf-8")
        source = (observer / "src" / "main.rs").read_text(encoding="utf-8")
        self.assertNotIn("archive/", manifest)
        self.assertNotIn("archive/", source)
        self.assertEqual(manifest.count("path = \"../../../../compiler/crates/"), 3)

    def test_two_source_complete_unit_reports_dependent_topology_cross_check(self) -> None:
        command = (
            "cargo",
            "run",
            "--quiet",
            "--locked",
            "--offline",
            "--manifest-path",
            str(MANIFEST),
            "--",
            str(REPOSITORY / "conformance" / "cases" / "gram2-pos-items.wf"),
            str(REPOSITORY / "conformance" / "cases" / "const1-pos-array-size.wf"),
        )
        completed = subprocess.run(
            command,
            cwd=REPOSITORY,
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(completed.stdout)
        self.assertEqual(
            report,
            {
                "evidence_scope": "v0.9-dependent-topology-cross-check",
                "specification": "bdfb461d1901f610633c5cbcd2477d24df3c77ca90599b9580c8289e50b82b68",
                "sources": 2,
                "source_bytes": 457,
                "lexemes": 171,
                "tokens": 101,
                "classified_tokens": 101,
                "parsed_elements": 171,
                "production_nodes": 70,
                "terminals": 101,
                "projected_mixed_elements": 170,
            },
        )
        self.assertEqual(
            report["parsed_elements"],
            report["production_nodes"] + report["terminals"],
        )
        self.assertEqual(
            report["projected_mixed_elements"],
            report["production_nodes"] - 1 + report["terminals"],
        )


if __name__ == "__main__":
    unittest.main()
