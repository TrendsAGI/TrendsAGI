from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        if entry.name.startswith("__"):
            continue
        if entry.suffix in {".py", ".pyc"}:
            continue
        target = dst / entry.name
        if entry.is_dir():
            _copy_tree(entry, target)
        else:
            _copy_file(entry, target)


def scaffold(template_type: str, output_dir: str = ".") -> None:
    out_dir = Path(output_dir).resolve()
    template_root = Path(__file__).resolve().parent / "templates"

    if template_type == "docker":
        source = Path(template_root / "Dockerfile")
        target = out_dir / "Dockerfile"
        _copy_file(source, target)
        print(f"Created {target}")
        return

    if template_type == "terraform":
        source = Path(template_root / "terraform")
        target = out_dir / "terraform"
        _copy_tree(source, target)
        print(f"Created {target}")
        return

    raise ValueError("template type must be one of: docker, terraform")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trendsagi")
    subparsers = parser.add_subparsers(dest="command")

    scaffold_parser = subparsers.add_parser(
        "scaffold",
        help="Copy customer-hosted integration templates to your current workspace.",
    )
    scaffold_parser.add_argument(
        "--type",
        dest="template_type",
        required=True,
        choices=["docker", "terraform"],
        help="Template bundle to copy.",
    )
    scaffold_parser.add_argument(
        "--output-dir",
        default=".",
        help="Target directory (defaults to current working directory).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scaffold":
        scaffold(args.template_type, args.output_dir)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
