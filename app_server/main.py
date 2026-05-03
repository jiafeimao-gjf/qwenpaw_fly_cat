# -*- coding: utf-8 -*-
"""App Server 主入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from auth.routes import router as auth_router
from messages.routes import router as messages_router
from database import init_db, SessionLocal
from auth.user_store import UserStore


app = FastAPI(
    title="QwenPaw App Server",
    description="配合 QwenPaw MyApp Channel 的消息服务端",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(messages_router)


@app.on_event("startup")
def startup_event():
    init_db()
    db = SessionLocal()
    try:
        user_store = UserStore(db)
        if not user_store.exists("test"):
            user_store.create("test", "test123")
    finally:
        db.close()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)