import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from src.collectors.github import get_trending_repos
from src.collectors.qiita import get_qiita_articles
from src.collectors.zenn import get_zenn_articles
from src.collectors.stackoverflow import get_stackoverflow_questions
from src.collectors.hackernews import get_hackernews_stories
from src.collectors.wikipedia import get_wikipedia_articles
from src.collectors.devto import get_devto_articles
from src.db import save_articles, get_stats, search
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from contextlib import asynccontextmanager

load_dotenv()

scheduler = AsyncIOScheduler()

async def scheduled_collect():
    """毎日自動収集する"""
    print(f"[{datetime.now()}] スケジュール収集開始")
    collectors = {
        "github": get_trending_repos,
        "qiita": get_qiita_articles,
        "zenn": get_zenn_articles,
        "stackoverflow": get_stackoverflow_questions,
        "hackernews": get_hackernews_stories,
        "wikipedia": get_wikipedia_articles,
        "devto": get_devto_articles,
    }
    for name, collector in collectors.items():
        try:
            data = collector()
            save_articles(name, data)
            print(f"[{datetime.now()}] {name}: {len(data)}件保存")
        except Exception as e:
            print(f"[{datetime.now()}] {name} エラー: {e}")
            
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

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/sources")
def get_sources():
    return {"sources": [
        {"id": 1, "name": "GitHub API", "enabled": True},
        {"id": 2, "name": "Qiita API", "enabled": True},
        {"id": 3, "name": "Zenn RSS", "enabled": True},
        {"id": 4, "name": "Stack Overflow", "enabled": True},
        {"id": 5, "name": "HackerNews", "enabled": True},
        {"id": 6, "name": "Wikipedia API", "enabled": True},
        {"id": 7, "name": "Dev.to API", "enabled": True},
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

@app.get("/api/collect/github")
def collect_github(language: str = "python", save: bool = True):
    try:
        repos = get_trending_repos(language=language)
        if save:
            save_articles("github", repos)
        return {"status": "success", "count": len(repos), "data": repos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/qiita")
def collect_qiita(tag: str = "python", save: bool = True):
    try:
        articles = get_qiita_articles(tag=tag)
        if save:
            save_articles("qiita", articles)
        return {"status": "success", "count": len(articles), "data": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/zenn")
def collect_zenn(topic: str = "python", save: bool = True):
    try:
        articles = get_zenn_articles(topic=topic)
        if save:
            save_articles("zenn", articles)
        return {"status": "success", "count": len(articles), "data": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/stackoverflow")
def collect_stackoverflow(tag: str = "python", save: bool = True):
    try:
        questions = get_stackoverflow_questions(tag=tag)
        if save:
            save_articles("stackoverflow", questions)
        return {"status": "success", "count": len(questions), "data": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/hackernews")
def collect_hackernews(save: bool = True):
    try:
        stories = get_hackernews_stories()
        if save:
            save_articles("hackernews", stories)
        return {"status": "success", "count": len(stories), "data": stories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/wikipedia")
def collect_wikipedia(topic: str = "Python", save: bool = True):
    try:
        articles = get_wikipedia_articles(topic=topic)
        if save:
            save_articles("wikipedia", articles)
        return {"status": "success", "count": len(articles), "data": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collect/devto")
def collect_devto(tag: str = "python", save: bool = True):
    try:
        articles = get_devto_articles(tag=tag)
        if save:
            save_articles("devto", articles)
        return {"status": "success", "count": len(articles), "data": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/collect/all")
def collect_all():
    """全ソースからデータを収集してDBに保存する"""
    results = {}
    errors = {}
    
    collectors = {
        "github": lambda: get_trending_repos(),
        "qiita": lambda: get_qiita_articles(),
        "zenn": lambda: get_zenn_articles(),
        "stackoverflow": lambda: get_stackoverflow_questions(),
        "hackernews": lambda: get_hackernews_stories(),
        "wikipedia": lambda: get_wikipedia_articles(),
        "devto": lambda: get_devto_articles(),
    }
    
    for name, collector in collectors.items():
        try:
            data = collector()
            saved = save_articles(name, data)
            results[name] = {"status": "success", "count": len(data), "saved": saved}
        except Exception as e:
            errors[name] = str(e)
    
    return {"results": results, "errors": errors}