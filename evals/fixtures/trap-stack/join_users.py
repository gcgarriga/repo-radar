import csv
import json
from pathlib import Path


def normalize(provider_a_csv: Path, provider_b_json: Path, output_path: Path) -> None:
    provider_a_rows = list(csv.DictReader(provider_a_csv.read_text().splitlines()))
    provider_b_rows = json.loads(provider_b_json.read_text())

    matches = []
    for left in provider_a_rows:
        left_email = left["email"].strip().lower()
        for right in provider_b_rows:
            if left_email == right["email"].strip().lower():
                matches.append(
                    {
                        "email": left_email,
                        "provider_a": json.dumps(left),
                        "provider_b": json.dumps(right),
                    }
                )

    output_path.write_text(json.dumps(matches))
