#!/usr/bin/env python3
"""mid_grep - search files and folders for an exact hexadecimal byte sequence."""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

__version__ = "1.0.0"

CHUNK_SIZE = 1024 * 1024  # 1 MiB

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "venv",
    ".idea",
}

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
RED = "\033[31m"


class HexPatternError(ValueError):
    """Raised when the user-provided hexadecimal sequence is invalid."""


@dataclass
class Stats:
    files_scanned: int = 0
    files_matched: int = 0
    matches: int = 0


def parse_hex_sequence(text: str) -> bytes:
    """Convert a hexadecimal string into raw bytes.

    Accepted forms include ``"48 65 6c 6c 6f"``, ``"0xDEADBEEF"``,
    ``"\\x89PNG"``, ``"de:ad:be:ef"`` and plain ``"deadbeef"``.
    """
    cleaned = re.sub(r"(?i)0x|\\x", "", text)
    cleaned = re.sub(r"[\s,:_-]+", "", cleaned)

    if not cleaned:
        raise HexPatternError("the hexadecimal sequence is empty")

    if len(cleaned) % 2 != 0:
        raise HexPatternError(
            f"the hexadecimal sequence has an odd number of digits ({len(cleaned)})"
        )

    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise HexPatternError(
            "the sequence contains characters that are not hexadecimal digits"
        ) from exc


def iter_matches(
    file_path: Path, pattern: bytes, chunk_size: int = CHUNK_SIZE
) -> Iterator[int]:
    """Yield the offset of every exact occurrence of *pattern* in *file_path*.

    Files are read in chunks with a one-byte overlap so that sequences
    spanning a chunk boundary are still detected.
    """
    overlap = len(pattern) - 1
    previous = b""
    base = 0

    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break

            data = previous + chunk
            data_start = base - len(previous)
            position = 0

            while True:
                index = data.find(pattern, position)
                if index == -1:
                    break
                yield data_start + index
                position = index + 1

            previous = data[-overlap:] if overlap else b""
            base += len(chunk)


def format_match(
    display_path: str,
    offset: int,
    pattern: bytes,
    context: int,
    use_color: bool,
) -> str:
    """Build a hexdump-style line for a single match."""
    if context:
        start = max(0, offset - context)
        end = offset + len(pattern) + context
        try:
            with open(display_path, "rb") as handle:
                handle.seek(start)
                window = handle.read(end - start)
        except OSError:
            window = pattern
            start = offset
    else:
        window = pattern
        start = offset

    match_start = offset - start
    match_end = match_start + len(pattern)

    if use_color:
        location = f"{GREEN}{display_path}{RESET}:{CYAN}0x{offset:08x}{RESET}"
    else:
        location = f"{display_path}:0x{offset:08x}"

    hex_parts = []
    for index, byte in enumerate(window):
        token = f"{byte:02x}"
        if use_color and match_start <= index < match_end:
            token = f"{BOLD}{RED}{token}{RESET}"
        hex_parts.append(token)

    ascii_parts = []
    for index, byte in enumerate(window):
        character = chr(byte) if 32 <= byte < 127 else "."
        if use_color and match_start <= index < match_end:
            character = f"{BOLD}{RED}{character}{RESET}"
        ascii_parts.append(character)

    return f"{location}  {' '.join(hex_parts)}  |{''.join(ascii_parts)}|"


def iter_candidate_files(
    root: Path,
    recursive: bool,
    excluded_dirs: set[str],
    includes: Sequence[str],
    excludes: Sequence[str],
) -> Iterator[Path]:
    """Yield files under *root* that pass the directory/glob filters."""
    if root.is_file():
        yield root
        return

    if not root.is_dir():
        return

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if name not in excluded_dirs
        )
        if not recursive:
            dirnames[:] = []

        for filename in sorted(filenames):
            if includes and not any(
                fnmatch.fnmatch(filename, pattern) for pattern in includes
            ):
                continue
            if any(fnmatch.fnmatch(filename, pattern) for pattern in excludes):
                continue

            candidate = Path(dirpath) / filename
            if candidate.is_file():
                yield candidate


