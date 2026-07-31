import json
import httpx
from fastapi import APIRouter, HTTPException, Query
from service.db.redis import RedisHandle

from config import config
OPENWEATHER_API_KEY = config.OPENWEATHER_API_KEY

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/geocode")
async def geocode_location(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(1, ge=1, le=5),
):
    """Proxy OpenWeather geocoding without exposing its API key to browsers, cached in Redis for 24h."""
    if not OPENWEATHER_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OpenWeather API is not configured on the server",
        )

    clean_q = q.strip().lower()
    cache_key = f"cache:weather:geocode:{clean_q}:{limit}"

    try:
        r = RedisHandle.client()
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/geo/1.0/direct",
                params={"q": q, "limit": limit, "appid": OPENWEATHER_API_KEY},
            )
        response.raise_for_status()
        data = response.json()

        try:
            r = RedisHandle.client()
            await r.set(cache_key, json.dumps(data), ex=86400)
        except Exception:
            pass

        return data
    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail="OpenWeather rejected the geocoding request",
        ) from error
    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach OpenWeather",
        ) from error