import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from utils import log

def clean_xml_content(raw_content: str) -> str:
    """
    清洗 XML 字符串，剔除导致 'invalid token' 报错的低位非打印字符。
    这是处理化学期刊 RSS 中特殊符号的关键。
    """
    if not raw_content:
        return ""
    # 仅保留合法的 XML 字符范围
    illegal_chars = re.compile(
        r'[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\xFF\u0100-\uD7FF\uE000-\uFDCF\uFDE0-\uFFFD]'
    )
    return illegal_chars.sub('', raw_content)

def robust_fetch_rss(url: str, journal_name: str) -> list[dict]:
    """
    使用 lxml 引擎强力解析 RSS/Atom 源。
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    articles = []
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 1. 预处理内容
        content = clean_xml_content(response.text)
        
        # 2. 解析 (使用 lxml-xml 模式，具备强大的容错恢复能力)
        soup = BeautifulSoup(content, 'xml')
        
        # 3. 兼容多种标签格式 (RSS 的 item 或 Atom 的 entry)
        items = soup.find_all(['item', 'entry'])
        
        for item in items:
            title = item.find('title').get_text(strip=True) if item.find('title') else "No Title"
            
            # 获取链接
            link = ""
            link_tag = item.find('link')
            if link_tag:
                link = link_tag.get_text(strip=True) or link_tag.get('href', "")
            
            # 获取摘要
            abstract = ""
            abstract_tag = item.find(['description', 'summary', 'content'])
            if abstract_tag:
                abstract = abstract_tag.get_text(strip=True)
            
            # 提取 DOI (尝试从 dc:identifier, prism:doi 或 link 中提取)
            doi = ""
            doi_tag = item.find(['dc:identifier', 'prism:doi', 'doi'])
            if doi_tag:
                doi = doi_tag.get_text(strip=True)
            elif "doi.org/" in link:
                doi = link.split("doi.org/")[-1].split("?")[0]
            
            articles.append({
                "title": title,
                "link": link,
                "doi": doi.lower(), # 统一小写方便去重
                "journal": journal_name,
                "abstract": abstract,
                "fetch_time": datetime.now().strftime("%Y-%m-%d")
            })
            
    except Exception as e:
        log(f"Warning: Failed to fetch {journal_name} from {url}. Error: {e}")
        
    return articles

def fetch_recent_articles() -> list[dict]:
    """
    获取所有配置期刊的最新文献。
    """
    # 建议将你的期刊列表整理如下
    journal_configs = [
        {"name": "JACS", "url": "https://pubs.acs.org/journal/jacsat/feed"},
        {"name": "ACS Catalysis", "url": "https://pubs.acs.org/journal/accacs/feed"},
        {"name": "Organic Letters", "url": "https://pubs.acs.org/journal/orlef7/feed"},
        {"name": "JOC", "url": "https://pubs.acs.org/journal/joceah/feed"},
        {"name": "Angewandte", "url": "https://onlinelibrary.wiley.com/feed/15213773/most-recent"},
        {"name": "Chemical Science", "url": "https://www.rsc.org/publishing/journals/sc/rss.asp"},
        {"name": "ChemComm", "url": "https://www.rsc.org/publishing/journals/cc/rss.asp"},
        {"name": "Org. Chem. Front.", "url": "https://www.rsc.org/publishing/journals/qo/rss.asp"},
        {"name": "Nature Chemistry", "url": "
