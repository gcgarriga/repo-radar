from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIRROR_DIRS = {
    Path("skills"): Path("repo_radar/_artifacts/skills"),
    Path("agents"): Path("repo_radar/_artifacts/agents"),
    Path("templates"): Path("repo_radar/_artifacts/templates"),
    Path("calibration"): Path("repo_radar/_artifacts/calibration"),
}


@dataclass(frozen=True)
class Drift:
    kind: str
    source: Path
    mirror: Path

    def format(self) -> str:
        if self.kind == "extra":
            return f"extra: {self.mirror}"
        return f"{self.kind}: {self.mirror}\n  source: {self.source}"


def relative_files(root: Path) -> set[Path]:
    return {path.relative_to(root) for path in root.rglob("*") if path.is_file()}


def find_drift(root: Path = ROOT) -> list[Drift]:
    drift = []
    for source_dir, mirror_dir in MIRROR_DIRS.items():
        source_root = root / source_dir
        mirror_root = root / mirror_dir
        source_files = relative_files(source_root)
        mirror_files = relative_files(mirror_root) if mirror_root.exists() else set()

        for relative_path in sorted(source_files - mirror_files):
            drift.append(
                Drift("missing", source_dir / relative_path, mirror_dir / relative_path)
            )
        for relative_path in sorted(mirror_files - source_files):
            drift.append(
                Drift("extra", source_dir / relative_path, mirror_dir / relative_path)
            )
        for relative_path in sorted(source_files & mirror_files):
            source_path = source_root / relative_path
            mirror_path = mirror_root / relative_path
            if not filecmp.cmp(source_path, mirror_path, shallow=False):
                drift.append(
                    Drift(
                        "different",
                        source_dir / relative_path,
                        mirror_dir / relative_path,
                    )
                )
    return drift


def sync_mirrors(root: Path = ROOT) -> None:
    for source_dir, mirror_dir in MIRROR_DIRS.items():
        source_root = root / source_dir
        mirror_root = root / mirror_dir
        source_files = relative_files(source_root)
        mirror_files = relative_files(mirror_root) if mirror_root.exists() else set()

        for relative_path in sorted(source_files):
            source_path = source_root / relative_path
            mirror_path = mirror_root / relative_path
            mirror_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, mirror_path)

        for relative_path in sorted(mirror_files - source_files):
            (mirror_root / relative_path).unlink()

        for directory in sorted(
            [path for path in mirror_root.rglob("*") if path.is_dir()],
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync or verify repo-radar packaged runtime artifact mirrors.",
    )
    parser.add_argument(
        "--check", action="store_true", help="Only verify mirrors; do not copy files."
    )
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = args.root.resolve()

    if args.check:
        drift = find_drift(root)
        if drift:
            print("Runtime artifact mirror drift detected:", file=sys.stderr)
            for item in drift:
                print(item.format(), file=sys.stderr)
            print(
                "Run python3 scripts/sync_runtime_artifacts.py to refresh packaged mirrors.",
                file=sys.stderr,
            )
            return 1
        return 0

    sync_mirrors(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
