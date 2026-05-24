import requests
import xml.etree.ElementTree as ET

def get_zenn_articles(topic: str = "python", count: int = 20) -> list:
    url = f"https://zenn.dev/topics/{topic}/feed"
    
    res = requests.get(url, timeout=10)
    if res.status_code != 200:
        raise Exception(f"Zenn RSS error: {res.status_code}")
    
    root = ET.fromstring(res.content)
    channel = root.find("channel")
    if channel is None:
        return []
    
    articles = []
    for item in channel.findall("item")[:count]:
        title = item.find("title")
        link = item.find("link")
        description = item.find("description")
        pub_date = item.find("pubDate")
        
        articles.append({
            "title": title.text if title is not None else "",
            "url": link.text if link is not None else "",
            "description": (description.text or "")[:200] if description is not None else "",
            "created_at": pub_date.text if pub_date is not None else "",
        })
    
    return articles