"""Feishu webhook sender for daily radar results."""

from __future__ import annotations

import os
from typing import List

import requests

from utils import log


class FeishuBot:
    """Feishu bot wrapper for markdown push messages."""

    def __init__(self) -> None:
        """Initialize webhook URL from environment variable."""
        self.webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
        if not self.webhook_url:
            raise ValueError("FEISHU_WEBHOOK_URL is not set.")

    def build_markdown(self, articles: List[dict]) -> str:
        """Build Feishu markdown message.

        Args:
            articles: List of selected paper records.

        Returns:
            Markdown content for Feishu.
        """
        if not articles:
            return "今日无符合条件的有机方法学相关论文"

        lines = ["## Organic Chemistry Daily Radar（DeepSeek）"]

        for idx, article in enumerate(articles, start=1):
            lines.extend(
                [
                    f"\n### {idx}. {article.get('journal', '')}",
                    f"- **英文标题**：{article.get('title', '')}",
                    f"- **中文标题**：{article.get('title_zh', '')}",
                    f"- **DOI**：{article.get('doi', 'N/A') or 'N/A'}",
                    f"- **发表日期**：{article.get('published_date', '')}",
                    "\n**中文摘要**",
                    article.get("abstract_zh", ""),
                    "\n**推荐理由**",
                    article.get("recommendation", ""),
                ]
            )

        return "\n".join(lines)

    def send_markdown(self, markdown_text: str, timeout: int = 20) -> bool:
        """Send markdown message to Feishu.

        Args:
            markdown_text: Markdown body to send.
            timeout: Request timeout seconds.

        Returns:
            True if request succeeds with Feishu success code.
        """
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": "Organic Chemistry Daily Radar",
                        "content": [[{"tag": "md", "text": markdown_text}]],
                    }
                }
            },
        }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            ok = data.get("code") == 0
            if not ok:
                log(f"Feishu returned non-zero code: {data}")
            return ok
        except requests.RequestException as exc:
            log(f"Failed to push Feishu message: {exc}")
            return False
