import requests

def get_manpages(commands=None):
    if commands is None:
        commands = [
            "ls", "cd", "grep", "awk", "sed", "find", "curl",
            "ssh", "git", "docker", "systemctl", "journalctl",
            "chmod", "chown", "ps", "top", "netstat", "tar",
        ]
    docs = []
    for cmd in commands:
        try:
            r = requests.get(
                f"https://man.archlinux.org/man/{cmd}.1",
                timeout=10,
            )
            if r.status_code != 200:
                continue
            # テキスト部分だけ抽出
            from html.parser import HTMLParser
            class P(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self.in_pre = False
                def handle_starttag(self, tag, attrs):
                    if tag == "pre": self.in_pre = True
                def handle_endtag(self, tag):
                    if tag == "pre": self.in_pre = False
                def handle_data(self, data):
                    if self.in_pre: self.text.append(data)
            p = P()
            p.feed(r.text)
            content = "\n".join(p.text)[:2000]
            if not content:
                continue
            docs.append({
                "title": f"man {cmd}",
                "content": content,
                "url": f"https://man.archlinux.org/man/{cmd}.1",
            })
        except Exception as e:
            print(f"manpages {cmd} エラー: {e}")
    return docs