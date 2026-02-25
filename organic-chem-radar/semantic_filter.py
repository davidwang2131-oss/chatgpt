"""Semantic screening using DeepSeek API."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from openai import OpenAI

from utils import log

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"


class SemanticFilter:
    """Wrapper class for DeepSeek semantic screening."""

    def __init__(self) -> None:
        """Initialize DeepSeek client from environment variable."""
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set.")
        self.client = OpenAI(api_key=api_key, base_url=BASE_URL)

    def _build_prompt(self, article: Dict[str, str]) -> str:
        """更新提示词，增加类别标注"""
        return (
            "You are an expert in organic chemistry.\n"
            "Task:\n"
            "1) Classify the paper into exactly one category: 'carbene', 'methodology', or 'none'.\n"
            "   - 'carbene': Research specifically about carbene chemistry.\n"
            "   - 'methodology': General organic synthetic methodology or organometallic catalysis.\n"
            "2) If category is 'none', output: NO\n"
            "3) If related, output STRICT JSON with keys: category, title_zh, abstract_zh, recommendation\n"
            "Requirements:\n"
            "- abstract_zh: 3-5 Chinese sentences.\n"
            "- recommendation: Focus on innovation.\n\n"
            f"Journal: {article.get('journal', '')}\n"
            f"Title: {article.get('title', '')}\n"
            f"Abstract: {article.get('abstract', '')}\n"
        )

    def analyze_article(self, article: Dict[str, str], timeout: int = 60) -> Optional[Dict[str, Any]]:
        """Analyze a single article with up to 2 retries on transient failures.

        Args:
            article: Normalized article dictionary.
            timeout: API request timeout in seconds.

        Returns:
            Dict containing translated fields if relevant; otherwise None.
        """
        prompt = self._build_prompt(article)

        for attempt in range(1, 4):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL,
                    temperature=0.2,
                    timeout=timeout,
                    messages=[
                        {"role": "system", "content": "You provide concise and valid outputs."},
                        {"role": "user", "content": prompt},
                    ],
                )
                content = (response.choices[0].message.content or "").strip()

                if content.upper() == "NO":
                    return None

                parsed = json.loads(content)
                if not isinstance(parsed, dict):
                    log(f"Skipping article due to non-dict JSON output: {article.get('title', '')}")
                    return None

                for key in ("title_zh", "abstract_zh", "recommendation"):
                    if key not in parsed:
                        log(f"Skipping article due to missing key {key}: {article.get('title', '')}")
                        return None

                return {
                    "title_zh": str(parsed["title_zh"]).strip(),
                    "abstract_zh": str(parsed["abstract_zh"]).strip(),
                    "recommendation": str(parsed["recommendation"]).strip(),
                }

            except json.JSONDecodeError:
                log(f"JSON parse failed, skipping: {article.get('title', '')}")
                return None
            except Exception as exc:  # noqa: BLE001
                log(f"DeepSeek API attempt {attempt}/3 failed: {exc}")
                if attempt < 3:
                    time.sleep(2)
                else:
                    return None

        return None
