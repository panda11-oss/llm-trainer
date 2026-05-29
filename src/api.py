import os
import json
import sqlite3
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
from src.collectors.serper import search_serper
from src.db import save_articles, get_stats, search, get_collection
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from contextlib import asynccontextmanager

load_dotenv()

# ── 設定 ─────────────────────────────────────────────────
OPENWEBUI_URL    = os.getenv("OPENWEBUI_URL", "http://host.docker.internal:3000")
OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY", "")
KNOWLEDGE_ID     = os.getenv("OPENWEBUI_KNOWLEDGE_ID", "")
COLLECT_TAGS     = [t.strip() for t in os.getenv("COLLECT_TAGS", "python").split(",") if t.strip()]

TAGSETS_PATH = "/app/data/tagsets.json"
SHUTDOWN_FLAG_PATH = "/app/data/shutdown.flag"

scheduler = AsyncIOScheduler()


# ── 設定管理 ─────────────────────────────────────────────
SETTINGS_PATH = "/app/data/settings.json"
DEFAULT_SETTINGS = {
    "auto_shutdown": False,
    "collect_hour": 9,
    "collect_minute": 0,
    "timezone": "Asia/Tokyo",
    "retry_count": 3,
    "timeout": 30,
}

def load_settings() -> dict:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    except Exception:
        return DEFAULT_SETTINGS

