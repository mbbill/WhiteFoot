#!/usr/bin/env python3
"""Freeze or verify the raw-DEFLATE Silesia scoring corpus.

The preparation path is deliberately separate from measurement and model
generation.  It accepts exactly the pinned Silesia archive, verifies every
member before use, compresses each complete member with the pinned stock-zlib
public adapter, and requires both pinned public decoders to reproduce the
member at exact full capacity.

The default mode creates the ignored ``corpus/scoring`` tree and the tracked
``scoring-manifest.json`` once.  It refuses to replace either.  ``--check``
rebuilds the adapters in a temporary directory, regenerates every stream, and
requires byte identity with both the ignored artifacts and the canonical
manifest without modifying them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Sequence
import zipfile

import reference
import stock_zlib


HERE = Path(__file__).resolve().parent
DEFAULT_ARCHIVE = Path("/private/tmp/whitefoot-silesia.zip")
OUTPUT_ROOT = HERE / "corpus" / "scoring"
MANIFEST_PATH = HERE / "scoring-manifest.json"
LOCKED_CLANG = Path(
    "/Applications/Xcode.app/Contents/Developer/Toolchains/"
    "XcodeDefault.xctoolchain/usr/bin/clang"
)
MACOS_SDK = Path(
    "/Applications/Xcode.app/Contents/Developer/Platforms/"
    "MacOSX.platform/Developer/SDKs/MacOSX.sdk"
)
LOCKED_COMPILER_ARGV = (
    str(LOCKED_CLANG),
    "--no-default-config",
    "-isysroot",
    str(MACOS_SDK),
)

SCHEMA = "whitefoot.raw-deflate.scoring-corpus.v1"
SILESIA_PAGE = "https://sun.aei.polsl.pl/~sdeor/index.php?page=silesia"
SILESIA_ARCHIVE_URL = "http://sun.aei.polsl.pl/~sdeor/corpus/silesia.zip"
ARCHIVE_SIZE = 68_182_744
ARCHIVE_SHA256 = "0626e25f45c0ffb5dc801f13b7c82a3b75743ba07e3a71835a41e3d9f63c77af"
SOURCE_TOTAL = 211_938_580

# This tuple is an independent identity lock, not data learned from the zip
# while generating the manifest.
MEMBERS = (
    ("dickens", 10_192_446, "b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a"),
    ("mozilla", 51_220_480, "657fc3764b0c75ac9de9623125705831ebbfbe08fed248df73bc2dc66e2a963b"),
    ("mr", 9_970_564, "68637ed52e3e4860174ed2dc0840ac77d5f1a60abbcb13770d5754e3774d53e6"),
    ("nci", 33_553_445, "fc63a31770947b8c2062d3b19ca94c00485a232bb91b502021948fee983e1635"),
    ("ooffice", 6_152_192, "e7ee013880d34dd5208283d0d3d91b07f442e067454276095ded14f322a656eb"),
    ("osdb", 10_085_684, "60f027179302ca3ad87c58ac90b6be72ec23588aaa7a3b7fe8ecc0f11def3fa3"),
    ("reymont", 6_627_202, "0eac0114a3dfe6e2ee1f345a0f79d653cb26c3bc9f0ed79238af4933422b7578"),
    ("samba", 21_606_400, "93ba07bc44d8267789c1d911992f40b089ffa2140b4a160fac11ccae9a40e7b2"),
    ("sao", 7_251_944, "c2d0ea2cc59d4c21b7fe43a71499342a00cbe530a1d5548770e91ecd6214adcc"),
    ("webster", 41_458_703, "6a68f69b26daf09f9dd84f7470368553194a0b294fcfa80f1604efb11143a383"),
    ("xml", 5_345_280, "0e82e54e695c1938e4193448022543845b33020c8be6bf3bf3ead2224903e08c"),
    ("x-ray", 8_474_240, "7de9fce1405dc44ae5e6813ed21cd5751e761bd4265655a005d39b9685d1c9ad"),
)

LEVEL = 6
MEM_LEVEL = 8
WINDOW_BITS = -15
METHOD = "Z_DEFLATED"
STRATEGY = stock_zlib.Z_DEFAULT_STRATEGY


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_text(command: Sequence[str]) -> str:
    process = subprocess.run(
        list(command),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(f"command failed ({' '.join(command)}): {detail}")
    return process.stdout.strip()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def require_exact_file(path: Path, expected: bytes, description: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"missing {description}: {path}")
    if path.stat().st_size != len(expected):
        raise RuntimeError(
            f"{description} size drift: {path} has {path.stat().st_size}, "
            f"expected {len(expected)}"
        )
    with path.open("rb") as source:
        offset = 0
        while offset < len(expected):
            actual = source.read(min(1024 * 1024, len(expected) - offset))
            wanted = expected[offset : offset + len(actual)]
            if actual != wanted:
                raise RuntimeError(f"{description} byte drift at or after offset {offset}: {path}")
            if not actual:
                raise RuntimeError(f"unexpected end of {description}: {path}")
            offset += len(actual)
        if source.read(1):
            raise RuntimeError(f"unexpected trailing byte in {description}: {path}")


def write_new_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as destination:
        destination.write(data)


def verify_archive_identity(archive: Path) -> zipfile.ZipFile:
    if not archive.is_file():
        raise RuntimeError(f"missing Silesia archive: {archive}")
    actual_size = archive.stat().st_size
    if actual_size != ARCHIVE_SIZE:
        raise RuntimeError(
            f"Silesia archive size is {actual_size}, expected {ARCHIVE_SIZE}"
        )
    actual_hash = sha256_file(archive)
    if actual_hash != ARCHIVE_SHA256:
        raise RuntimeError(
            f"Silesia archive SHA-256 is {actual_hash}, expected {ARCHIVE_SHA256}"
        )

    corpus = zipfile.ZipFile(archive, mode="r")
    infos = corpus.infolist()
    expected_names = [name for name, _, _ in MEMBERS]
    actual_names = [info.filename for info in infos]
    if actual_names != expected_names:
        corpus.close()
        raise RuntimeError(
            "Silesia archive member order or membership drift: "
            f"got {actual_names}, expected {expected_names}"
        )
    for info, (name, size, _) in zip(infos, MEMBERS):
        if info.is_dir() or info.filename != name:
            corpus.close()
            raise RuntimeError(f"invalid Silesia member entry: {info.filename!r}")
        if info.flag_bits & 0x1:
            corpus.close()
            raise RuntimeError(f"encrypted Silesia member is forbidden: {name}")
        if info.file_size != size:
            corpus.close()
            raise RuntimeError(
                f"Silesia member {name} has size {info.file_size}, expected {size}"
            )
    return corpus


def read_member(corpus: zipfile.ZipFile, name: str, size: int, digest: str) -> bytes:
    data = corpus.read(name)
    if len(data) != size:
        raise RuntimeError(f"Silesia member {name} decoded to {len(data)} bytes, expected {size}")
    actual_hash = sha256_bytes(data)
    if actual_hash != digest:
        raise RuntimeError(
            f"Silesia member {name} SHA-256 is {actual_hash}, expected {digest}"
        )
    return data


def adapter_suffix() -> str:
    if sys.platform == "darwin":
        return ".dylib"
    if os.name == "nt":
        return ".dll"
    return ".so"


def adapter_compiler(base: Sequence[str], install_name: str) -> list[str]:
    compiler = list(base)
    if sys.platform == "darwin":
        # ld64 derives LC_UUID from the linked image.  Fixing LC_ID_DYLIB makes
        # adapters built at different temporary paths byte-identical while
        # retaining the LC_UUID required by dyld.
        compiler.append(f"-Wl,-install_name,@rpath/{install_name}")
    return compiler


def normalize_command(
    command: Sequence[str],
    *,
    source: Path,
    output: Path,
) -> list[str]:
    replacements = {
        str(output): f"corpus/scoring/tools/{output.name}",
        str(source): source.name,
    }
    ordered = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)
    normalized: list[str] = []
    for token in command:
        value = token
        for concrete, symbolic in ordered:
            value = value.replace(concrete, symbolic)
        normalized.append(value)
    return normalized


def provenance_record(provenance: dict[str, Any], *, library_name: str) -> dict[str, Any]:
    record = {
        "build_configuration": provenance["build_configuration"],
        "cmake_cache_sha256": provenance["cmake_cache_sha256"],
        "commit": provenance["commit"],
        "generated_header_sha256": provenance["generated_header_sha256"],
        "shared_library_file": library_name,
        "shared_library_sha256": provenance["shared_library_sha256"],
        "tree": provenance["tree"],
        "version": provenance["version"],
    }
    if "tag" in provenance:
        record["tag"] = provenance["tag"]
    if "source_header_sha256" in provenance:
        record["source_header_sha256"] = provenance["source_header_sha256"]
    return record


def build_adapters(
    tools_dir: Path,
    *,
    compiler: Sequence[str],
    stock_checkout: Path,
    stock_build_dir: Path,
    stock_library: Path,
    zng_checkout: Path,
    zng_build_dir: Path,
    zng_library: Path,
) -> dict[str, Any]:
    tools_dir.mkdir(parents=True, exist_ok=False)
    suffix = adapter_suffix()
    stock_source = HERE / "stock_zlib.c"
    zng_source = HERE / "reference.c"
    stock_output = tools_dir / f"libwhitefoot_stock_zlib{suffix}"
    zng_output = tools_dir / f"libwhitefoot_raw_reference{suffix}"

    stock_provenance = stock_zlib.verify_provenance(
        stock_checkout, stock_build_dir, stock_library
    )
    zng_provenance = reference.verify_provenance(zng_checkout, zng_build_dir, zng_library)
    zng_provenance["cmake_cache_sha256"] = sha256_file(
        zng_build_dir / "CMakeCache.txt"
    )
    zng_provenance["tag"] = "2.3.3"

    stock_command = stock_zlib.build_adapter(
        stock_source,
        stock_checkout,
        stock_build_dir,
        stock_library,
        stock_output,
        adapter_compiler(compiler, stock_output.name),
    )
    zng_command = reference.build_adapter(
        zng_source,
        zng_checkout,
        zng_build_dir,
        zng_library,
        zng_output,
        adapter_compiler(compiler, zng_output.name),
    )
    stock_adapter = stock_zlib.load_adapter(stock_output)
    zng_adapter = reference.load_adapter(zng_output)

    # Exercise each adapter independently before the full-corpus cross-check.
    stock_zlib.verify_roundtrips(stock_adapter)
    reference.verify_status_contract(zng_adapter)

    stock_compile = normalize_command(
        stock_command,
        source=stock_source,
        output=stock_output,
    )
    zng_compile = normalize_command(
        zng_command,
        source=zng_source,
        output=zng_output,
    )

    return {
        "stock": {
            "adapter": stock_adapter,
            "artifact": stock_output,
            "artifact_sha256": sha256_file(stock_output),
            "compile_command": stock_compile,
            "library": provenance_record(
                stock_provenance, library_name=stock_library.name
            ),
            "source": stock_source,
        },
        "zng": {
            "adapter": zng_adapter,
            "artifact": zng_output,
            "artifact_sha256": sha256_file(zng_output),
            "compile_command": zng_compile,
            "library": provenance_record(zng_provenance, library_name=zng_library.name),
            "source": zng_source,
        },
    }


def adapter_manifest(name: str, built: dict[str, Any]) -> dict[str, Any]:
    helper = HERE / ("stock_zlib.py" if name == "stock" else "reference.py")
    artifact_name = built["artifact"].name
    return {
        "artifact_file": f"corpus/scoring/tools/{artifact_name}",
        "artifact_sha256": built["artifact_sha256"],
        "compile_command": built["compile_command"],
        "helper_file": helper.name,
        "helper_sha256": sha256_file(helper),
        "source_file": built["source"].name,
        "source_sha256": sha256_file(built["source"]),
    }


def expected_output_files() -> set[str]:
    suffix = adapter_suffix()
    files = {
        f"tools/libwhitefoot_stock_zlib{suffix}",
        f"tools/libwhitefoot_raw_reference{suffix}",
    }
    for name, _, _ in MEMBERS:
        files.add(f"{name}.raw")
        files.add(f"{name}.deflate")
    return files


def verify_output_membership(root: Path) -> None:
    if not root.is_dir():
        raise RuntimeError(f"missing scoring artifact directory: {root}")
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    expected = expected_output_files()
    if actual != expected:
        raise RuntimeError(
            "scoring artifact membership drift: "
            f"missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}"
        )


def verify_rebuilt_adapters(built: dict[str, Any]) -> None:
    for key in ("stock", "zng"):
        rebuilt = built[key]["artifact"]
        frozen = OUTPUT_ROOT / "tools" / rebuilt.name
        if not frozen.is_file():
            raise RuntimeError(f"missing frozen {key} adapter: {frozen}")
        if sha256_file(frozen) != built[key]["artifact_sha256"]:
            raise RuntimeError(f"{key} adapter is not byte-identical after rebuild")
        require_exact_file(frozen, rebuilt.read_bytes(), f"frozen {key} adapter")


def manifest_document(
    *,
    compiler_argv: Sequence[str],
    built: dict[str, Any],
    members: list[dict[str, Any]],
    compressed_total: int,
) -> dict[str, Any]:
    compiler_version = run_text([*compiler_argv, "--version"])
    return {
        "aggregate": {
            "member_count": len(MEMBERS),
            "raw_deflate_bytes": compressed_total,
            "source_bytes": SOURCE_TOTAL,
        },
        "archive": {
            "file": "silesia.zip",
            "sha256": ARCHIVE_SHA256,
            "size": ARCHIVE_SIZE,
            "source_page": SILESIA_PAGE,
            "source_url": SILESIA_ARCHIVE_URL,
        },
        "compression": {
            "api": "deflateInit2",
            "flush": "Z_FINISH exactly once",
            "level": LEVEL,
            "mem_level": MEM_LEVEL,
            "method": METHOD,
            "output": "one raw RFC 1951 stream per complete member",
            "strategy": "Z_DEFAULT_STRATEGY",
            "window_bits": WINDOW_BITS,
        },
        "generator": {
            "file": Path(__file__).name,
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "members": members,
        "order": [name for name, _, _ in MEMBERS],
        "schema": SCHEMA,
        "toolchain": {
            "adapter_build": {
                "compiler_argv": list(compiler_argv),
                "compiler_sha256": sha256_file(Path(compiler_argv[0])),
                "compiler_version": compiler_version,
                "machine": platform.machine(),
                "platform": sys.platform,
                "system": platform.system(),
                "working_directory": ".",
            },
            "stock_zlib_compressor_and_decoder": {
                "adapter": adapter_manifest("stock", built["stock"]),
                "library": built["stock"]["library"],
                "public_api_only": True,
            },
            "zlib_ng_reference_decoder": {
                "adapter": adapter_manifest("zng", built["zng"]),
                "library": built["zng"]["library"],
                "public_api_only": True,
                "tag": "2.3.3",
            },
        },
        "validation": {
            "capacity": "exact uncompressed member size",
            "expected_status": {"name": "Done", "value": 0},
            "output": "byte-identical complete source member",
            "validated_decoders": ["stock zlib 1.3.2", "zlib-ng 2.3.3"],
            "validated_stream_count": len(MEMBERS),
        },
    }


def prepare(
    *,
    check: bool,
    archive: Path,
    compiler_argv: Sequence[str],
    stock_checkout: Path,
    stock_build_dir: Path,
    stock_library: Path,
    zng_checkout: Path,
    zng_build_dir: Path,
    zng_library: Path,
) -> None:
    if sum(size for _, size, _ in MEMBERS) != SOURCE_TOTAL:
        raise RuntimeError("hard-coded Silesia member sizes do not match SOURCE_TOTAL")

    if check:
        if not MANIFEST_PATH.is_file():
            raise RuntimeError(f"missing frozen scoring manifest: {MANIFEST_PATH}")
        verify_output_membership(OUTPUT_ROOT)
    else:
        if MANIFEST_PATH.exists():
            raise RuntimeError(
                f"refusing to overwrite existing scoring manifest: {MANIFEST_PATH}"
            )
        if OUTPUT_ROOT.exists():
            raise RuntimeError(
                f"refusing to overwrite existing scoring artifacts: {OUTPUT_ROOT}"
            )

    corpus = verify_archive_identity(archive)
    staging_parent: Path | None = None
    temporary: tempfile.TemporaryDirectory[str] | None = None
    try:
        if check:
            temporary = tempfile.TemporaryDirectory(prefix="whitefoot-scoring-check-")
            work_root = Path(temporary.name)
        else:
            OUTPUT_ROOT.parent.mkdir(parents=True, exist_ok=True)
            staging_parent = Path(
                tempfile.mkdtemp(prefix=".scoring-staging-", dir=OUTPUT_ROOT.parent)
            )
            work_root = staging_parent

        built = build_adapters(
            work_root / "tools",
            compiler=compiler_argv,
            stock_checkout=stock_checkout,
            stock_build_dir=stock_build_dir,
            stock_library=stock_library,
            zng_checkout=zng_checkout,
            zng_build_dir=zng_build_dir,
            zng_library=zng_library,
        )
        if check:
            verify_rebuilt_adapters(built)

        member_records: list[dict[str, Any]] = []
        compressed_total = 0
        for ordinal, (name, source_size, source_hash) in enumerate(MEMBERS):
            data = read_member(corpus, name, source_size, source_hash)
            compressed = stock_zlib.compress_raw(
                built["stock"]["adapter"], data, LEVEL, STRATEGY
            )
            compressed_hash = sha256_bytes(compressed)

            stock_status, stock_output = stock_zlib.inflate_full(
                built["stock"]["adapter"], compressed, source_size
            )
            if stock_status != stock_zlib.STOCK_DONE or stock_output != data:
                raise RuntimeError(f"stock zlib failed the full-capacity check for {name}")
            zng_status, zng_output = reference.inflate_once(
                built["zng"]["adapter"], compressed, source_size
            )
            if zng_status != reference.WF_RAW_DONE or zng_output != data:
                raise RuntimeError(f"zlib-ng failed the full-capacity check for {name}")

            source_relative = Path(f"{name}.raw")
            compressed_relative = Path(f"{name}.deflate")
            artifact_root = OUTPUT_ROOT if check else work_root
            source_path = artifact_root / source_relative
            compressed_path = artifact_root / compressed_relative
            if check:
                require_exact_file(source_path, data, f"frozen source member {name}")
                require_exact_file(
                    compressed_path, compressed, f"frozen raw-DEFLATE stream {name}"
                )
            else:
                write_new_file(source_path, data)
                write_new_file(compressed_path, compressed)

            member_records.append(
                {
                    "name": name,
                    "order": ordinal,
                    "raw_deflate": {
                        "file": f"corpus/scoring/{compressed_relative.as_posix()}",
                        "sha256": compressed_hash,
                        "size": len(compressed),
                    },
                    "source": {
                        "file": f"corpus/scoring/{source_relative.as_posix()}",
                        "sha256": source_hash,
                        "size": source_size,
                    },
                }
            )
            compressed_total += len(compressed)
            print(
                f"verified {ordinal + 1:02d}/{len(MEMBERS):02d} {name}: "
                f"{source_size} -> {len(compressed)} bytes",
                flush=True,
            )

        document = manifest_document(
            compiler_argv=compiler_argv,
            built=built,
            members=member_records,
            compressed_total=compressed_total,
        )
        manifest_bytes = canonical_json(document)

        if check:
            require_exact_file(
                MANIFEST_PATH, manifest_bytes, "canonical scoring manifest"
            )
        else:
            verify_output_membership(work_root)
            work_root.rename(OUTPUT_ROOT)
            staging_parent = None
            write_new_file(MANIFEST_PATH, manifest_bytes)

        mode = "verified" if check else "created"
        print(
            f"{mode} {len(MEMBERS)} streams, {SOURCE_TOTAL} source bytes, "
            f"{compressed_total} raw-DEFLATE bytes"
        )
    finally:
        corpus.close()
        if temporary is not None:
            temporary.cleanup()
        if staging_parent is not None and staging_parent.exists():
            shutil.rmtree(staging_parent)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate in temporary storage and verify all frozen bytes",
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=DEFAULT_ARCHIVE,
        help="official Silesia zip with the frozen identity",
    )
    parser.add_argument(
        "--stock-checkout",
        type=Path,
        default=stock_zlib.DEFAULT_RESEARCH_ROOT / "zlib",
    )
    parser.add_argument(
        "--stock-build-dir",
        type=Path,
        default=stock_zlib.DEFAULT_RESEARCH_ROOT / "build-zlib",
    )
    parser.add_argument("--stock-library", type=Path)
    parser.add_argument(
        "--zng-checkout",
        type=Path,
        default=reference.DEFAULT_RESEARCH_ROOT / "zlib-ng",
    )
    parser.add_argument(
        "--zng-build-dir",
        type=Path,
        default=reference.DEFAULT_RESEARCH_ROOT / "build-zng-dispatch",
    )
    parser.add_argument("--zng-library", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    compiler_argv = LOCKED_COMPILER_ARGV
    if not LOCKED_CLANG.is_file():
        raise RuntimeError(f"missing locked C compiler: {LOCKED_CLANG}")

    stock_checkout = args.stock_checkout.resolve()
    stock_build_dir = args.stock_build_dir.resolve()
    stock_library = (
        args.stock_library.resolve()
        if args.stock_library is not None
        else stock_zlib.find_library(stock_build_dir)
    )
    zng_checkout = args.zng_checkout.resolve()
    zng_build_dir = args.zng_build_dir.resolve()
    zng_library = (
        args.zng_library.resolve()
        if args.zng_library is not None
        else reference.find_library(zng_build_dir)
    )

    prepare(
        check=args.check,
        archive=args.archive.resolve(),
        compiler_argv=compiler_argv,
        stock_checkout=stock_checkout,
        stock_build_dir=stock_build_dir,
        stock_library=stock_library,
        zng_checkout=zng_checkout,
        zng_build_dir=zng_build_dir,
        zng_library=zng_library,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
