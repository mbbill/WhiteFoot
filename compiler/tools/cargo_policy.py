#!/usr/bin/env python3
"""Run reviewed Cargo commands without ambient Cargo configuration."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_COMMANDS = frozenset(
    {"build", "check", "clippy", "doc", "fmt", "metadata", "test"}
)
FORBIDDEN_PATH_OPTIONS = ("--config", "--manifest-path", "--target", "--target-dir")
TOOLCHAIN_CHANNEL = json.loads(
    (ROOT / "toolchain-lock.json").read_text(encoding="utf-8")
)["channel"]
RUSTUP_HOME = Path(
    os.environ.get(
        "RUSTUP_HOME",
        str(Path(os.environ.get("HOME") or Path.home()) / ".rustup"),
    )
).resolve()
LEXICAL_OBSERVER_PACKAGE = "whitefoot-lexical-observer"
LEXICAL_OBSERVER_TARGET = "whitefoot-lexical-observer"
LEXICAL_OBSERVER_MANIFEST = Path(
    "crates/whitefoot-lexical-observer/Cargo.toml"
)


def ambient_tool_configuration_files(
    working_directory: Path,
    cargo_home: Path,
    workspace: Path,
) -> tuple[Path, ...]:
    """Return Cargo, rustfmt, or Clippy configuration discoverable by a run."""
    candidates = [cargo_home / "config", cargo_home / "config.toml"]
    working = working_directory.resolve()
    candidates.extend(
        candidate
        for directory in (working, *working.parents)
        for candidate in (
            directory / ".cargo" / "config",
            directory / ".cargo" / "config.toml",
        )
    )
    source = workspace.resolve()
    tool_directories = dict.fromkeys(
        (working, *working.parents, source, *source.parents)
    )
    candidates.extend(
        candidate
        for directory in tool_directories
        for candidate in (
            directory / ".rustfmt.toml",
            directory / "rustfmt.toml",
            directory / ".clippy.toml",
            directory / "clippy.toml",
        )
    )
    return tuple(candidate for candidate in candidates if candidate.exists())


def closed_environment(
    cargo_home: Path,
    target_directory: Path,
    home_directory: Path,
    temporary_directory: Path,
    command: str,
) -> dict[str, str]:
    """Construct the complete environment admitted to a Cargo subprocess."""
    environment = {
        "CARGO_HOME": str(cargo_home),
        "CARGO_INCREMENTAL": "0",
        "CARGO_NET_OFFLINE": "true",
        "CARGO_TARGET_DIR": str(target_directory),
        "CARGO_TERM_COLOR": "never",
        "HOME": str(home_directory),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", ""),
        "RUSTUP_HOME": str(RUSTUP_HOME),
        "RUSTUP_TOOLCHAIN": TOOLCHAIN_CHANNEL,
        "SOURCE_DATE_EPOCH": "0",
        "TMPDIR": str(temporary_directory),
        "ZERO_AR_DATE": "1",
    }
    if command == "doc":
        environment["RUSTDOCFLAGS"] = "-D warnings"
    return environment


def cargo_command(arguments: Sequence[str], workspace: Path = ROOT) -> tuple[str, ...]:
    """Construct one manifest-explicit allowlisted Cargo command."""
    if not arguments or arguments[0] not in ALLOWED_COMMANDS:
        raise ValueError("first argument must be an allowlisted Cargo command")
    forbidden_options = tuple(
        option
        for option in FORBIDDEN_PATH_OPTIONS
        if any(
            argument == option or argument.startswith(f"{option}=")
            for argument in arguments
        )
    )
    if forbidden_options:
        raise ValueError(f"Cargo path/configuration options are forbidden: {forbidden_options}")
    if any(argument.startswith("-Z") for argument in arguments):
        raise ValueError("unstable Cargo options are forbidden")
    if arguments[0] == "test" and "--doc" in arguments:
        raise ValueError("Cargo doctest execution is forbidden")
    manifest = workspace.resolve() / "Cargo.toml"
    if not manifest.is_file():
        raise ValueError(f"Cargo manifest is not a regular file: {manifest}")
    return (
        "cargo",
        arguments[0],
        "--manifest-path",
        str(manifest),
        *arguments[1:],
    )


def run_cargo(
    arguments: Sequence[str],
    *,
    workspace: Path = ROOT,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run one allowlisted Cargo command from a configuration-free directory."""
    workspace = workspace.resolve()
    command = cargo_command(arguments, workspace)

    with tempfile.TemporaryDirectory(prefix="whitefoot-cargo-policy-") as temporary:
        temporary_root = Path(temporary)
        working_directory = temporary_root / "work"
        cargo_home = temporary_root / "cargo-home"
        target_directory = temporary_root / "target"
        home_directory = temporary_root / "home"
        child_temporary_directory = temporary_root / "tmp"
        working_directory.mkdir()
        cargo_home.mkdir()
        home_directory.mkdir()
        child_temporary_directory.mkdir()
        configurations = ambient_tool_configuration_files(
            working_directory,
            cargo_home,
            workspace,
        )
        if configurations:
            names = ", ".join(str(path) for path in configurations)
            raise RuntimeError(f"Cargo configuration reached isolated run: {names}")
        return subprocess.run(
            command,
            cwd=working_directory,
            env=closed_environment(
                cargo_home,
                target_directory,
                home_directory,
                child_temporary_directory,
                arguments[0],
            ),
            check=False,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=True,
        )


