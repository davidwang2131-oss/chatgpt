"""Hybrid semantic screening using Gemini Flash (Fast) and DeepSeek Reasoner (Deep)."""

from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, Optional
from openai import OpenAI
from utils import log

class SemanticFilter:
    def __init__(self) -> None:
        # 1. 初始化 Gemini 客户端 (用于 Layer 1 快速初筛)
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_client = OpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        
        # 2. 初始化 DeepSeek 客户端 (用于 Layer 2 深度精读)
        ds_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.ds_client = OpenAI(
            api_key=ds_key,
            base_url="https://api.deepseek.com"
        )

    def fast_screen(self, article: Dict[str, str]) -> bool:
        """
        Layer 1: Gemini 3 Flash 初筛。
        目标：极速判定是否属于广义卡宾化学或高质量合成方法学。
        """
        prompt = (
            "Task: Decide if this chemistry paper is relevant (YES/NO).\n"
            "Criteria:\n"
            "1. Carbene Chemistry: Diazo, Sulfonylhydrazone, Ylides, NHCs, Cyclopropanation, Insertion, etc.\n"
            "2. Advanced Synthesis: New ligands, catalysis, C-H activation, or methodology.\n"
            "Exclude: Polymers, materials, bio-testing, or routine total synthesis.\n\n"
            f"Title: {article.get('title', '')}\n"
            f"Abstract: {article.get('abstract', '')[:500]}\n"
            "Output ONLY 'YES' or 'NO'."
        )
        try:
            response = self.gemini_client.chat.completions.create(
                model="gemini-3.0-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                timeout=10
            )
            return "YES" in response.choices[0].message.content.upper()
        except Exception as e:
            log(f"Gemini fast screen failed: {e}")
            return True # 容错处理：如果初筛失败，保留该文章进入精筛

    def analyze_article(self, article: Dict[str, str], timeout: int = 60) -> Optional[Dict[str, Any]]:
        """
        Layer 2: DeepSeek-R1 (Reasoner) 深度精读。
        目标：进行逻辑推导并生成中文研报内容。
        """
        # 这里的 Prompt 聚焦于广义卡宾化学进展
        prompt = (
            "You are a PhD in Organic Chemistry. Analyze this paper's innovation.\n"
            "Focus: Carbene transfer, reactive intermediates ($Metal-Carbene$), and catalytic cycles.\n"
            "Task: Output STRICT JSON with keys: category, title_zh, abstract_zh, recommendation.\n"
            "Category must be 'carbene' or 'methodology'.\n\n"
            f"Title: {article.get('title', '')}\n"
            f"Abstract: {article.get('abstract', '')}\n"
        )
        
        for attempt in range(1, 3):
            try:
                response = self.ds_client.chat.completions.create(
                    model="deepseek-reasoner",
                    messages=[{"role": "user", "content": prompt}],
                    timeout=timeout
                )
                content = (response.choices[0].message.content or "").strip()
                # 提取 JSON (DeepSeek R1 有时会在思考后包裹 markdown 代码块)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                
                parsed = json.loads(content)
                return {
                    "category": str(parsed.get("category", "none")).strip(),
                    "title_zh": str(parsed.get("title_zh", "")).strip(),
                    "abstract_zh": str(parsed.get("abstract_zh", "")).strip(),
                    "recommendation": str(parsed.get("recommendation", "")).strip(),
                }
            except Exception as e:
                log(f"DeepSeek deep reason failed (Attempt {attempt}): {e}")
                time.sleep(2)
        return None
