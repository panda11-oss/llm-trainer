import os
import json
import hashlib
import requests as req
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from src.collectors.github import get_trending_repos
from src.collectors.qiita import get_qiita_articles
from src.collectors.zenn import get_zenn_articles
from src.collectors.stackoverflow import get_stackoverflow_questions
from src.collectors.hackernews import get_hackernews_stories
from src.collectors.wikipedia import get_wikipedia_articles
from src.collectors.devto import get_devto_articles
from src.collectors.archwiki import get_archwiki_articles
from src.collectors.manpages import get_manpages
from src.db import save_articles, get_stats, search, get_collection
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from contextlib import asynccontextmanager

load_dotenv()

# ── Open WebUI 設定 ───────────────────────────────────────
OPENWEBUI_URL     = os.getenv("OPENWEBUI_URL",     "http://host.docker.internal:3000")
OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY", "")
KNOWLEDGE_ID      = os.getenv("OPENWEBUI_KNOWLEDGE_ID", "")  # 作成後に設定

scheduler = AsyncIOScheduler()

# ── Open WebUI ナレッジベース更新 ─────────────────────────
def update_openwebui_knowledge(file_path: str) -> bool:
    """エクスポートファイルをOpen WebUIのナレッジベースに送信する"""
    if not OPENWEBUI_API_KEY or not KNOWLEDGE_ID:
        print("[OpenWebUI] APIキーまたはナレッジIDが未設定のためスキップ")
        return False
    try:
        headers = {"Authorization": f"Bearer {OPENWEBUI_API_KEY}"}

        # ファイルをアップロード
        with open(file_path, "rb") as f:
            upload_res = req.post(
                f"{OPENWEBUI_URL}/api/v1/files/",
                headers=headers,
                files={"file": ("llm_trainer.txt", f, "text/plain")},
                timeout=60,
            )
        if not upload_res.ok:
            print(f"[OpenWebUI] ファイルアップロード失敗: {upload_res.text}")
            return False

        file_id = upload_res.json().get("id")

        # ナレッジベースに追加
        add_res = req.post(
            f"{OPENWEBUI_URL}/api/v1/knowledge/{KNOWLEDGE_ID}/file/add",
            headers={**headers, "Content-Type": "application/json"},
            json={"file_id": file_id},
            timeout=30,
        )
        if add_res.ok:
            print(f"[OpenWebUI] ナレッジベース更新完了 (file_id: {file_id})")
            return True
        else:
            print(f"[OpenWebUI] ナレッジベース追加失敗: {add_res.text}")
            return False
    except Exception as e:
        print(f"[OpenWebUI] 更新エラー: {e}")
        return False

# ── エクスポート処理 ──────────────────────────────────────
def do_export_all() -> str:
    """全ソースをテキストファイルにエクスポートしてパスを返す"""
    sources = [
        "github", "qiita", "zenn", "stackoverflow",
        "hackernews", "wikipedia", "devto", "archwiki", "manpages"
    ]
    lines = []
    for source in sources:
        try:
            col     = get_collection(source)
            results = col.get(include=["documents", "metadatas"])
            for doc, meta in zip(results["documents"], results["metadatas"]):
                lines.append(f"# {meta.get('title', '')}")
                lines.append(f"Source: {source}")
                lines.append(f"URL: {meta.get('url', '')}")
                lines.append(doc)
                lines.append("---")
        except Exception:
            continue

    path = "/app/data/export_all.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[Export] {path} に {len(lines)} 行を書き出しました")
    return path

# ── スケジュール収集 ──────────────────────────────────────
async def scheduled_collect():
    print(f"[{datetime.now()}] スケジュール収集開始")
    collectors = {
        "github":        get_trending_repos,
        "qiita":         get_qiita_articles,
        "zenn":          get_zenn_articles,
        "stackoverflow": get_stackoverflow_questions,
        "hackernews":    get_hackernews_stories,
        "wikipedia":     get_wikipedia_articles,
        "devto":         get_devto_articles,
        "archwiki":      get_archwiki_articles,
        "manpages":      get_manpages,
    }
    for name, collector in collectors.items():
        try:
            data = collector()
            saved = save_articles(name, data)
            print(f"[{datetime.now()}] {name}: {len(data)}件 (保存/更新: {saved}件)")
        except Exception as e:
            print(f"[{datetime.now()}] {name} エラー: {e}")

    # 収集後に自動エクスポート & Open WebUI 更新
    try:
        path = do_export_all()
        update_openwebui_knowledge(path)
    except Exception as e:
        print(f"[Export] エラー: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        scheduled_collect,
        CronTrigger(hour=9, minute=0),
        id="daily_collect",
        replace_existing=True,
    )
    scheduler.start()
    print("✅ スケジューラー起動完了", flush=True)
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ════════════════════════════════════════════════════════════
#  基本
# ════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/sources")
def get_sources():
    return {"sources": [
        {"id": 1, "name": "GitHub API",    "enabled": True},
        {"id": 2, "name": "Qiita API",     "enabled": True},
        {"id": 3, "name": "Zenn RSS",      "enabled": True},
        {"id": 4, "name": "Stack Overflow","enabled": True},
        {"id": 5, "name": "HackerNews",    "enabled": True},
        {"id": 6, "name": "Wikipedia API", "enabled": True},
        {"id": 7, "name": "Dev.to API",    "enabled": True},
        {"id": 8, "name": "Arch Wiki",     "enabled": True},
        {"id": 9, "name": "Man Pages",     "enabled": True},
    ]}

