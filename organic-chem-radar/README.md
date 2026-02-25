# Organic Chemistry Daily Radar (DeepSeek Version)

一个基于 GitHub Actions 的自动化系统，每天北京时间 08:00（UTC 00:00）抓取期刊 RSS，使用 DeepSeek 进行语义筛选，并推送结果到飞书群。

## 功能概览

- 抓取指定高水平化学期刊 RSS
- 仅保留过去 24 小时且 Article / Research Article / Communication 类型论文
- 使用 DeepSeek API 判断目标方向：
  - Organic synthetic methodology
  - Carbene chemistry
  - Organometallic chemistry
- 自动生成中文标题、中文摘要和推荐理由
- 每天最多推送 10 篇到飞书
- 使用本地 JSON 记录已推送 DOI，减少重复推送

## 项目结构

```text
organic-chem-radar/
├── main.py
├── journal_fetcher.py
├── semantic_filter.py
├── feishu_bot.py
├── utils.py
├── requirements.txt
├── .env.example
└── .github/
    └── workflows/
        └── daily.yml
```

## 部署步骤

1. 将代码推送到 GitHub 仓库。
2. 在仓库 `Settings -> Secrets and variables -> Actions` 添加：
   - `DEEPSEEK_API_KEY`
   - `FEISHU_WEBHOOK_URL`
3. GitHub Actions 会在每天 UTC 00:00 自动执行，也可手动触发 `workflow_dispatch`。

## 本地运行

```bash
cd organic-chem-radar
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## 注意事项

- 严格使用 RSS，不使用 Selenium。
- 若部分期刊 RSS 未提供明确文章类型字段，代码会依据标签与标题进行近似过滤。
- `pushed_dois.json` 会在首次成功推送后自动生成。
