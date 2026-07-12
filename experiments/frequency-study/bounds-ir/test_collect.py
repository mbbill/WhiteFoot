#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import collect


def module(body: str, *, path: str = "/work/app/src/lib.rs") -> str:
    directory, filename = path.rsplit("/", 1)
    return f'''source_filename = "probe.rs"
define void @app() !dbg !10 {{
entry:
{body}
  ret void
}}
!10 = distinct !DISubprogram(name: "app", file: !12, line: 7)
!11 = !DILocation(line: 9, column: 4, scope: !10)
!12 = !DIFile(filename: "{filename}", directory: "{directory}")
'''


class BoundsIrTests(unittest.TestCase):
    def test_finds_first_party_call_and_location(self) -> None:
        result = collect.analyze_ir(
            module("  call void @_ZN4core9panicking18panic_bounds_check17h123E(i64 3, i64 2, ptr null), !dbg !11"),
            ir_file="app.ll",
            source_root=Path("/work/app"),
        )
        self.assertEqual(result["direct_panic_bounds_call_count"], 1)
        self.assertEqual(len(result["candidates"]), 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["classification"], collect.CLASSIFICATION)
        self.assertEqual(candidate["function"], "app")
        self.assertEqual(candidate["debug_location"]["path"], "src/lib.rs")
        self.assertEqual(candidate["debug_location"]["line"], 9)

    def test_finds_invoke_and_quoted_rust_symbol(self) -> None:
        ir = module(
            '  invoke void @"_RNvCs123_4core9panicking18panic_bounds_check"(i64 3, i64 2, ptr null) to label %ok unwind label %bad, !dbg !11\n'
            "ok:\n  br label %done\nbad:\n  br label %done\ndone:"
        )
        result = collect.analyze_ir(
            ir, ir_file="app.ll", source_root=Path("/work/app")
        )
        self.assertEqual(result["direct_panic_bounds_call_count"], 1)
        self.assertEqual(result["candidates"][0]["callsites"][0]["kind"], "invoke")

    def test_comment_and_string_decoys_do_not_count(self) -> None:
        ir = '''source_filename = "decoy.ll"
@text = private constant [39 x i8] c"call @panic_bounds_check(i64 1, i64 0)\\00"
define void @app() {
entry:
  ; call void @panic_bounds_check(i64 1, i64 0)
  call void @sink(ptr @text)
  ret void
}
declare void @sink(ptr)
'''
        result = collect.analyze_ir(
            ir, ir_file="decoy.ll", source_root=Path("/work/app")
        )
        self.assertEqual(result["direct_panic_bounds_call_count"], 0)
        self.assertEqual(result["candidates"], [])

    def test_dependency_location_is_not_first_party(self) -> None:
        ir = module(
            "  call void @panic_bounds_check(i64 3, i64 2, ptr null), !dbg !11",
            path="/cargo/registry/src/dependency.rs",
        )
        result = collect.analyze_ir(
            ir, ir_file="dep.ll", source_root=Path("/work/app")
        )
        self.assertEqual(result["candidates"], [])
        self.assertEqual(len(result["unattributed_hits"]), 1)
        self.assertFalse(
            result["unattributed_hits"][0]["debug_location"]["first_party"]
        )

    def test_function_debug_location_is_a_first_party_fallback(self) -> None:
        result = collect.analyze_ir(
            module("  call void @panic_bounds_check(i64 3, i64 2, ptr null)"),
            ir_file="app.ll",
            source_root=Path("/work/app"),
        )
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["debug_location"]["line"], 7)

    def test_empty_and_malformed_inputs_fail_closed(self) -> None:
        for ir in (
            "",
            "; only a comment\n",
            "not LLVM IR\n",
            "define void @broken() {\nentry:\n  ret void\n",
        ):
            with self.subTest(ir=ir), self.assertRaises(ValueError):
                collect.analyze_ir(
                    ir, ir_file="bad.ll", source_root=Path("/work/app")
                )

    def test_valid_zero_hit_module_is_not_an_error(self) -> None:
        result = collect.analyze_ir(
            'source_filename = "zero.ll"\ndeclare void @external()\n',
            ir_file="zero.ll",
            source_root=Path("/work/app"),
        )
        self.assertEqual(result["llvm_function_count"], 0)
        self.assertEqual(result["candidates"], [])

    def test_directory_report_is_sorted_and_malformed_member_aborts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            ir_dir = root / "ir"
            ir_dir.mkdir()
            (ir_dir / "b.ll").write_text(
                module("", path=f"{source}/b.rs"), encoding="utf-8"
            )
            (ir_dir / "a.ll").write_text(
                module("", path=f"{source}/a.rs"), encoding="utf-8"
            )
            report = collect.analyze_paths([str(ir_dir)], source_root=source)
            self.assertEqual(report["input_file_count"], 2)

            (ir_dir / "bad.ll").write_text("garbage\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                collect.analyze_paths([str(ir_dir)], source_root=source)

    def test_cli_writes_one_json_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            ir_file = root / "probe.ll"
            ir_file.write_text(
                module("", path=f"{source}/lib.rs"), encoding="utf-8"
            )
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = collect.main(
                    [str(ir_file), "--source-root", str(source)]
                )
            self.assertEqual(status, 0, stderr.getvalue())
            self.assertEqual(json.loads(stdout.getvalue())["input_file_count"], 1)
            self.assertEqual(stdout.getvalue().count("\n"), 1)


if __name__ == "__main__":
    unittest.main()
