import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.cache import check_redis, close_redis
from app.db import check_database, close_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_redis()
    await close_database()


app = FastAPI(
    title="AgentOps AI API",
    version="0.2.0",
    description="Backend API for the AgentOps AI platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "AgentOps AI API",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "api",
        "version": "0.2.0",
    }


@app.get("/ready")
async def ready():
    database_result, redis_result = await asyncio.gather(
        check_database(),
        check_redis(),
        return_exceptions=True,
    )

    services = {
        "database": database_result is True,
        "redis": redis_result is True,
    }
    is_ready = all(services.values())

    payload = {
        "status": "ready" if is_ready else "not_ready",
        "services": services,
    }

    if not is_ready:
        return JSONResponse(status_code=503, content=payload)

    return payload
