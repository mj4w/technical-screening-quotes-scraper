from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

from quotes_scraper.env import load_dotenv
from quotes_scraper.s3_upload import upload_file
from quotes_scraper.scraper import QuotesScraper
from quotes_scraper.writers import write_json


async def async_main() -> int:
    # This runner is what the EC2 instance or cron job executes: scrape first,
    # then publish a timestamped artifact to S3.
    load_dotenv()

    bucket = os.environ["QUOTES_S3_BUCKET"]
    prefix = os.environ.get("QUOTES_S3_PREFIX", "quotes-to-scrape")
    output_path = Path(os.environ.get("QUOTES_OUTPUT_PATH", "output/quotes.json"))

    output_path.parent.mkdir(parents=True, exist_ok=True)

    scraper = QuotesScraper(
        delay_seconds=float(os.environ.get("QUOTES_DELAY_SECONDS", "0")),
        concurrency=int(os.environ.get("QUOTES_CONCURRENCY", "10")),
    )
    records = await scraper.scrape()
    write_json(records, output_path)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    key = f"{prefix}/quotes_{timestamp}.json"
    region = os.environ.get("AWS_REGION")
    s3_uri, https_url = upload_file(file_path=output_path, bucket=bucket, key=key, region=region)
    print(s3_uri)
    print(https_url)
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
