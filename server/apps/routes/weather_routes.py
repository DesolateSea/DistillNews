import httpx
from fastapi import APIRouter, HTTPException, Query

from apps.core.config import OPENWEATHER_API_KEY

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/geocode")
async def geocode_location(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(1, ge=1, le=5),
):
    """Proxy OpenWeather geocoding without exposing its API key to browsers."""
    if not OPENWEATHER_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OpenWeather API is not configured on the server",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/geo/1.0/direct",
                params={"q": q, "limit": limit, "appid": OPENWEATHER_API_KEY},
            )
        response.raise_for_status()
        return response.json()
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