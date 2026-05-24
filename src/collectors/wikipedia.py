import requests

def get_wikipedia_articles(topic: str = "Python", count: int = 10) -> list:
    """WikipediaのAPIから記事を取得する"""
    url = "https://ja.wikipedia.org/w/api.php"
    headers = {
        "User-Agent": "llm-trainer/1.0 (educational project)"
    }
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": topic,
        "srlimit": count,
        "srprop": "snippet",
    }
    
    res = requests.get(url, headers=headers, params=params, timeout=10)
    if res.status_code != 200:
        raise Exception(f"Wikipedia API error: {res.status_code}")
    
    items = res.json().get("query", {}).get("search", [])
    return [
        {
            "title": item["title"],
            "url": f"https://ja.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
            "description": item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")[:200],
            "created_at": item.get("timestamp", ""),
        }
        for item in items
    ]