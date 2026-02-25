"""Fetch and normalize latest papers from journal RSS feeds."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List

import feedparser

from utils import is_within_last_7days, log

RSS_SOURCES: Dict[str, str] = {
    "Journal of the American Chemical Society": "https://pubs.acs.org/action/showFeed?type=etoc&feed=rss&jc=jacsat",
    "ACS Catalysis": "https://pubs.acs.org/action/showFeed?type=etoc&feed=rss&jc=accacs",
    "Organic Letters": "https://pubs.acs.org/action/showFeed?type=etoc&feed=rss&jc=orlef7",
    "The Journal of Organic Chemistry": "https://pubs.acs.org/action/showFeed?type=etoc&feed=rss&jc=joceah",
    "Accounts of Chemical Research": "https://pubs.acs.org/action/showFeed?type=etoc&feed=rss&jc=achre4",
    "ACS Bio & Med Chem Au": "https://pubs.acs.org/action/showFeed?type=etoc&feed=rss&jc=abmcb8",
    "ACS Organic & Inorganic Au": "https://pubs.acs.org/action/showFeed?type=etoc&feed=rss&jc=aoiabc",
    "Angewandte Chemie International Edition": "https://onlinelibrary.wiley.com/feed/15213773/most-recent",
    "Advanced Synthesis & Catalysis": "https://onlinelibrary.wiley.com/feed/16154169/most-recent",
    "Chemical Science": "https://pubs.rsc.org/en/journals/rsslanding?journalcode=sc",
    "Chemical Communications": "https://pubs.rsc.org/en/journals/rsslanding?journalcode=cc",
    "Organic Chemistry Frontiers": "https://pubs.rsc.org/en/journals/rsslanding?journalcode=qo",
    "Nature Chemistry": "https://www.nature.com/nchem.rss",
    "Nature Catalysis": "https://www.nature.com/natcatal.rss",
    "Nature Communications": "https://www.nature.com/ncomms.rss",
    "Nature Synthesis": "https://www.nature.com/natsynth.rss",
    "Nature Reviews Chemistry": "https://www.nature.com/natrevchem.rss",
    "Journal of Organometallic Chemistry": "https://rss.sciencedirect.com/publication/science/0022328X",
    "Tetrahedron": "https://rss.sciencedirect.com/publication/science/00404020",
    "Synthesis": "https://www.thieme-connect.com/products/ejournals/rss/synthesis",
    "Synlett": "https://www.thieme-connect.com/products/ejournals/rss/synlett",
    "Science": "https://www.science.org/action/showFeed?type=axatoc&feed=rss&jc=science",
}

ALLOWED_TYPES = ("article", "research article", "communication")
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")


def parse_datetime(entry: feedparser.FeedParserDict) -> datetime | None:
    """Parse publication datetime from RSS entry.

    Args:
        entry: RSS entry.

    Returns:
        Parsed datetime in UTC or None.
    """
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            dt = parsedate_to_datetime(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue

    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            try:
                return datetime.fromtimestamp(time.mktime(value), tz=timezone.utc)
            except (OverflowError, ValueError):
                continue
    return None


def extract_doi(entry: feedparser.FeedParserDict) -> str:
    """Extract DOI from an RSS entry.

    Args:
        entry: RSS entry.

    Returns:
        DOI string or empty string.
    """
    text_pool = [
        entry.get("id", ""),
        entry.get("link", ""),
        entry.get("title", ""),
        entry.get("summary", ""),
    ]
    for text in text_pool:
        match = DOI_PATTERN.search(text or "")
        if match:
            return match.group(0)

    for link in entry.get("links", []):
        href = link.get("href", "")
        match = DOI_PATTERN.search(href)
        if match:
            return match.group(0)

    return ""


def is_allowed_article_type(entry: feedparser.FeedParserDict) -> bool:
    """Determine whether an entry matches allowed article types.

    Args:
        entry: RSS entry.

    Returns:
        True if entry appears to be article/research article/communication.
    """
    candidates = [
        entry.get("category", ""),
        entry.get("dc_type", ""),
        " ".join(tag.get("term", "") for tag in entry.get("tags", [])),
        entry.get("title", ""),
    ]
    merged = " | ".join(candidates).lower()
    return any(item in merged for item in ALLOWED_TYPES)


def fetch_recent_articles() -> List[dict]:
    """Fetch and normalize articles from configured RSS sources.

    Returns:
        List of normalized article dictionaries.
    """
    all_articles: List[dict] = []

    for journal, url in RSS_SOURCES.items():
        try:
            log(f"Fetching RSS for {journal}")
            feed = feedparser.parse(url)
            if getattr(feed, "bozo", False):
                log(f"Warning: malformed feed for {journal}: {feed.bozo_exception}")

            for entry in feed.entries:
                published = parse_datetime(entry)
                # 使用新的 7 天判断逻辑
                if not published or not is_within_last_7days(published):
                    continue
                if not is_allowed_article_type(entry):
                    continue
                # ... 后续逻辑保持不变

                article = {
                    "journal": journal,
                    "title": (entry.get("title") or "").strip(),
                    "abstract": (entry.get("summary") or "").strip(),
                    "doi": extract_doi(entry),
                    "published_date": published.isoformat(),
                }
                if article["title"]:
                    all_articles.append(article)

        except Exception as exc:  # noqa: BLE001
            log(f"Failed to fetch {journal}: {exc}")
            continue

    return all_articles
