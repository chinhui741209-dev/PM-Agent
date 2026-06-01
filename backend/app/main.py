from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import intake, jira, templates, wbs

settings = get_settings()

app = FastAPI(
    title="AI Agent PM",
    description="輸入需求/規格 → AI 產生 WBS → PM 確認 → 一鍵部署 Jira",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake.router)
app.include_router(wbs.router)
app.include_router(jira.router)
app.include_router(templates.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "openai_configured": settings.openai_configured,
        "jira_configured": settings.jira_configured,
    }
