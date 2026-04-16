from __future__ import annotations

# Centralizing these constants keeps the scraper behavior consistent across the
# CLI entrypoint and the EC2/S3 pipeline runner.
BASE_URL = "https://quotes.toscrape.com"
SEARCH_URL = f"{BASE_URL}/search.aspx"
FILTER_URL = f"{BASE_URL}/filter.aspx"
PLACEHOLDER_OPTION = "----------"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_CONCURRENCY = 10
