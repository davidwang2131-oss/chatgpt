"""Semantic screening using DeepSeek API."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from openai import OpenAI

from utils import log

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-reasoner"


class SemanticFilter:
    """Wrapper class for DeepSeek semantic screening."""

    def __init__(self) -> None:
        """Initialize DeepSeek client from environment variable."""
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set.")
        self.client = OpenAI(api_key=api_key, base_url=BASE_URL)

    def _build_prompt(self, article: Dict[str, str]) -> str:
        """为 deepseek-reasoner 优化的专家级化学审查 Prompt"""
        return (
            "You are a Senior Professor in Organic Chemistry specializing in Organometallic Catalysis.\n"
            "### Target Research Interests:\n"
            "1. **Carbene Chemistry (Highest Priority)**:\n"
            "   - Core: Metal-carbene mediated transformations.\n"
            "   - Precursors: Diazo compounds, N-sulfonylhydrazones, sulfur ylides, gem-dihalides, etc.\n"
            "   - Ligand Focus: Pyridine-imine (P-I) ligands, Schiff bases, α-diimines, and related bidentate N,N-ligands.\n"
            "   - Reactions: Cyclopropanation, X-H insertion (X=C, O, N, Si, S), ylide formation, and carbene cross-coupling.\n"
            "   - *Note*: Include all carbene transfer reactions, NOT limited to C-H bond insertion.\n\n"
            "2. **Organic Methodology (High Priority)**:\n"
            "   - Focus: Novel catalytic systems, asymmetric synthesis, C-H activation, and photoredox/electrocatalysis.\n"
            "   - *Exclusion*: Strictly exclude pure polymerization, material science, clinical bio-activity, or routine total synthesis.\n\n"
            "### Task:\n"
            "Analyze the provided Journal, Title, and Abstract. Classify into: 'carbene', 'methodology', or 'none'.\n"
            "1. If category is 'none', output ONLY the word 'NO'.\n"
            "2. If category is 'carbene' or 'methodology', output a VALID JSON object.\n\n"
            "### JSON Schema:\n"
            "{\n"
            "  \"category\": \"carbene\" | \"methodology\",\n"
            "  \"title_zh\": \"Professional Chinese title\",\n"
            "  \"abstract_zh\": \"3-5 concise Chinese sentences summarizing the mechanism and significance\",\n"
            "  \"recommendation\": \"Professional insight on innovation and relevance to pyridine-imine or carbene chemistry\"\n"
            "}\n\n"
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
                    "category": str(parsed.get("category", "none")).strip(), # 加上这一行
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
