#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import io
import json
import stat
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import pilot


def write_project(root: Path, name: str, lines: int, *, binary: bool = False) -> Path:
    project = root / name
    source = project / "src" / ("main.rs" if binary else "lib.rs")
    source.parent.mkdir(parents=True)
    source.write_text("".join(f"pub fn f{i}() {{}}\n" for i in range(lines)), encoding="utf-8")
    (project / "Cargo.toml").write_text(
        f'[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2021"\n',
        encoding="utf-8",
    )
    return project


def make_archive(path: Path, project: Path) -> str:
    with tarfile.open(path, "w:gz") as bundle:
        bundle.add(project, arcname=project.name)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PilotTests(unittest.TestCase):
    def test_directory_order_and_eligible_limit_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_project(root, "c", 2)
            write_project(root, "a", 1)
            write_project(root, "b", 2)
            result = pilot.run_pilot(root, limit=2, min_loc=2, work_dir=root / "work")
            self.assertEqual([item["id"] for item in result["projects"]], ["a", "b", "c"])
            self.assertEqual(result["projects"][0]["eligibility"], "ineligible")
            self.assertEqual(result["summary"]["eligible_projects"], 2)
            self.assertEqual(result["summary"]["examined_projects"], 3)

    def test_unknown_is_logged_before_later_eligible_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            good = write_project(root, "good", 1)
            listing = root / "crates.json"
            listing.write_text(
                json.dumps([{"name": "missing", "path": "absent"}, {"name": "good", "path": str(good)}]),
                encoding="utf-8",
            )
            result = pilot.run_pilot(listing, limit=1, min_loc=1, work_dir=root / "work")
            self.assertEqual([item["status"] for item in result["projects"]], ["unknown", "ok"])
            self.assertEqual(result["summary"]["unknown_projects"], 1)

    def test_raw_crates_io_rows_derive_url_and_dedupe_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            listing = Path(temporary) / "crates.json"
            listing.write_text(
                json.dumps(
                    {
                        "crates": [
                            {"name": "alpha", "max_stable_version": "1.2.3", "repository": "https://x/r.git"},
                            {"name": "duplicate", "max_stable_version": "2.0.0", "repository": "https://x/r"},
                            {"name": "beta", "max_stable_version": "3.0.0", "repository": "https://x/b"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            entries = pilot.load_entries(listing)
            self.assertEqual([entry["name"] for entry in entries], ["alpha", "beta"])
            self.assertEqual(
                entries[0]["url"], "https://static.crates.io/crates/alpha/alpha-1.2.3.crate"
            )

    def test_checksum_verified_local_archive_is_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(root, "packed", 3, binary=True)
            archive = root / "packed.crate"
            checksum = make_archive(archive, project)
            listing = root / "crates.json"
            listing.write_text(
                json.dumps([{"name": "packed", "archive": str(archive), "sha256": checksum}]),
                encoding="utf-8",
            )
            result = pilot.run_pilot(
                listing, limit=1, min_loc=3, require_bin=True, work_dir=root / "work"
            )
            item = result["projects"][0]
            self.assertEqual(item["status"], "ok")
            self.assertEqual(item["rust"], {"files": 1, "nonblank_loc": 3, "status": "ok"})
            self.assertEqual(item["materialized_source"]["sha256"], checksum)

    def test_file_url_download_uses_checksum_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(root, "downloaded", 1)
            archive = root / "downloaded.crate"
            checksum = make_archive(archive, project)
            listing = root / "crates.json"
            listing.write_text(
                json.dumps([{"name": "downloaded", "url": archive.as_uri(), "sha256": checksum}]),
                encoding="utf-8",
            )
            result = pilot.run_pilot(
                listing, limit=1, min_loc=1, fetch=True, work_dir=root / "work"
            )
            self.assertEqual(result["projects"][0]["eligibility"], "eligible")

    def test_archive_rejects_traversal_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            traversal = root / "traversal.tar"
            with tarfile.open(traversal, "w") as bundle:
                info = tarfile.TarInfo("../escape.rs")
                payload = b"fn escape() {}\n"
                info.size = len(payload)
                bundle.addfile(info, io.BytesIO(payload))
            with self.assertRaises(pilot.PilotError):
                pilot.safe_extract_archive(traversal, root / "out-traversal")
            self.assertFalse((root / "escape.rs").exists())

            linked = root / "linked.zip"
            with zipfile.ZipFile(linked, "w") as bundle:
                info = zipfile.ZipInfo("crate/link.rs")
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                bundle.writestr(info, "target.rs")
            with self.assertRaises(pilot.PilotError):
                pilot.safe_extract_archive(linked, root / "out-linked")

    def test_ingested_reassociation_and_external_source_scanner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(root, "scanme", 1)
            records = root / "reassociation.jsonl"
            records.write_text(
                '{"disposition":"candidate","class":"serial"}\n'
                '{"disposition":"unresolved","class":"nearby"}\n',
                encoding="utf-8",
            )
            scanner = root / "scanner.py"
            scanner.write_text(
                "import json, sys\n"
                "print(json.dumps({'signal': 'index-loop', 'root': bool(sys.argv[1])}))\n",
                encoding="utf-8",
            )
            listing = root / "crates.json"
            listing.write_text(
                json.dumps(
                    [{"name": "scanme", "path": str(project), "reassociation_jsonl": str(records)}]
                ),
                encoding="utf-8",
            )
            result = pilot.run_pilot(
                listing,
                limit=1,
                min_loc=1,
                work_dir=root / "work",
                source_signal_command=[sys.executable, str(scanner)],
            )
            item = result["projects"][0]
            self.assertEqual(item["reassociation"]["candidates"], 1)
            self.assertEqual(item["reassociation"]["unresolved"], 1)
            self.assertEqual(item["source_signals"]["record_count"], 1)
            self.assertEqual(result["summary"]["reassociation"]["candidate_projects"], 1)

    def test_bundled_source_report_is_flattened_to_actual_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(root, "signals", 1)
            (project / "src/lib.rs").write_text(
                "fn copy(src: &[u8], out: &mut [u8]) {\n"
                "    for i in 0..src.len() { out[i] = src[i]; }\n"
                "}\n",
                encoding="utf-8",
            )
            result = pilot.run_pilot(project, limit=1, min_loc=1, work_dir=root / "work")
            signals = result["projects"][0]["source_signals"]
            self.assertEqual(signals["candidate_count"], len(signals["records"]))
            self.assertEqual(signals["record_count"], len(signals["records"]))
            self.assertEqual(signals["report"]["schema"], "whitefoot.frequency-study.pilot-signals.v1")
            self.assertEqual(
                result["summary"]["source_signals"]["records"], len(signals["records"])
            )
            self.assertGreater(
                result["summary"]["source_signals"]["by_class"]["index_loop_bounds_candidate"],
                0,
            )

    def test_canonical_json_is_stable_and_sorted(self) -> None:
        self.assertEqual(pilot.canonical_json_bytes({"z": 1, "a": 2}), b'{"a":2,"z":1}\n')


if __name__ == "__main__":
    unittest.main()
