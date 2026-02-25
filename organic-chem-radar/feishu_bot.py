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

    def build_markdown(self, articles: List[dict], has_carbene: bool = True) -> str:
        """按照要求格式化输出，并增加卡宾检索结果提醒"""
        lines = ["## Organic Chemistry Daily Radar"]
        
        # 状态提醒：如果没有卡宾文献，在开头明确说明
        if not has_carbene:
            lines.append("> 📢 **今日雷达监测结果：未发现最新的卡宾相关文献。**\n")
        
        if not articles:
            return "\n".join(lines) + "今日无符合条件的论文推荐。"

        for idx, article in enumerate(articles, start=1):
            # 严格按照要求的 7 项信息进行排列
            lines.extend([
                f"### {idx}. {article.get('title_zh', '无中文标题')}",
                f"- **英文题目**：{article.get('title', 'N/A')}",
                f"- **中文题目**：{article.get('title_zh', 'N/A')}",
                f"- **DOI**：[{article.get('doi', 'N/A')}](https://doi.org/{article.get('doi', '')})",
                f"- **发表日期**：{article.get('published_date', 'N/A')}",
                f"- **发表期刊**：{article.get('journal', 'N/A')}",
                "\n**中文摘要**",
                f"{article.get('abstract_zh', '无摘要')}",
                "\n**推荐理由**",
                f"{article.get('recommendation', '无理由')}",
                "\n---"
            ])

        return "\n".join(lines)

    def send_markdown(self, markdown_text: str, timeout: int = 20) -> bool:
        """Send markdown message to Feishu using interactive card format.

        Args:
            markdown_text: Markdown body to send.
            timeout: Request timeout seconds.

        Returns:
            True if request succeeds with Feishu success code.
        """
        # 修复之前使用 post 类型导致不支持 md 标签的问题
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "Organic Chemistry Daily Radar"},
                    "template": "orange",
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": markdown_text,
                    }
                ],
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
