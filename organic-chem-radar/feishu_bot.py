"""Feishu card sender for organic chemistry research updates."""

from __future__ import annotations

import os
from typing import List, Dict, Any
from datetime import datetime
import requests

from utils import log


class FeishuBot:
    """封装飞书交互式卡片推送功能。"""

    def __init__(self) -> None:
        """从环境变量初始化 Webhook 地址。"""
        self.webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
        if not self.webhook_url:
            raise ValueError("FEISHU_WEBHOOK_URL is not set.")

    def build_card(self, articles: List[Dict[str, Any]], has_carbene: bool = False) -> Dict[str, Any]:
        """
        构建结构化交互式卡片 JSON。
        
        Args:
            articles: 经过筛选和翻译的文章列表。
            has_carbene: 是否包含卡宾类高价值文献，决定卡宾颜色。
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 1. 动态确定卡片主题色和标题
        # orange: 警告/高亮色（用于卡宾）；blue: 信息色（用于普通方法学）
        template_color = "orange" if has_carbene else "blue"
        header_title = "🔥 有机化学前沿雷达 (卡宾专项)" if has_carbene else "🧪 有机化学前沿雷达 (方法学)"

        elements = []

        # 2. 顶部元信息
        elements.append({
            "tag": "note",
            "content": {
                "tag": "plain_text",
                "content": f"📅 日期：{today} | 🔍 来源：JACS, Angew, RSC, Nature, Thieme 等"
            }
        })

        # 3. 如果没有文章的处理
        if not articles:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": "📍 **今日暂无符合条件的顶级文献更新。**\n*已检索所有订阅期刊 RSS 源。*"}
            })
        else:
            # 4. 遍历文章构建模块
            for idx, article in enumerate(articles, start=1):
                category = article.get("category", "none")
                badge = "【卡宾】" if category == "carbene" else "【方法学】"
                
                # 文章标题与期刊信息
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{idx}. {article.get('title_zh', '无中文标题')}**\n"
                                   f"📖 期刊：*{article.get('journal', 'N/A')}*\n"
                                   f"🔬 **推荐理由**：{article.get('recommendation', '暂无推荐理由')}"
                    }
                })

                # 摘要部分（使用引言格式区分）
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"> 📝 **摘要精选**：{article.get('abstract_zh', '无摘要内容')}"
                    }
                })

                # 原文链接按钮
                doi = article.get('doi', '')
                url = f"https://doi.org/{doi}" if doi else article.get('link', '#')
                
                elements.append({
                    "tag": "action",
                    "actions": [{
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔗 阅读原文 (DOI)"},
                        "type": "primary" if category == "carbene" else "default",
                        "url": url
                    }]
                })

                # 分隔线
                elements.append({"tag": "hr"})

        # 5. 底部版权/提醒
        if not has_carbene and articles:
            elements.append({
                "tag": "note",
                "content": {
                    "tag": "lark_md",
                    "content": "💡 *提示：今日未监测到吡啶-亚胺配体相关的卡宾转移研究，已为您优选方法学文献。*"
                }
            })

        # 组装完整卡片
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": header_title},
                "template": template_color,
            },
            "elements": elements,
        }

    def send_card(self, card_json: Dict[str, Any], timeout: int = 20) -> bool:
        """
        发送构建好的 JSON 卡片到飞书。
        """
        payload = {
            "msg_type": "interactive",
            "card": card_json,
        }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            ok = data.get("code") == 0
            if not ok:
                log(f"Feishu API Error: {data}")
            return ok
        except requests.RequestException as exc:
            log(f"Failed to push Feishu card: {exc}")
            return False
