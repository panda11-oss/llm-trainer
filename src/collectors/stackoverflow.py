import requests

def get_stackoverflow_questions(tag: str = "python", count: int = 20) -> list:
    """Stack OverflowのAPIから質問を取得する"""
    url = "https://api.stackexchange.com/2.3/questions"
    params = {
        "order": "desc",
        "sort": "activity",
        "tagged": tag,
        "site": "stackoverflow",
        "pagesize": count,
        "filter": "withbody",
    }
    
    res = requests.get(url, params=params, timeout=10)
    if res.status_code != 200:
        raise Exception(f"Stack Overflow API error: {res.status_code}")
    
    items = res.json().get("items", [])
    return [
        {
            "title": item["title"],
            "url": item["link"],
            "description": item.get("body", "")[:200],
            "score": item.get("score", 0),
            "tags": item.get("tags", []),
            "created_at": str(item.get("creation_date", "")),
        }
        for item in items
    ]