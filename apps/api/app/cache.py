from redis.asyncio import Redis

from app.config import get_settings

settings = get_settings()

redis_client = Redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def check_redis() -> bool:
    return bool(await redis_client.ping())


async def close_redis() -> None:
    await redis_client.aclose()
