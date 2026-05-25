import chromadb
import hashlib

# ChromaDB HTTPクライアント
client = chromadb.HttpClient(host="chromadb", port=8000)

def get_collection(name: str):
    """コレクションを取得または作成する"""
    return client.get_or_create_collection(name=name)

def make_id(source: str, url: str, title: str) -> str:
    """URLベースの安定したMD5ハッシュIDを生成する"""
    key = f"{source}_{url or title}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()

def save_articles(source: str, articles: list) -> int:
    """記事をDBに保存する (重複はupsertで更新)"""
    if not articles:
        return 0

    collection = get_collection(source)

    ids        = []
    documents  = []
    metadatas  = []

    for article in articles:
        url   = article.get("url", "")
        title = article.get("title", "")

        # URLベースの安定したID (同じ記事は常に同じID)
        doc_id = make_id(source, url, title)

        ids.append(doc_id)
        documents.append(f"{title} {article.get('description', '') or article.get('content', '')}")
        metadatas.append({
            "title":      title,
            "url":        url,
            "source":     source,
            "created_at": str(article.get("created_at", "")),
        })

    # upsert: 同じIDなら更新、なければ追加
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    return len(articles)

def get_stats() -> dict:
    """各コレクションの統計を返す"""
    stats = {}
    for col in client.list_collections():
        stats[col.name] = col.count()
    return stats

def search(query: str, source: str = None, n_results: int = 10) -> list:
    """ベクトル検索を行う"""
    if source:
        col     = get_collection(source)
        results = col.query(query_texts=[query], n_results=n_results)
        if results["metadatas"]:
            return results["metadatas"][0]
        return []

    # 全コレクションから検索
    all_results = []
    for col in client.list_collections():
        try:
            results = col.query(query_texts=[query], n_results=3)
            if results["metadatas"]:
                all_results.extend(results["metadatas"][0])
        except Exception:
            pass
    return all_results