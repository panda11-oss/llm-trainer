import requests

def get_devto_articles(tag: str = "python", count: int = 20) -> list:
    """Dev.toのAPIから記事を取得する"""
    url = "https://dev.to/api/articles"
    params = {
        "tag": tag,
        "per_page": count,
        "top": 1,
    }
    
    res = requests.get(url, params=params, timeout=10)
    if res.status_code != 200:
        raise Exception(f"Dev.to API error: {res.status_code}")
    
    items = res.json()
    return [
        {
            "title": item["title"],
            "url": item["url"],
            "description": item.get("description", "")[:200],
            "tags": item.get("tag_list", []),
            "reactions": item.get("positive_reactions_count", 0),
            "created_at": item.get("published_at", ""),
        }
        for item in items
    ]