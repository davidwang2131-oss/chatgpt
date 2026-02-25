"""Utility helpers for the Organic Chemistry Daily Radar project."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Set


def log(message: str) -> None:
    """Print a timestamped log line.

    Args:
        message: Message to print.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now}] {message}")


def is_within_last_7days(published: datetime) -> bool:
    """检查日期是否在过去 7 天内。

    Args:
        published: 出版日期。

    Returns:
        如果在过去 7 天内则返回 True，否则返回 False。
    """
    now = datetime.now(timezone.utc)
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    # 将 timedelta(hours=24) 修改为 timedelta(days=7)
    return now - timedelta(days=7) <= published <= now


def deduplicate_by_doi(items: Iterable[dict]) -> List[dict]:
    """Remove duplicated items by DOI.

    Args:
        items: Iterable of article dicts.

    Returns:
        List with unique DOI entries. Empty DOI values are kept once per title.
    """
    seen: Set[str] = set()
    unique_items: List[dict] = []

    for item in items:
        doi = (item.get("doi") or "").strip().lower()
        fallback = (item.get("title") or "").strip().lower()
        key = doi or f"title::{fallback}"
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)

    return unique_items


def load_pushed_dois(path: str = "pushed_dois.json") -> Set[str]:
    """Load pushed DOI set from local JSON file.

    Args:
        path: Path to JSON storage file.

    Returns:
        Set of DOI strings in lower-case.
    """
    file_path = Path(path)
    if not file_path.exists():
        return set()

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return set()
        return {str(x).strip().lower() for x in data if str(x).strip()}
    except (json.JSONDecodeError, OSError):
        return set()


def save_pushed_dois(dois: Iterable[str], path: str = "pushed_dois.json") -> None:
    """Persist pushed DOI set to local JSON file.

    Args:
        dois: DOI iterable.
        path: Path to JSON storage file.
    """
    normalized = sorted({d.strip().lower() for d in dois if d and d.strip()})
    file_path = Path(path)
    file_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
