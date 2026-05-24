import requests

def get_hackernews_stories(count: int = 20) -> list:
    """HackerNewsのトップストーリーを取得する"""
    top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    
    res = requests.get(top_url, timeout=10)
    if res.status_code != 200:
        raise Exception(f"HackerNews API error: {res.status_code}")
    
    story_ids = res.json()[:count]
    
    stories = []
    for story_id in story_ids:
        story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        story_res = requests.get(story_url, timeout=10)
        if story_res.status_code == 200:
            item = story_res.json()
            if item and item.get("type") == "story":
                stories.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("text", "")[:200] if item.get("text") else "",
                    "score": item.get("score", 0),
                    "created_at": str(item.get("time", "")),
                })
    
    return stories