@contextmanager
def built_lexical_observer(
    *, workspace: Path = ROOT
) -> Iterator[Path]:
    """Build and yield the exact observer executable from one fresh target."""

    workspace = workspace.resolve()
    with tempfile.TemporaryDirectory(
        prefix="whitefoot-observer-build-"
    ) as temporary:
        temporary_root = Path(temporary)
        working_directory = temporary_root / "work"
        cargo_home = temporary_root / "cargo-home"
        target_directory = temporary_root / "target"
        home_directory = temporary_root / "home"
        child_temporary_directory = temporary_root / "tmp"
        for directory in (
            working_directory,
            cargo_home,
            home_directory,
            child_temporary_directory,
        ):
            directory.mkdir()
        configurations = ambient_tool_configuration_files(
            working_directory,
            cargo_home,
            workspace,
        )
        if configurations:
            names = ", ".join(str(path) for path in configurations)
            raise RuntimeError(f"Cargo configuration reached observer build: {names}")

        arguments = (
            "build",
            "--package",
            LEXICAL_OBSERVER_PACKAGE,
            "--bin",
            LEXICAL_OBSERVER_TARGET,
            "--locked",
            "--offline",
            "--message-format=json-render-diagnostics",
        )
        result = subprocess.run(
            cargo_command(arguments, workspace),
            cwd=working_directory,
            env=closed_environment(
                cargo_home,
                target_directory,
                home_directory,
                child_temporary_directory,
                "build",
            ),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or "observer build failed without a diagnostic"
            raise RuntimeError(detail)

        expected_manifest = (workspace / LEXICAL_OBSERVER_MANIFEST).resolve()
        executables: list[Path] = []
        for line in result.stdout.splitlines():
            try:
                message = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError("Cargo emitted a malformed JSON build message") from error
            if message.get("reason") != "compiler-artifact":
                continue
            if Path(message.get("manifest_path", "")).resolve() != expected_manifest:
                continue
            target = message.get("target", {})
            if (
                target.get("name") != LEXICAL_OBSERVER_TARGET
                or target.get("kind") != ["bin"]
                or target.get("crate_types") != ["bin"]
            ):
                raise RuntimeError("Cargo observer target identity drifted")
            executable = message.get("executable")
            if not isinstance(executable, str):
                raise RuntimeError("Cargo did not declare the observer executable")
            executables.append(Path(executable))

        if len(executables) != 1:
            raise RuntimeError(
                f"Cargo declared {len(executables)} observer executables, expected one"
            )
        executable = executables[0]
        try:
            executable.resolve().relative_to(target_directory.resolve())
        except ValueError as error:
            raise RuntimeError("Cargo observer executable escaped its fresh target") from error
        if executable.is_symlink() or not executable.is_file():
            raise RuntimeError("Cargo observer executable is not one regular file")
        if not os.access(executable, os.X_OK):
            raise RuntimeError("Cargo observer executable is not executable")
        yield executable


def main() -> None:
    """Forward command-line arguments and preserve Cargo's exit status."""
    try:
        result = run_cargo(sys.argv[1:])
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"cargo policy: {error}") from error
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
