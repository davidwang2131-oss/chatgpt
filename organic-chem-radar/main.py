"""Entrypoint for Organic Chemistry Daily Radar pipeline."""

from __future__ import annotations

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

    # 1. 获取最近文献（受 journal_fetcher.py 中的日期范围控制）
    try:
        raw_articles = fetch_recent_articles()
    except Exception as exc:
        log(f"Failed to fetch articles: {exc}")
        raw_articles = []

    # 2. DOI 去重
    candidates = deduplicate_by_doi(raw_articles)
    log(f"Fetched {len(raw_articles)} items, {len(candidates)} after deduplication.")

    # 3. 加载历史推送记录，用于跨天去重
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
                # 使用 DeepSeek 进行分类（需配合修改后的 semantic_filter.py）
                result = screener.analyze_article(article, timeout=60)
                if not result:
                    continue
                
                merged = {**article, **result}
                category = result.get("category", "none")
                
                # 分别存储卡宾类和通用方法学类文献
                if category == "carbene":
                    carbene_papers.append(merged)
                elif category == "methodology":
                    methodology_papers.append(merged)
                
                # 如果方法学文献已找齐且卡宾文献已搜寻足够，可提前结束以节省 API
                if len(methodology_papers) >= 10 and len(carbene_papers) >= 5:
                    break

            except Exception as exc:
                log(f"Skip article due to screening failure: {exc}")
                continue

    # 5. 组合最终推送列表：全部最新卡宾文献 + 最多 3 篇有机方法学文献
    final_selection = carbene_papers + methodology_papers[:MAX_METHODOLOGY]
    has_carbene = len(carbene_papers) > 0

    # 6. 推送到飞书
    try:
        bot = FeishuBot()
        # 将 has_carbene 状态传入，以便在无卡宾文献时进行提醒
        markdown = bot.build_markdown(final_selection, has_carbene=has_carbene)
        success = bot.send_markdown(markdown, timeout=20)
        
        if success:
            log(f"Pushed {len(final_selection)} articles to Feishu (Carbene: {len(carbene_papers)}, Methodology: {min(len(methodology_papers), MAX_METHODOLOGY)}).")
            # 更新已推送记录
            for item in final_selection:
                doi = (item.get("doi") or "").strip().lower()
                if doi:
                    pushed_dois.add(doi)
            save_pushed_dois(pushed_dois, DOI_STORE)
        else:
            log("Feishu push failed.")
    except Exception as exc:
        log(f"Unexpected push error: {exc}")

    log("Daily radar finished.")


if __name__ == "__main__":
    run()
