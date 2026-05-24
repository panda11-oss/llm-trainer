import requests
import os

QIITA_TOKEN = os.getenv("QIITA_TOKEN")

def get_qiita_articles(tag: str = "python", per_page: int = 20) -> list:
    """Qiitaの記事を取得する"""
    headers = {"Content-Type": "application/json"}
    if QIITA_TOKEN:
        headers["Authorization"] = f"Bearer {QIITA_TOKEN}"
    
    url = "https://qiita.com/api/v2/items"
    params = {
        "query": f"tag:{tag}",
        "per_page": per_page,
    }
    
    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        raise Exception(f"Qiita API error: {res.status_code}")
    
    items = res.json()
    return [
        {
            "title": item["title"],
            "url": item["url"],
            "description": item.get("body", "")[:200],
            "tags": [t["name"] for t in item.get("tags", [])],
            "likes": item.get("likes_count", 0),
            "created_at": item.get("created_at", ""),
        }
        for item in items
    ]