import os
import requests

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")


def search_serper(keyword: str, num: int = 10) -> list[dict]:
    """
    Serper API でキーワード検索し、上位サイトの情報を返す。
    各結果のスニペット・タイトル・URLを収集する。
    """
    if not SERPER_API_KEY:
        print("[Serper] SERPER_API_KEY が未設定のためスキップ")
        return []

    try:
        res = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json",
            },
            json={"q": keyword, "num": num},
            timeout=10,
        )
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"[Serper] 検索エラー: {e}")
        return []

    results = []
    for item in data.get("organic", []):
        title   = item.get("title", "")
        url     = item.get("link", "")
        snippet = item.get("snippet", "")

        if not url:
            continue

        # ページ本文を取得（失敗してもスニペットだけで保存）
        content = fetch_page_content(url) or snippet

        results.append({
            "title":   title,
            "url":     url,
            "content": content,
            "tags":    [keyword],
        })

    print(f"[Serper] '{keyword}' → {len(results)}件取得")
    return results


def fetch_page_content(url: str, timeout: int = 10) -> str | None:
    """URLのページ本文をプレーンテキストで取得する（失敗時はNone）"""
    try:
        res = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; llm-trainer/1.0)"},
            timeout=timeout,
        )
        res.raise_for_status()

        # BeautifulSoupがあれば本文抽出、なければraw text
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, "html.parser")
            # script/styleを除去
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            # 長すぎる場合は先頭3000文字に絞る
            return text[:3000]
        except ImportError:
            return res.text[:3000]

    except Exception as e:
        print(f"[Serper] ページ取得失敗 {url}: {e}")
        return None