@app.get("/api/stats")
def get_db_stats():
    try:
        stats = get_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
def search_articles(q: str, source: str = None, n: int = 10):
    try:
        results = search(q, source=source, n_results=n)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ════════════════════════════════════════════════════════════
#  個別収集
# ════════════════════════════════════════════════════════════

@app.get("/api/collect/github")
def collect_github(language: str = "python", save: bool = True):
    try:
        data = get_trending_repos(language=language)
        if save:
            save_articles("github", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/qiita")
def collect_qiita(tag: str = "python", save: bool = True):
    try:
        data = get_qiita_articles(tag=tag)
        if save:
            save_articles("qiita", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/zenn")
def collect_zenn(topic: str = "python", save: bool = True):
    try:
        data = get_zenn_articles(topic=topic)
        if save:
            save_articles("zenn", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/stackoverflow")
def collect_stackoverflow(tag: str = "python", save: bool = True):
    try:
        data = get_stackoverflow_questions(tag=tag)
        if save:
            save_articles("stackoverflow", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/hackernews")
def collect_hackernews(save: bool = True):
    try:
        data = get_hackernews_stories()
        if save:
            save_articles("hackernews", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/wikipedia")
def collect_wikipedia(topic: str = "Python", save: bool = True):
    try:
        data = get_wikipedia_articles(topic=topic)
        if save:
            save_articles("wikipedia", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/devto")
def collect_devto(tag: str = "python", save: bool = True):
    try:
        data = get_devto_articles(tag=tag)
        if save:
            save_articles("devto", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/archwiki")
def collect_archwiki(save: bool = True):
    try:
        data = get_archwiki_articles()
        if save:
            save_articles("archwiki", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/manpages")
def collect_manpages(save: bool = True):
    try:
        data = get_manpages()
        if save:
            save_articles("manpages", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/collect/all")
def collect_all():
    """全ソースからデータを収集してDBに保存する"""
    results = {}
    errors  = {}
    collectors = {
        "github":        lambda: get_trending_repos(),
        "qiita":         lambda: get_qiita_articles(),
        "zenn":          lambda: get_zenn_articles(),
        "stackoverflow": lambda: get_stackoverflow_questions(),
        "hackernews":    lambda: get_hackernews_stories(),
        "wikipedia":     lambda: get_wikipedia_articles(),
        "devto":         lambda: get_devto_articles(),
        "archwiki":      lambda: get_archwiki_articles(),
        "manpages":      lambda: get_manpages(),
    }
    for name, collector in collectors.items():
        try:
            data  = collector()
            saved = save_articles(name, data)
            results[name] = {"status": "success", "count": len(data), "saved": saved}
        except Exception as e:
            errors[name] = str(e)
    return {"results": results, "errors": errors}

# ════════════════════════════════════════════════════════════
#  エクスポート (export/all を export/{source} より先に定義)
# ════════════════════════════════════════════════════════════

@app.get("/api/export/all")
def export_all():
    """全ソースをテキストファイルに書き出してダウンロード"""
    try:
        path = do_export_all()
        return FileResponse(path, filename="llm_trainer_all.txt")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export/{source}")
def export_source(source: str):
    """指定ソースのデータをテキストファイルに書き出してダウンロード"""
    try:
        col     = get_collection(source)
        results = col.get(include=["documents", "metadatas"])
        lines   = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            lines.append(f"# {meta.get('title', '')}")
            lines.append(f"URL: {meta.get('url', '')}")
            lines.append(doc)
            lines.append("---")
        path = f"/app/data/export_{source}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return FileResponse(path, filename=f"{source}.txt")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ════════════════════════════════════════════════════════════
#  Open WebUI 手動更新
# ════════════════════════════════════════════════════════════

@app.post("/api/openwebui/update")
def openwebui_update():
    """手動でOpen WebUIのナレッジベースを更新する"""
    try:
        path    = do_export_all()
        success = update_openwebui_knowledge(path)
        return {"status": "ok" if success else "skipped", "file": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))