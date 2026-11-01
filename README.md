# mid_grep

A dependency-free command-line tool that browses a file or a whole directory tree
and finds an **exact hexadecimal byte sequence** inside files — text or binary.

Unlike a text grep, the pattern is a sequence of raw bytes, so you can hunt for
magic numbers, firmware markers, protocol payloads, embedded signatures, or any
arbitrary bytes in executables and images.

## Features

- Exact byte-for-byte matching (no regex, no encoding surprises)
- Recursive directory scan with a sensible default ignore list (`/.git`,
  `__pycache__`, `node_modules`, virtualenvs, …)
- Flexible hex input: spaces, commas, colons, dashes, `0x…` and `\x…` prefixes
- Reads files in 1 MiB chunks, so multi-gigabyte files work and matches that
  span a chunk boundary are still found
- Hexdump-style output with optional surrounding context and ASCII preview
- ANSI colours on a terminal (disable with `--no-color` or `NO_COLOR`)
- Filename filtering with `--include` / `--exclude`, plus extra ignored dirs
- Script-friendly exit codes

## Requirements

- Python 3.8 or newer
- No third-party packages

## Usage

```text
python3 main.py [options] HEX [PATH]
```

`HEX` is the byte sequence to look for and `PATH` is a file or directory
(default: the current directory). Directories are searched recursively.

### Examples

```bash
# Find "Hello" in the current directory
python3 main.py '48 65 6c 6c 6f'

# Search one binary file for the PNG signature (89 50 4E 47)
python3 main.py 0x89504e47 picture.png

# Same bytes written with separators and \x escapes
python3 main.py '\xde\xad\xbe\xef' firmware.bin
python3 main.py 'de:ad:be:ef' firmware.bin

# Show 8 bytes of context around every match
python3 main.py '474e5000' images/ -C 8

# Count matches per file, only for *.bin files
python3 main.py 'deadbeef' . --include '*.bin' --count

# List files that contain the sequence, skipping node_modules and .build
python3 main.py 'cafebabe' . -l --exclude-dir node_modules --exclude-dir .build

# Only search the top level of a directory
python3 main.py '00ff00ff' downloads/ --no-recursive
```

Make the script directly executable if you like:

```bash
chmod +x main.py
ln -s "$PWD/main.py" ~/.local/bin/mid_grep   # optional
mid_grep '48656c6c6f' .
```

## Hex input formats

All of the following are equivalent:

| Input | Bytes |
| --- | --- |
| `48656c6c6f` | `48 65 6c 6c 6f` |
| `48 65 6c 6c 6f` | `48 65 6c 6c 6f` |
| `48,65,6c,6c,6f` | `48 65 6c 6c 6f` |
| `48:65:6c:6c:6f` | `48 65 6c 6c 6f` |
| `0x48 0x65 0x6c 0x6c 0x6f` | `48 65 6c 6c 6f` |
| `\x48\x65\x6c\x6c\x6f` | `48 65 6c 6c 6f` |

The sequence must contain hexadecimal digits only and an even number of them.
Characters such as `P`, `N` or `G` are rejected — encode ASCII text as its
hexadecimal bytes (for example `PNG` becomes `50 4e 47`).

## Output format

```text
path/to/file:0x0000002a  48 65 6c 6c 6f 00  |Hello.|
```

- `path/to/file` — file containing the match
- `0x0000002a` — byte offset of the match from the start of the file
- hex bytes — the match, or the surrounding bytes when `--context` is used
- `|Hello.|` — ASCII preview; non-printable bytes are shown as `.`

With `--context 4`, the match bytes are still highlighted in colour (on a TTY)
and the hexdump line is widened accordingly.

`--count` prints one `path:count` line per matching file plus a final
`total:N` line. `--files-with-matches` prints each matching path once.

## Options

| Option | Description |
| --- | --- |
| `HEX` | Hexadecimal byte sequence to search for (required) |
| `PATH` | File or directory to search (default: `.`) |
| `--no-recursive` | Only scan the top level of a directory |
| `-C, --context N` | Show `N` bytes before and after each match |
| `-c, --count` | Print match counts per file instead of each match |
| `-l, --files-with-matches` | Only print names of files that contain a match |
| `-m, --max-count N` | Stop after `N` matches in each file |
| `--include GLOB` | Only search filenames matching `GLOB` (repeatable) |
| `--exclude GLOB` | Skip filenames matching `GLOB` (repeatable) |
| `--exclude-dir NAME` | Skip directories named `NAME` (repeatable) |
| `--no-color` | Disable coloured output |
| `-v, --verbose` | Print a scan summary on stderr |
| `-V, --version` | Show the program version |
| `-h, --help` | Show help |

By default these directories are skipped during recursion: `.git`, `.hg`,
`.svn`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`,
`node_modules`, `.venv`, `venv`, `.idea`.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | At least one match was found |
| `1` | No match was found |
| `2` | Invalid arguments, invalid hex sequence, or missing path |

Unreadable files are reported on stderr and skipped; they do not abort the scan.

## Project layout

```text
cli_tool/
├── main.py    # the mid_grep CLI
└── README.md
```

## Development

Syntax check and a quick smoke test:

```bash
python3 -m py_compile main.py
printf 'Hello, world!\n' > /tmp/sample.txt
python3 main.py '48 65 6c 6c 6f' /tmp/sample.txt
```

Expected output:

```text
/tmp/sample.txt:0x00000000  48 65 6c 6c 6f  |Hello|
```
