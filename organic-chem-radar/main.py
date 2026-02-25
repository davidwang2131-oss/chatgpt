"""Entrypoint for Organic Chemistry Daily Radar pipeline."""

from __future__ import annotations
import os
from dotenv import load_dotenv

from feishu_bot import FeishuBot
from journal_fetcher import fetch_recent_articles 
from semantic_filter import SemanticFilter
from utils import deduplicate_by_doi, load_pushed_dois, log, save_pushed_dois

# 存储已推送 DOI 的文件
DOI_STORE = "pushed_dois.json"
# 每日推荐的有机方法学文献上限
MAX_METHODOLOGY = 3

def run() -> None:
    """执行端到端的每日雷达工作流。"""
    load_dotenv()
    log("Daily radar started.")

    # 1. 获取最近文献（建议确保 journal_fetcher.py 已更新为 bs4+lxml 版本）
    try:
        raw_articles = fetch_recent_articles()
    except Exception as exc:
        log(f"CRITICAL ERROR: Failed to fetch articles: {exc}")
        raw_articles = []

    if not raw_articles:
        log("No articles fetched. Checking journal_fetcher logic or network.")
        # 这里可以选择是否给飞书发心跳包，保持沉默通常更适合这种自动化脚本

    # 2. DOI 去重
    candidates = deduplicate_by_doi(raw_articles)
    log(f"Fetched {len(raw_articles)} items, {len(candidates)} after deduplication.")

    # 3. 加载历史推送记录
    pushed_dois = load_pushed_dois(DOI_STORE)
    
    carbene_papers = []
    methodology_papers = []

    try:
        screener = SemanticFilter()
    except Exception as exc:
        log(f"Semantic filter init failed: {exc}")
        screener = None

    # 4. 语义筛选与分类
    if screener is not None:
        for article in candidates:
            doi = (article.get("doi") or "").strip().lower()
            if doi and doi in pushed_dois:
                continue

            try:
                if not article.get("title"):
                    continue
                    
                # 使用 deepseek-reasoner 进行深度分析
                result = screener.analyze_article(article, timeout=60)
                if not result:
                    continue
                
                # 合并原文数据与 AI 分析结果
                merged = {**article, **result}
                # result 字典中现在包含 category 字段
                category = result.get("category", "none")
                
                if category == "carbene":
                    carbene_papers.append(merged)
                elif category == "methodology":
                    methodology_papers.append(merged)
                
                # 提前终止逻辑：如果两类文献都搜集够了，停止调用 API 以节省成本
                if len(methodology_papers) >= 10 and len(carbene_papers) >= 5:
                    break

            except Exception as exc:
                log(f"Screening failed for {article.get('title', 'Unknown')}: {exc}")
                continue

    # 5. 组合最终推送列表
    final_selection = carbene_papers + methodology_papers[:MAX_METHODOLOGY]
    has_carbene = len(carbene_papers) > 0

    # 6. 推送到飞书（改为发送交互式卡片）
    try:
        bot = FeishuBot()
        
        # --- 核心改动点 ---
        # 1. 调用新的 build_card 方法构建 JSON 结构
        card_payload = bot.build_card(final_selection, has_carbene=has_carbene)
        
        #
