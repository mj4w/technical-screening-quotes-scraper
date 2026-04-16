from __future__ import annotations

import csv
import json
from pathlib import Path

from quotes_scraper.models import QuoteRecord


# Keeping serialization separate from scraping makes the code easier to test
# and easier to extend if a second output format is requested later.
def write_json(records: list[QuoteRecord], output_path: Path) -> None:
    payload = {
        "quote_count": len(records),
        "quotes": [
            {"quote": record.quote, "author": record.author, "tags": list(record.tags)}
            for record in records
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(records: list[QuoteRecord], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["quote", "author", "tags"])
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "quote": record.quote,
                    "author": record.author,
                    "tags": "|".join(record.tags),
                }
            )
