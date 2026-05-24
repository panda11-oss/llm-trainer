import chromadb
import os

# ChromaDBの初期化
client = chromadb.PersistentClient(path="/app/data/chromadb")

def get_collection(name: str):
    """コレクションを取得または作成する"""
    return client.get_or_create_collection(name=name)

def save_articles(source: str, articles: list) -> int:
    """記事をDBに保存する"""
    collection = get_collection(source)
    
    if not articles:
        return 0
    
    ids = []
    documents = []
    metadatas = []
    
    for i, article in enumerate(articles):
        doc_id = f"{source}_{i}_{hash(article.get('url', '') + article.get('title', ''))}"
        ids.append(str(abs(hash(doc_id))))
        documents.append(f"{article.get('title', '')} {article.get('description', '')}")
        metadatas.append({
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "source": source,
            "created_at": str(article.get("created_at", "")),
        })
    
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )
    
    return len(articles)

def get_stats() -> dict:
    """各コレクションの統計を返す"""
    stats = {}
    collections = client.list_collections()
    for col in collections:
        stats[col.name] = col.count()
    return stats

def search(query: str, source: str = None, n_results: int = 10) -> list:
    """ベクトル検索を行う"""
    if source:
        collection = get_collection(source)
        results = collection.query(query_texts=[query], n_results=n_results)
    else:
        all_results = []
        for col in client.list_collections():
            try:
                results = col.query(query_texts=[query], n_results=3)
                if results["metadatas"]:
                    all_results.extend(results["metadatas"][0])
            except:
                pass
        return all_results
    
    if results["metadatas"]:
        return results["metadatas"][0]
    return []