import requests

def get_archwiki_articles(topics=None):
    if topics is None:
        topics = [
            "Installation guide", "Systemd", "SSH", "Docker",
            "Networking", "Pacman", "Vim", "Bash", "Git", "Linux"
        ]
    docs = []
    for topic in topics:
        try:
            r = requests.get(
                "https://wiki.archlinux.org/api.php",
                params={
                    "action": "query",
                    "titles": topic,
                    "prop": "extracts",
                    "exintro": True,
                    "explaintext": True,
                    "format": "json",
                },
                timeout=10,
            )
            pages = r.json()["query"]["pages"]
            for page in pages.values():
                if "extract" not in page or not page["extract"]:
                    continue
                docs.append({
                    "title": page["title"],
                    "content": page["extract"][:2000],
                    "url": f"https://wiki.archlinux.org/title/{page['title'].replace(' ','_')}",
                })
        except Exception as e:
            print(f"archwiki {topic} エラー: {e}")
    return docs