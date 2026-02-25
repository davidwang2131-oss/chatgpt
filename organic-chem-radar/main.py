"""
Entrypoint for Organic Chemistry Daily Radar pipeline.
Architecture: Gemini 3 Flash (Layer 1 Fast Screen) -> DeepSeek R1 (Layer 2 Deep Reasoning)
"""

from __future__ import annotations
import os
from dotenv import load_dotenv

from feishu_bot import FeishuBot
from journal_fetcher import fetch_recent_articles 
from semantic_filter import SemanticFilter # 确保你已更新此文件为 Hybrid 版本
from utils import deduplicate_by_doi, load_pushed_dois, log, save_pushed_dois

# 存储已推送 DOI 的文件
DOI_STORE = "pushed_dois.json"
# 每日推送上限配置
MAX_CARBENE = 8
MAX_METHODOLOGY = 5

def run() -> None:
    """执行端到端的双层过滤每日雷达工作流。"""
    load_dotenv()
    log("Daily radar (Hybrid Mode) started.")

    # 1. 获取最近文献
    try:
        raw_articles = fetch_recent_articles()
    except Exception as exc:
        log(f"CRITICAL ERROR: Failed to fetch articles: {exc}")
        raw_articles = []

    if not raw_articles:
        log("No articles fetched. Process terminated.")
        return

    # 2. DOI 去重
    candidates = deduplicate_by_doi(raw_articles)
    log(f"Fetched {len(raw_articles)} items, {len(candidates)} after deduplication.")

    # 3. 加载历史推送记录
    pushed_dois = load_pushed_dois(DOI_STORE)
    
    carbene_papers = []
    methodology_papers = []

    try:
        # 此时的 screener 内部已封装 Gemini (Layer 1) 和 DeepSeek (Layer 2)
        screener = SemanticFilter()
    except Exception as exc:
        log(f"Filter initialization failed: {exc}")
        return

    # 4. 双层语义筛选循环
    # Layer 1 (Gemini) 毫秒级处理全量数据，Layer 2 (DeepSeek) 仅处理精华
    log("Starting two-layer screening...")
    
    for article in candidates:
        # 跳过已推送的 DOI
        doi = (article.get("doi") or "").strip().lower()
        if doi and doi in pushed_dois:
            continue

        try:
            if not article.get("title") or not article.get("abstract"):
                continue
                
            # --- Layer 1: Gemini 3 Flash 极速初筛 ---
            # 这一步会过滤掉约 90% 的无关文献（如生物、材料、常规全合成等）
            if not screener.fast_screen(article):
                continue
            
            log(f"Layer 1 passed (Gemini): {article.get('title')[:50]}...")

            # --- Layer 2: DeepSeek Reasoner 深度推理 ---
            # 仅对初筛通过的文章进行深度逻辑推演和中文翻译
            result = screener.analyze_article(article, timeout=60)
            if not result:
                continue
            
            merged = {**article, **result}
            category = result.get("category", "none")
            
            # 分类存储
            if category == "carbene":
                carbene_papers.append(merged)
            elif category == "methodology":
                methodology_papers.append(merged)
            
            # 如果抓取的卡宾文献和方法学都已经够多，可以提前结束
            if len(carbene_papers) >= MAX_CARBENE and len(methodology_papers) >= MAX_METHODOLOGY:
                log("Target quotas reached. Ending screening early.")
                break

        except Exception as exc:
            log(f"Error during screening loop: {exc}")
            continue

    # 5. 组合最终推送列表
    # 优先展示卡宾化学进展
    final_selection = carbene_papers[:MAX_CARBENE] + methodology_papers[:MAX_METHODOLOGY]
    has_carbene = len(carbene_papers) > 0

    # 6. 构建并推送飞书交互式卡片
    if not final_selection:
        log("No relevant papers found today. No message sent.")
        return

    try:
        bot = FeishuBot()
        # 构建专业研报卡片
        card_payload = bot.build_card(final_selection, has_carbene=has_carbene)
        success = bot.send_card(card_payload, timeout=20)
        
        if success:
            log(f"Successfully pushed {len(final_selection)} articles to Feishu.")
            log(f"(Carbene: {len(carbene_papers)}, Methodology: {len(methodology_papers)})")
            
            # 7. 更新 DOI 数据库
            for item in final_selection:
                doi = (item.get("doi") or "").strip().lower()
                if doi:
                    pushed_dois.add(doi)
            save_pushed_dois(pushed_dois, DOI_STORE)
        else:
            log("Feishu API push failed.")
            
    except Exception as exc:
        log(f"Final push phase error: {exc}")

    log("Daily radar workflow finished.")

if __name__ == "__main__":
    run()
