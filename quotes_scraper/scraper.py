from __future__ import annotations

import argparse
import asyncio
from collections.abc import Iterable
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup

from quotes_scraper.config import (
    BASE_URL,
    DEFAULT_CONCURRENCY,
    DEFAULT_TIMEOUT_SECONDS,
    FILTER_URL,
    PLACEHOLDER_OPTION,
    SEARCH_URL,
)
from quotes_scraper.models import QuoteRecord
from quotes_scraper.writers import write_csv, write_json


class QuotesScraper:
    def __init__(
        self,
        delay_seconds: float = 0.0,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> None:
        self.delay_seconds = delay_seconds
        self.timeout = timeout
        self.concurrency = concurrency
        self._semaphore = asyncio.Semaphore(concurrency)

    async def scrape(self) -> list[QuoteRecord]:
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        headers = {"User-Agent": "quotes-scraper/2.0"}

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            search_page = await self._get_soup(session, SEARCH_URL)
            authors = self._parse_select_options(search_page, "author")
            initial_viewstate = self._extract_viewstate(search_page)

            aggregated: dict[tuple[str, str], set[str]] = {}

            author_pages = await asyncio.gather(
                *[
                    self._fetch_author_page(session, author=author, viewstate=initial_viewstate)
                    for author in authors
                ]
            )

            result_pages = await asyncio.gather(
                *[
                    self._fetch_tag_results(
                        session,
                        author=author,
                        author_page=author_page,
                    )
                    for author, author_page in author_pages
                ]
            )

            for author_results in result_pages:
                for quote_text, quote_author, quote_tags in author_results:
                    aggregated.setdefault((quote_author, quote_text), set()).update(quote_tags)

            for quote_text, quote_author, quote_tags in await self._scrape_paginated_quotes(session):
                aggregated.setdefault((quote_author, quote_text), set()).update(quote_tags)

        records = [
            QuoteRecord(quote=text, author=author, tags=tuple(sorted(tags)))
            for (author, text), tags in aggregated.items()
        ]
        records.sort(key=lambda item: (item.author.casefold(), item.quote.casefold()))
        return records

    async def _fetch_author_page(
        self,
        session: aiohttp.ClientSession,
        *,
        author: str,
        viewstate: str,
    ) -> tuple[str, BeautifulSoup]:
        # Each author page reveals the tags that are actually valid for that
        # author, which keeps the next request batch smaller and cleaner.
        soup = await self._post_filter(
            session,
            author=author,
            tag=PLACEHOLDER_OPTION,
            viewstate=viewstate,
            submit=False,
        )
        return author, soup

    async def _fetch_tag_results(
        self,
        session: aiohttp.ClientSession,
        *,
        author: str,
        author_page: BeautifulSoup,
    ) -> list[tuple[str, str, tuple[str, ...]]]:
        author_viewstate = self._extract_viewstate(author_page)
        tags = self._parse_select_options(author_page, "tag")
        tag_pages = await asyncio.gather(
            *[
                self._post_filter(
                    session,
                    author=author,
                    tag=tag,
                    viewstate=author_viewstate,
                    submit=True,
                )
                for tag in tags
            ]
        )

        parsed_results: list[tuple[str, str, tuple[str, ...]]] = []
        for tag_page in tag_pages:
            for quote_text, quote_author, quote_tag in self._parse_search_results(tag_page):
                parsed_results.append((quote_text, quote_author, (quote_tag,)))
        return parsed_results

    async def _get_soup(self, session: aiohttp.ClientSession, url: str) -> BeautifulSoup:
        async with self._semaphore:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
            await self._sleep()
            return BeautifulSoup(html, "html.parser")

    async def _post_filter(
        self,
        session: aiohttp.ClientSession,
        *,
        author: str,
        tag: str,
        viewstate: str,
        submit: bool,
    ) -> BeautifulSoup:
        payload = {
            "author": author,
            "tag": tag,
            "__VIEWSTATE": viewstate,
        }
        if submit:
            payload["submit_button"] = "Search"

        async with self._semaphore:
            async with session.post(FILTER_URL, data=payload) as response:
                response.raise_for_status()
                html = await response.text()
            await self._sleep()
            return BeautifulSoup(html, "html.parser")

    async def _scrape_paginated_quotes(
        self,
        session: aiohttp.ClientSession,
    ) -> list[tuple[str, str, tuple[str, ...]]]:
        # The search flow currently misses a few untagged quotes, so this pass
        # ensures the final dataset really contains every quote on the site.
        next_url = BASE_URL
        records: list[tuple[str, str, tuple[str, ...]]] = []

        while next_url:
            soup = await self._get_soup(session, next_url)
            for quote_block in soup.select("div.quote"):
                content = quote_block.select_one("span.text")
                author = quote_block.select_one("small.author")
                tags = tuple(sorted(tag.get_text(strip=True) for tag in quote_block.select("div.tags a.tag")))
                if not content or not author:
                    continue
                records.append((content.get_text(strip=True), author.get_text(strip=True), tags))

            next_link = soup.select_one("li.next a")
            next_url = f"{BASE_URL}{next_link['href']}" if next_link and next_link.get("href") else ""

        return records

    @staticmethod
    def _extract_viewstate(soup: BeautifulSoup) -> str:
        field = soup.select_one("input[name='__VIEWSTATE']")
        if field is None or not field.get("value"):
            raise ValueError("Could not find __VIEWSTATE field on the page.")
        return field["value"]

    @staticmethod
    def _parse_select_options(soup: BeautifulSoup, field_name: str) -> list[str]:
        select = soup.select_one(f"select[name='{field_name}']")
        if select is None:
            raise ValueError(f"Could not find select field '{field_name}'.")

        values: list[str] = []
        for option in select.select("option"):
            value = (option.get("value") or option.get_text(strip=True)).strip()
            if value and value != PLACEHOLDER_OPTION:
                values.append(value)
        return values

    @staticmethod
    def _parse_search_results(soup: BeautifulSoup) -> Iterable[tuple[str, str, str]]:
        for quote_block in soup.select("div.results div.quote"):
            content = quote_block.select_one("span.content")
            author = quote_block.select_one("span.author")
            tag = quote_block.select_one("span.tag")
            if not content or not author or not tag:
                continue
            yield content.get_text(strip=True), author.get_text(strip=True), tag.get_text(strip=True)

    async def _sleep(self) -> None:
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape all quotes from quotes.toscrape.com/search.aspx.")
    parser.add_argument("--output", default="output/quotes.json", help="Path to the output file.")
    parser.add_argument("--format", choices=("json", "csv"), default="json", help="Output format.")
    parser.add_argument("--delay-seconds", type=float, default=0.0, help="Optional delay between requests.")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Concurrent request limit.")
    return parser


async def async_main() -> int:
    args = build_parser().parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scraper = QuotesScraper(
        delay_seconds=args.delay_seconds,
        concurrency=args.concurrency,
    )
    records = await scraper.scrape()

    if args.format == "json":
        write_json(records, output_path)
    else:
        write_csv(records, output_path)

    print(f"Wrote {len(records)} quotes to {output_path}")
    return 0


def main() -> int:
    # `asyncio.run` gives us a normal CLI entrypoint while keeping the scraper
    # itself fully asynchronous and easy to reuse from other modules.
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
