import json
from redis import Redis
import os
from fastapi import HTTPException

redis_url = os.getenv("REDIS_URL")
redis = Redis.from_url(redis_url)


async def save_results_to_redis(results, uuid_str):
    # Store in Redis for 10 minutes
    redis.setex(uuid_str, 600, json.dumps(results))


async def get_results_from_redis(uuid_str):
    result = redis.get(uuid_str)
    if result is None:
        raise HTTPException(
            status_code=404, detail="Results not found or expired")
    return json.loads(result)
