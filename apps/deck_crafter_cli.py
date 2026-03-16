"""Default CLI entrypoint for Deck Crafter."""

from __future__ import annotations

import argparse
from pathlib import Path

from deck_crafter import __version__
from deck_crafter.application import generate_deck
from deck_crafter.visual_interface import serve_visual_interface


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="deck-crafter",
        description="Deck Crafter command-line interface.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    build_parser = subparsers.add_parser(
        "build",
        help="Generate LaTeX or PDF output from YAML.",
    )
    build_parser.add_argument(
        "configuration_file", type=Path, help="Path to the YAML project file."
    )
    build_parser.add_argument(
        "--tex-only",
        action="store_true",
        help="Render the .tex file without compiling it to PDF.",
    )

    serve_parser = subparsers.add_parser("serve", help="Start the local visual editor.")
    serve_parser.add_argument(
        "configuration_file",
        nargs="?",
        type=Path,
        help="Optional YAML project file to open on startup.",
    )
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    serve_parser.add_argument("--port", default=8765, type=int, help="Port to bind.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entrypoint."""
    args = build_parser().parse_args(argv)
    if args.command == "build":
        outputs = generate_deck(args.configuration_file, compile_pdf=not args.tex_only)
        for output in outputs:
            print(output)
        return 0
    if args.command == "serve":
        serve_visual_interface(
            host=args.host,
            port=args.port,
            configuration_file=args.configuration_file,
        )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
