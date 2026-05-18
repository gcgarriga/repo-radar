from pathlib import Path

from join_users import normalize


def run_pipeline(export_dir: Path) -> None:
    raw_a = export_dir / "provider-a.csv"
    raw_b = export_dir / "provider-b.json"
    copied_a = export_dir / "copied-provider-a.csv"
    copied_b = export_dir / "copied-provider-b.json"
    copied_a.write_text(raw_a.read_text())
    copied_b.write_text(raw_b.read_text())
    normalize(copied_a, copied_b, export_dir / "matches.json")
