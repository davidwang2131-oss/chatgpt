"""Entrypoint for Organic Chemistry Daily Radar pipeline."""

from __future__ import annotations

from dotenv import load_dotenv

from feishu_bot import FeishuBot
from journal_fetcher import fetch_recent_articles
from semantic_filter import SemanticFilter
from utils import deduplicate_by_doi, load_pushed_dois, log, save_pushed_dois

MAX_PUSH_ITEMS = 10
DOI_STORE = "pushed_dois.json"


def run() -> None:
    """Execute end-to-end daily workflow with fault tolerance."""
    load_dotenv()
    log("Daily radar started.")

    try:
        raw_articles = fetch_recent_articles()
    except Exception as exc:  # noqa: BLE001
        log(f"Failed to fetch articles: {exc}")
        raw_articles = []

    candidates = deduplicate_by_doi(raw_articles)
    log(f"Fetched {len(raw_articles)} items, {len(candidates)} after deduplication.")

    pushed_dois = load_pushed_dois(DOI_STORE)
    filtered_articles = []

    try:
        screener = SemanticFilter()
    except Exception as exc:  # noqa: BLE001
        log(f"Semantic filter init failed: {exc}")
        screener = None

    if screener is not None:
        for article in candidates:
            doi = (article.get("doi") or "").strip().lower()
            if doi and doi in pushed_dois:
                continue

            try:
                result = screener.analyze_article(article, timeout=60)
                if not result:
                    continue
                merged = {**article, **result}
                filtered_articles.append(merged)
                if len(filtered_articles) >= MAX_PUSH_ITEMS:
                    break
            except Exception as exc:  # noqa: BLE001
                log(f"Skip article due to screening failure: {exc}")
                continue

    try:
        bot = FeishuBot()
        markdown = bot.build_markdown(filtered_articles)
        success = bot.send_markdown(markdown, timeout=20)
        if success:
            log(f"Pushed {len(filtered_articles)} articles to Feishu.")
            for item in filtered_articles:
                doi = (item.get("doi") or "").strip().lower()
                if doi:
                    pushed_dois.add(doi)
            save_pushed_dois(pushed_dois, DOI_STORE)
        else:
            log("Feishu push failed.")
    except Exception as exc:  # noqa: BLE001
        log(f"Unexpected push error: {exc}")

    log("Daily radar finished.")


if __name__ == "__main__":
    run()
