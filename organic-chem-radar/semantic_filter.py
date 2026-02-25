"""Hybrid semantic screening: Focused on Non-Diazo Carbene Precursors."""

from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, Optional
from openai import OpenAI
from utils import log

class SemanticFilter:
    def __init__(self) -> None:
        # Layer 1: Gemini 3 Flash (快速初筛 - 极速过滤海量文献)
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_client = OpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        
        # Layer 2: DeepSeek Reasoner (深度推理 - 分析机理与创新)
        ds_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.ds_client = OpenAI(
            api_key=ds_key,
            base_url="https://api.deepseek.com"
        )

    def fast_screen(self, article: Dict[str, str]) -> bool:
        """
        Layer 1: Gemini 3 Flash 初筛。
        核心：锁定非重氮前体，剔除 NHC。
        """
        prompt = (
            "Task: Identify if this paper is about 'Non-Diazo Carbene Chemistry' (YES/NO).\n"
            "Include if it generates carbenes from:\n"
            "1. Aldehydes or Ketones (e.g., via specialized catalytic cycles).\n"
            "2. Gem-dihalides (偕二卤代物) or Polyhalomethanes.\n"
            "3. Sulfur Ylides, Selenium Ylides, or other non-diazo reactive species.\n"
            "4. Carbene reactions: Cyclopropanation, X-H insertion, coupling, etc.\n\n"
            "Exclude (STRICTLY IGNORE):\n"
            "1. N-heterocyclic carbenes (NHCs) as catalysts or ligands.\n"
            "2. Traditional diazo compounds or sulfonylhydrazones unless used in a highly unusual way.\n"
            "3. Polymerization, materials, or routine synthesis.\n\n"
            f"Title: {article.get('title', '')}\n"
            f"Abstract: {article.get('abstract', '')[:600]}\n"
            "Respond ONLY with 'YES' or 'NO'."
        )
        try:
            response = self.gemini_client.chat.completions.create(
                model="gemini-3.0-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                timeout=12
            )
            return "YES" in response.choices[0].message.content.upper()
        except Exception as e:
            log(f"Gemini screening error: {e}")
            return True

    def analyze_article(self, article: Dict[str, str], timeout: int = 60) -> Optional[Dict[str, Any]]:
        """
        Layer 2: DeepSeek-R1 深度专家分析。
        关注非重氮路径的机理突破。
        """
        prompt = (
            "You are a PhD in Organic Chemistry. Analyze this carbene chemistry paper.\n"
            "### Strict Focus:\n"
            "- Precursor Innovation: Evaluate how carbenes are generated from Aldehydes, Ketones, or Gem-dihalides.\n"
            "- Reaction Type: ANY carbene transfer (not limited to X-H insertion).\n"
            "- Catalyst: Role of the metal/ligand in stabilizing these unique intermediates.\n"
            "- EXCLUDE NHC catalysis.\n\n"
            "### Output (STRICT JSON):\n"
            "{\n"
            "  \"category\": \"carbene\" | \"methodology\",\n"
            "  \"title_zh\": \"Professional Chinese title\",\n"
            "  \"abstract_zh\": \"3 sentences summarizing the non-diazo precursor path and mechanism\",\n"
            "  \"recommendation\": \"Professional insight on the novelty of using this specific precursor over traditional diazo reagents\"\n"
            "}\n\n"
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
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                
                parsed = json.loads(content)
                return {
                    "category": str(parsed.get("category", "none")).lower(),
                    "title_zh": str(parsed.get("title_zh", "无标题")).strip(),
                    "abstract_zh": str(parsed.get("abstract_zh", "无摘要内容")).strip(),
                    "recommendation": str(parsed.get("recommendation", "无点评")).strip(),
                }
            except Exception as e:
                log(f"DeepSeek Reasoning failed: {e}")
                time.sleep(2)
        return None