def save_settings(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── ログ管理 ─────────────────────────────────────────────
LOG_DB_PATH = "/app/data/logs.db"

def init_log_db():
    os.makedirs(os.path.dirname(LOG_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(LOG_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_log(source: str, status: str, message: str):
    conn = sqlite3.connect(LOG_DB_PATH)
    conn.execute(
        "INSERT INTO logs (time, source, status, message) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime("%H:%M:%S"), source, status, message)
    )
    conn.commit()
    conn.close()

def get_logs(limit: int = 200) -> list[dict]:
    conn = sqlite3.connect(LOG_DB_PATH)
    rows = conn.execute(
        "SELECT id, time, source, status, message FROM logs ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "time": r[1], "source": r[2], "status": r[3], "message": r[4]} for r in rows]

# ── タグセット管理 ────────────────────────────────────────
DEFAULT_TAGSETS = {
    "active_ids": ["general"],
    "tagsets": [
        {
            "id": "general",
            "name": "技術全般",
            "icon": "🖥",
            "subcategories": [
                {"id": "g1", "name": "インフラ系",        "enabled": True,  "tags": ["linux", "docker", "bash", "ssh", "systemd"]},
                {"id": "g2", "name": "開発ツール",        "enabled": True,  "tags": ["python", "git", "vim", "rust"]},
                {"id": "g3", "name": "コンテナ/オーケストレーション", "enabled": True, "tags": ["kubernetes", "docker", "terraform"]},
            ],
        },
        {
            "id": "study",
            "name": "資格勉強",
            "icon": "📚",
            "subcategories": [
                {"id": "s1", "name": "サーバー系",     "enabled": True,  "tags": ["linuc", "lpic", "ccna", "rhcsa", "shell-script", "networking"]},
                {"id": "s2", "name": "コーディング系", "enabled": False, "tags": ["algorithm", "atcoder", "paiza", "competitive-programming"]},
                {"id": "s3", "name": "クラウド系",     "enabled": False, "tags": ["aws", "gcp", "azure", "terraform"]},
            ],
        },
    ],
}

def load_tagsets() -> dict:
    try:
        with open(TAGSETS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_TAGSETS

def save_tagsets(data: dict):
    os.makedirs(os.path.dirname(TAGSETS_PATH), exist_ok=True)
    with open(TAGSETS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_active_tags() -> list[str]:
    """アクティブなタグセット（複数可）のONカテゴリのタグを重複なしで返す"""
    data = load_tagsets()
    active_ids = data.get("active_ids", data.get("active_id", ["general"]))
    if isinstance(active_ids, str):
        active_ids = [active_ids]
    tags = []
    for active_id in active_ids:
        tagset = next((t for t in data["tagsets"] if t["id"] == active_id), None)
        if tagset:
            for sub in tagset["subcategories"]:
                if sub.get("enabled", True):
                    for tag in sub["tags"]:
                        if tag not in tags:
                            tags.append(tag)
    return tags if tags else COLLECT_TAGS

# ── タグベースの収集 ──────────────────────────────────────
def collect_by_tags() -> dict:
    tags = get_active_tags()
    results = {}
    errors = {}

    for tag in tags:
        for name, collector in [
            ("github",        lambda t=tag: get_trending_repos(language=t)),
            ("qiita",         lambda t=tag: get_qiita_articles(tag=t)),
            ("zenn",          lambda t=tag: get_zenn_articles(topic=t)),
            ("stackoverflow", lambda t=tag: get_stackoverflow_questions(tag=t)),
            ("devto",         lambda t=tag: get_devto_articles(tag=t)),
            ("wikipedia",     lambda t=tag: get_wikipedia_articles(topic=t)),
        ]:
            try:
                data = collector()
                saved = save_articles(name, data)
                if name not in results:
                    results[name] = {"count": 0, "saved": 0}
                results[name]["count"] += len(data)
                results[name]["saved"] += saved
            except Exception as e:
                errors[f"{name}_{tag}"] = str(e)
                save_log(name, "error", str(e))

    for name, collector in [
        ("hackernews", get_hackernews_stories),
        ("archwiki",   get_archwiki_articles),
        ("manpages",   get_manpages),
    ]:
        try:
            data = collector()
            saved = save_articles(name, data)
            results[name] = {"count": len(data), "saved": saved}
        except Exception as e:
            errors[name] = str(e)
            save_log(name, "error", str(e))

    # 収集結果をログに保存
    for name, r in results.items():
        save_log(name, "success", f"{r['count']}件取得 ({r['saved']}件保存)")

    return {"results": results, "errors": errors}

# ── Open WebUI 更新 ───────────────────────────────────────
def do_export_all() -> str:
    sources = ["github","qiita","zenn","stackoverflow","hackernews","wikipedia","devto","archwiki","manpages"]
    lines = []
    for source in sources:
        try:
            col = get_collection(source)
            results = col.get(include=["documents","metadatas"])
            for doc, meta in zip(results["documents"], results["metadatas"]):
                lines.append(f"# {meta.get('title','')}")
                lines.append(f"Source: {source}")
                lines.append(f"URL: {meta.get('url','')}")
                lines.append(doc)
                lines.append("---")
        except Exception:
            continue
    path = "/app/data/export_all.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[Export] {path} に {len(lines)} 行を書き出しました")
    return path

def update_openwebui_knowledge(file_path: str) -> bool:
    if not OPENWEBUI_API_KEY or not KNOWLEDGE_ID:
        print("[OpenWebUI] APIキーまたはナレッジIDが未設定のためスキップ")
        return False
    try:
        headers = {"Authorization": f"Bearer {OPENWEBUI_API_KEY}"}
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

# ── スケジューラー ────────────────────────────────────────
async def scheduled_collect():
    tags = get_active_tags()
    print(f"[{datetime.now()}] スケジュール収集開始 タグ: {tags}")
    collect_by_tags()
    try:
        path = do_export_all()
        update_openwebui_knowledge(path)
    except Exception as e:
        print(f"[Export] エラー: {e}")
    print(f"[{datetime.now()}] スケジュール収集完了")

    # シャットダウンフラグが有効なら実行フラグを作成
    try:
        settings = load_settings()
        if settings.get("auto_shutdown", False):
            with open(SHUTDOWN_FLAG_PATH, "w") as f:
                f.write("shutdown")
            print(f"[Shutdown] シャットダウンフラグを作成しました")
    except Exception as e:
        print(f"[Shutdown] エラー: {e}")

def update_scheduler():
    """設定からスケジューラーを更新する"""
    settings = load_settings()
    hour = settings.get("collect_hour", 9)
    minute = settings.get("collect_minute", 0)
    tz = settings.get("timezone", "Asia/Tokyo")
    scheduler.reschedule_job(
        "daily_collect",
        trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
    )
    print(f"[Scheduler] 収集時刻を {hour:02d}:{minute:02d} ({tz}) に更新しました")

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    hour = settings.get("collect_hour", 9)
    minute = settings.get("collect_minute", 0)
    tz = settings.get("timezone", "Asia/Tokyo")
    scheduler.add_job(
        scheduled_collect,
        CronTrigger(hour=hour, minute=minute, timezone=tz),
        id="daily_collect",
        replace_existing=True,
    )
    init_log_db()
    scheduler.start()
    tags = get_active_tags()
    print(f"✅ スケジューラー起動完了 収集時刻: {hour:02d}:{minute:02d} タグ: {tags}", flush=True)
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
# 基本
# ════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {"status": "ok", "tags": get_active_tags()}

@app.get("/api/sources")
def get_sources():
    return {"sources": [
        {"id": 1, "name": "GitHub API",      "enabled": True},
        {"id": 2, "name": "Qiita API",       "enabled": True},
        {"id": 3, "name": "Zenn RSS",        "enabled": True},
        {"id": 4, "name": "Stack Overflow",  "enabled": True},
        {"id": 5, "name": "HackerNews",      "enabled": True},
        {"id": 6, "name": "Wikipedia API",   "enabled": True},
        {"id": 7, "name": "Dev.to API",      "enabled": True},
        {"id": 8, "name": "Arch Wiki",       "enabled": True},
        {"id": 9, "name": "Man Pages",       "enabled": True},
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

@app.get("/api/tags")
def get_tags():
    return {"tags": get_active_tags()}



# ════════════════════════════════════════════════════════════
# ログ
# ════════════════════════════════════════════════════════════

@app.get("/api/logs")
def api_get_logs(limit: int = 200):
    return {"logs": get_logs(limit)}

@app.delete("/api/logs")
def api_clear_logs():
    conn = sqlite3.connect(LOG_DB_PATH)
    conn.execute("DELETE FROM logs")
    conn.commit()
    conn.close()
    return {"status": "ok"}

# ════════════════════════════════════════════════════════════
# 設定管理
# ════════════════════════════════════════════════════════════

@app.get("/api/settings")
def api_get_settings():
    return load_settings()

@app.put("/api/settings")
def api_update_settings(body: dict):
    settings = load_settings()
    settings.update(body)
    save_settings(settings)
    # 時刻・タイムゾーン変更時はスケジューラーを即時更新
    if any(k in body for k in ["collect_hour", "collect_minute", "timezone"]):
        try:
            update_scheduler()
        except Exception as e:
            print(f"[Scheduler] 更新エラー: {e}")
    return settings

# ════════════════════════════════════════════════════════════
# タグセット管理
# ════════════════════════════════════════════════════════════

@app.get("/api/tagsets")
def api_get_tagsets():
    data = load_tagsets()
    active_ids = data.get("active_ids", [data.get("active_id", "general")])
    if isinstance(active_ids, str):
        active_ids = [active_ids]
    return {"tagsets": data["tagsets"], "active_ids": active_ids}

@app.post("/api/tagsets")
def api_create_tagset(body: dict):
    data = load_tagsets()
    new_tagset = {
        "id": body.get("id", f"f{int(datetime.now().timestamp())}"),
        "name": body.get("name", "新しいタグセット"),
        "icon": body.get("icon", "📁"),
        "subcategories": body.get("subcategories", []),
    }
    data["tagsets"].append(new_tagset)
    save_tagsets(data)
    return {"status": "ok", "tagset": new_tagset}

@app.put("/api/tagsets/{tagset_id}/activate")
def api_activate_tagset(tagset_id: str, body: dict = {}):
    data = load_tagsets()
    if not any(t["id"] == tagset_id for t in data["tagsets"]):
        raise HTTPException(status_code=404, detail="tagset not found")
    active_ids = data.get("active_ids", [])
    if isinstance(active_ids, str):
        active_ids = [active_ids]
    if tagset_id in active_ids:
        # 既にアクティブなら解除（最低1つは残す）
        if len(active_ids) > 1:
            active_ids.remove(tagset_id)
    else:
        active_ids.append(tagset_id)
    data["active_ids"] = active_ids
    save_tagsets(data)
    return {"status": "ok", "active_ids": active_ids, "tags": get_active_tags()}

@app.put("/api/tagsets/{tagset_id}")
def api_update_tagset(tagset_id: str, body: dict):
    data = load_tagsets()
    for i, t in enumerate(data["tagsets"]):
        if t["id"] == tagset_id:
            data["tagsets"][i] = {**t, **body, "id": tagset_id}
            save_tagsets(data)
            return {"status": "ok", "tagset": data["tagsets"][i]}
    raise HTTPException(status_code=404, detail="tagset not found")

@app.delete("/api/tagsets/{tagset_id}")
def api_delete_tagset(tagset_id: str):
    data = load_tagsets()
    data["tagsets"] = [t for t in data["tagsets"] if t["id"] != tagset_id]
    if data["active_id"] == tagset_id:
        data["active_id"] = data["tagsets"][0]["id"] if data["tagsets"] else "general"
    save_tagsets(data)
    return {"status": "ok"}

# ════════════════════════════════════════════════════════════
# 個別収集
# ════════════════════════════════════════════════════════════

@app.get("/api/collect/github")
def collect_github(language: str = "python", save: bool = True):
    try:
        data = get_trending_repos(language=language)
        if save: save_articles("github", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/qiita")
def collect_qiita(tag: str = "python", save: bool = True):
    try:
        data = get_qiita_articles(tag=tag)
        if save: save_articles("qiita", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/zenn")
def collect_zenn(topic: str = "python", save: bool = True):
    try:
        data = get_zenn_articles(topic=topic)
        if save: save_articles("zenn", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/stackoverflow")
def collect_stackoverflow(tag: str = "python", save: bool = True):
    try:
        data = get_stackoverflow_questions(tag=tag)
        if save: save_articles("stackoverflow", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/hackernews")
def collect_hackernews(save: bool = True):
    try:
        data = get_hackernews_stories()
        if save: save_articles("hackernews", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/wikipedia")
def collect_wikipedia(topic: str = "Python", save: bool = True):
    try:
        data = get_wikipedia_articles(topic=topic)
        if save: save_articles("wikipedia", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/devto")
def collect_devto(tag: str = "python", save: bool = True):
    try:
        data = get_devto_articles(tag=tag)
        if save: save_articles("devto", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/archwiki")
def collect_archwiki(save: bool = True):
    try:
        data = get_archwiki_articles()
        if save: save_articles("archwiki", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/manpages")
def collect_manpages(save: bool = True):
    try:
        data = get_manpages()
        if save: save_articles("manpages", data)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/collect/all")
def collect_all():
    return collect_by_tags()

# ════════════════════════════════════════════════════════════
# エクスポート
# ════════════════════════════════════════════════════════════

@app.get("/api/export/all")
def export_all():
    try:
        path = do_export_all()
        return FileResponse(path, filename="llm_trainer_all.txt")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export/{source}")
def export_source(source: str):
    try:
        col = get_collection(source)
        results = col.get(include=["documents","metadatas"])
        lines = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            lines.append(f"# {meta.get('title','')}")
            lines.append(f"URL: {meta.get('url','')}")
            lines.append(doc)
            lines.append("---")
        path = f"/app/data/export_{source}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return FileResponse(path, filename=f"{source}.txt")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ════════════════════════════════════════════════════════════
# Open WebUI
# ════════════════════════════════════════════════════════════

@app.post("/api/openwebui/update")
def openwebui_update():
    try:
        path = do_export_all()
        success = update_openwebui_knowledge(path)
        return {"status": "ok" if success else "skipped", "file": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ════════════════════════════════════════════════════════════
# キーワード都度収集
# ════════════════════════════════════════════════════════════

@app.post("/api/collect/keyword")
def collect_keyword(body: dict):
    keyword = body.get("keyword", "").strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required")
    results = {}
    errors = {}
    for name, collector in [
        ("github",        lambda: get_trending_repos(language=keyword)),
        ("qiita",         lambda: get_qiita_articles(tag=keyword)),
        ("zenn",          lambda: get_zenn_articles(topic=keyword)),
        ("stackoverflow", lambda: get_stackoverflow_questions(tag=keyword)),
        ("devto",         lambda: get_devto_articles(tag=keyword)),
        ("wikipedia",     lambda: get_wikipedia_articles(topic=keyword)),
    ]:
        try:
            data = collector()
            saved = save_articles(name, data)
            results[name] = {"count": len(data), "saved": saved}
        except Exception as e:
            errors[name] = str(e)

    # Serper API（APIキーが設定されている場合のみ）
    try:
        serper_data = search_serper(keyword)
        if serper_data:
            saved = save_articles("serper", serper_data)
            results["serper"] = {"count": len(serper_data), "saved": saved}
    except Exception as e:
        errors["serper"] = str(e)

    total = sum(v["count"] for v in results.values())
    try:
        path = do_export_all()
        update_openwebui_knowledge(path)
    except Exception as e:
        print(f"[OpenWebUI] 更新エラー: {e}")
    return {"keyword": keyword, "total": total, "results": results, "errors": errors}

# ════════════════════════════════════════════════════════════
# 履歴・トレンド
# ════════════════════════════════════════════════════════════

@app.get("/api/history/trend")
def get_trend():
    """日別収集件数（スタブ: 実装は db.py 側で対応）"""
    return {"trend": []}

@app.get("/api/history/keywords")
def get_keyword_history():
    """キーワード収集履歴（スタブ: 実装は db.py 側で対応）"""
    return {"keywords": []}