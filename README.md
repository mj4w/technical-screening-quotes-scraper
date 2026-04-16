# Quotes to Scrape Technical Screening

This project scrapes every quote exposed by `https://quotes.toscrape.com/search.aspx`, aggregates all tags for each quote, writes the dataset locally, and can upload the output file to Amazon S3.

The scraper uses an asynchronous request flow with `asyncio` and `aiohttp`, so the author/tag requests are fetched concurrently instead of one at a time.

## What the scraper does

The target page is a form-driven flow:

1. `GET /search.aspx` to collect all authors and the page `__VIEWSTATE`.
2. `POST /filter.aspx` with an author to discover the valid tags for that author.
3. `POST /filter.aspx` with each author/tag pair to collect matching quotes.
4. Merge duplicate quotes so the final output contains one record per quote with all of its tags.
5. Backfill any quotes missing from the search flow by reading the site's paginated quote pages.

The fallback in step 5 is necessary because `search.aspx` currently omits a few untagged quotes, including one from `Ayn Rand`. Without that backfill, the dataset would stop at `97` quotes instead of the full `100`.

Each record includes:

- `quote`
- `author`
- `tags`

## Project structure

- `quotes_scraper/config.py`: shared constants and request defaults
- `quotes_scraper/models.py`: typed data model for quote records
- `quotes_scraper/writers.py`: JSON and CSV serializers
- `quotes_scraper/env.py`: lightweight `.env` loader for local and EC2 runs
- `quotes_scraper/scraper.py`: async scraper and CLI
- `quotes_scraper/s3_upload.py`: uploads a local file to S3 with `boto3`
- `run_pipeline.py`: end-to-end scrape + upload runner for EC2 and cron
- `scripts/ec2_bootstrap.sh`: clones the repo and installs dependencies on Amazon Linux
- `scripts/setup_cron.sh`: installs a daily cron job

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m quotes_scraper.scraper --output output/quotes.json --format json
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
py -3 -m pip install -r requirements.txt
py -3 -m quotes_scraper.scraper --output output\quotes.json --format json
```

Optional flags:

- `--format csv`
- `--concurrency 10`
- `--delay-seconds 0.2`

To test the S3 pipeline locally, create a `.env` file from `.env.example`, fill in your AWS settings, and run:

```powershell
py -3 run_pipeline.py
```

## Output example

JSON:

```json
{
  "quote_count": 100,
  "quotes": [
    {
      "quote": "A day without sunshine is like, you know, night.",
      "author": "Steve Martin",
      "tags": ["humor", "obvious", "simile"]
    }
  ]
}
```

CSV:

```bash
python -m quotes_scraper.scraper --format csv --output output/quotes.csv
```

The CSV `tags` column uses `|` as the separator.

## Upload to S3

Set AWS credentials in the instance environment using an instance profile or `aws configure`, then run:

```bash
python run_pipeline.py
```

Environment variables:

- `QUOTES_S3_BUCKET`: required
- `QUOTES_S3_PREFIX`: optional, defaults to `quotes-to-scrape`
- `AWS_REGION`: optional
- `QUOTES_OUTPUT_PATH`: optional, defaults to `output/quotes.json`
- `QUOTES_DELAY_SECONDS`: optional
- `QUOTES_CONCURRENCY`: optional, defaults to `10`

You can also upload an existing file directly:

```bash
python -m quotes_scraper.s3_upload --file output/quotes.json --bucket my-bucket --key quotes/latest.json --region us-east-1
```

## EC2 deployment

1. Launch an EC2 instance.
2. SSH into the instance.
3. Run:

```bash
chmod +x scripts/ec2_bootstrap.sh scripts/setup_cron.sh
./scripts/ec2_bootstrap.sh https://github.com/<your-user>/<your-repo>.git
```

4. Copy `.env.example` to `.env` or export the variables directly:

```bash
export AWS_REGION=us-east-1
export QUOTES_S3_BUCKET=your-bucket-name
export QUOTES_S3_PREFIX=quotes-to-scrape
```

If you use `.env`, `run_pipeline.py` now loads it automatically and the cron helper will source it before each scheduled run.

5. Run the pipeline once:

```bash
source .venv/bin/activate
python run_pipeline.py
```

## Daily schedule bonus

Install the cron job:

```bash
./scripts/setup_cron.sh "$HOME/quotes-scraper"
```

The provided cron script schedules the pipeline for `02:00` every day.

## Submission checklist

1. Create a GitHub repository and push this project.
2. Create an S3 bucket and upload output with `run_pipeline.py`.
3. Make the uploaded object public or generate a presigned URL for the output file.
4. Share the GitHub repository link.
5. Share the S3 file link.
6. Optionally share a note showing the cron setup for the daily run.