def process_file(
    file_path: Path,
    pattern: bytes,
    args: argparse.Namespace,
    use_color: bool,
    stats: Stats,
) -> None:
    """Search one file and print its matches."""
    display_path = str(file_path)
    count = 0

    try:
        for offset in iter_matches(file_path, pattern):
            count += 1
            stats.matches += 1

            if args.files_with_matches:
                print(display_path)
                break

            if not args.count:
                print(
                    format_match(
                        display_path, offset, pattern, args.context, use_color
                    )
                )

            if args.max_count is not None and count >= args.max_count:
                break
    except OSError as exc:
        print(f"mid_grep: {display_path}: {exc.strerror or exc}", file=sys.stderr)
        return

    if count:
        stats.files_matched += 1
        if args.count and not args.files_with_matches:
            print(f"{display_path}:{count}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mid_grep",
        description=(
            "Browse files and folders and find an exact hexadecimal byte sequence."
        ),
        epilog=(
            "examples:\n"
            "  mid_grep '48 65 6c 6c 6f' .\n"
            "  mid_grep 0xDEADBEEF firmware.bin\n"
            "  mid_grep '\\x89\\x50\\x4e\\x47' images/ --context 8\n"
            "  mid_grep 'de:ad:be:ef' src/ --include '*.bin' --count\n"
            "\n"
            "exit codes: 0 = matches found, 1 = no match, 2 = error"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "hex_sequence",
        metavar="HEX",
        help=(
            "hexadecimal sequence to search for, e.g. '48 65 6c 6c 6f', "
            "'0xDEADBEEF', 'de:ad:be:ef' or '\\x89\\x50\\x4e\\x47'"
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        metavar="PATH",
        help="file or directory to search (default: current directory)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="only search the top level of a directory",
    )
    parser.add_argument(
        "-C",
        "--context",
        type=int,
        default=0,
        metavar="N",
        help="show N bytes before and after each match (default: 0)",
    )
    parser.add_argument(
        "-c",
        "--count",
        action="store_true",
        help="print the number of matches per file instead of each match",
    )
    parser.add_argument(
        "-l",
        "--files-with-matches",
        action="store_true",
        help="only print the names of files that contain a match",
    )
    parser.add_argument(
        "-m",
        "--max-count",
        type=int,
        default=None,
        metavar="N",
        help="stop searching a file after N matches",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help="only search files whose name matches GLOB (repeatable)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip files whose name matches GLOB (repeatable)",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        metavar="NAME",
        help="skip directories with this name (repeatable, added to defaults)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable coloured output",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print a scan summary on stderr",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        pattern = parse_hex_sequence(args.hex_sequence)
    except HexPatternError as exc:
        parser.error(str(exc))

    if args.context < 0:
        parser.error("--context must be zero or positive")
    if args.max_count is not None and args.max_count <= 0:
        parser.error("--max-count must be greater than zero")

    root = Path(args.path)
    if not root.exists():
        print(f"mid_grep: {root}: no such file or directory", file=sys.stderr)
        return 2

    use_color = (
        sys.stdout.isatty()
        and not args.no_color
        and "NO_COLOR" not in os.environ
    )

    excluded_dirs = DEFAULT_EXCLUDED_DIRS | set(args.exclude_dir)
    stats = Stats()

    for file_path in iter_candidate_files(
        root,
        recursive=not args.no_recursive,
        excluded_dirs=excluded_dirs,
        includes=args.include,
        excludes=args.exclude,
    ):
        stats.files_scanned += 1
        process_file(file_path, pattern, args, use_color, stats)

    if args.count and not args.files_with_matches and stats.files_matched:
        print(f"total:{stats.matches}")

    if args.verbose:
        print(
            f"scanned {stats.files_scanned} file(s), "
            f"{stats.matches} match(es) in {stats.files_matched} file(s)",
            file=sys.stderr,
        )

    return 0 if stats.matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
