import requests
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_trending_repos(language: str = "python", since: str = "daily") -> list:
    """GitHubのトレンドリポジトリを取得する"""
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    url = f"https://api.github.com/search/repositories"
    params = {
        "q": f"language:{language} created:>2026-01-01",
        "sort": "stars",
        "order": "desc",
        "per_page": 30,
    }
    
    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        raise Exception(f"GitHub API error: {res.status_code}")
    
    items = res.json().get("items", [])
    return [
        {
            "title": item["full_name"],
            "url": item["html_url"],
            "description": item.get("description", ""),
            "stars": item["stargazers_count"],
            "language": item.get("language", ""),
        }
        for item in items
    ]