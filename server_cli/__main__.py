from __future__ import annotations

import argparse
import sys

from server_cli.commands.extract import add_extract_parser, run_extract


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="videocr-engine",
        description="Server-safe VideOCR extraction engine.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract Chinese hardcoded subtitles to SRT.",
    )
    add_extract_parser(extract_parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "extract":
        return run_extract(args)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
