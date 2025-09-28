from datetime import datetime
from typing import Optional, List, Dict, Any, Union
import asyncio

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

app = FastAPI(
    title="Fingrid API Mirror",
    description="A clean FastAPI service mirroring Fingrid API endpoints",
    version="1.0.0",
)


class Settings(BaseSettings):
    fingrid_api_key: str
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"

    class Config:
        env_file = ".env"


settings = Settings()



# Pydantic models for response validation
class DatasetResponse(BaseModel):
    id: int
    name: str
    unit: str
    value: float
    start_time: datetime
    end_time: datetime


class ErrorResponse(BaseModel):
    error: str
    message: str


class WeatherCurrent(BaseModel):
    time: datetime
    temperature_2m: float
    wind_speed_10m: float
    wind_direction_10m: Optional[float] = None
    weather_code: Optional[int] = None


class WeatherHourly(BaseModel):
    time: List[datetime]
    temperature_2m: List[float]
    relative_humidity_2m: List[float]
    wind_speed_10m: List[float]
    precipitation: Optional[List[float]] = None
    weather_code: Optional[List[int]] = None


class WeatherResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str
    current_units: Dict[str, str]
    current: WeatherCurrent
    hourly_units: Dict[str, str]
    hourly: WeatherHourly


@app.get("/")
async def root():
    return {"message": "Fingrid API Mirror Service"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Production Data Endpoints
@app.get("/api/production/nuclear-power")
async def nuclear_power(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get real-time nuclear power production data"""
    return await fetch_fingrid_data(181, start_time, end_time, format, page, page_size)


@app.get("/api/production/hydro-power")
async def hydro_power(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get real-time hydro power production data"""
    return await fetch_fingrid_data(188, start_time, end_time, format, page, page_size)


@app.get("/api/production/wind-power")
async def wind_power(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get real-time wind power production data"""
    return await fetch_fingrid_data(191, start_time, end_time, format, page, page_size)


@app.get("/api/production/total-real-time")
async def total_production_realtime(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get real-time total electricity production data"""
    return await fetch_fingrid_data(193, start_time, end_time, format, page, page_size)


@app.get("/api/production/total")
async def total_production(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get total electricity production data"""
    return await fetch_fingrid_data(192, start_time, end_time, format, page, page_size)


# Consumption & Grid Endpoints
@app.get("/api/consumption/electricity")
async def electricity_consumption(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get real-time electricity consumption data"""
    return await fetch_fingrid_data(74, start_time, end_time, format, page, page_size)


@app.get("/api/grid/kinetic-energy")
async def kinetic_energy(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get kinetic energy of Nordic power system"""
    return await fetch_fingrid_data(177, start_time, end_time, format, page, page_size)


@app.get("/api/grid/state")
async def power_system_state(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get real-time power system state"""
    return await fetch_fingrid_data(209, start_time, end_time, format, page, page_size)


@app.get("/api/grid/frequency")
async def grid_frequency(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get real-time grid frequency"""
    return await fetch_fingrid_data(260, start_time, end_time, format, page, page_size)


# Market & Pricing Endpoints
@app.get("/api/market/down-regulation-price")
async def down_regulation_price(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get price of last activated down-regulation bid"""
    return await fetch_fingrid_data(399, start_time, end_time, format, page, page_size)


@app.get("/api/market/emission-factor")
async def emission_factor(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get emission factor for electricity in Finland"""
    return await fetch_fingrid_data(246, start_time, end_time, format, page, page_size)


# Storage & Forecast Endpoints
@app.get("/api/storage/battery-charging")
async def battery_storage(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get battery storage charging power"""
    return await fetch_fingrid_data(251, start_time, end_time, format, page, page_size)


@app.get("/api/forecast/wind-power")
async def wind_power_forecast(
    start_time: Optional[datetime] = Query(None, description="Start time in ISO 8601 format"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO 8601 format"),
    format: str = Query("json", regex="^(json|xml|csv)$"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(100, ge=1, le=1000),
):
    """Get wind power generation forecast (daily update)"""
    return await fetch_fingrid_data(265, start_time, end_time, format, page, page_size)


# Open-Meteo Weather Endpoints
@app.get("/api/weather/current")
async def current_weather(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude between -90 and 90"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude between -180 and 180"),
):
    """Get current weather data from Open-Meteo API"""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m,weather_code",
    }
    return await fetch_open_meteo_data("forecast", params)


@app.get("/api/weather/forecast")
async def weather_forecast(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude between -90 and 90"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude between -180 and 180"),
    days: int = Query(7, ge=1, le=16, description="Number of forecast days (max 16)"),
    past_days: Optional[int] = Query(None, ge=0, le=90, description="Include past days in forecast (max 90)"),
):
    """Get weather forecast from Open-Meteo API"""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code",
        "forecast_days": days,
    }
    if past_days is not None:
        params["past_days"] = past_days
    return await fetch_open_meteo_data("forecast", params)


@app.get("/api/weather/historical")
async def historical_weather(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude between -90 and 90"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude between -180 and 180"),
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
):
    """Get historical weather data from Open-Meteo Archive API"""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
    }
    return await fetch_open_meteo_data("archive", params)


async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> httpx.Response:
    """Make HTTP request with exponential backoff retry logic"""
    for attempt in range(max_retries + 1):
        try:
            response = await client.get(url, headers=headers, params=params)

            # If successful, return the response
            if response.status_code == 200:
                return response

            # Handle rate limiting (429) with retry
            if response.status_code == 429:
                if attempt < max_retries:
                    # Extract retry-after header if available
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        delay = float(retry_after)
                    else:
                        # Exponential backoff with jitter
                        delay = base_delay * (2 ** attempt) + (0.1 * attempt)

                    await asyncio.sleep(delay)
                    continue

            # For other errors, raise immediately
            response.raise_for_status()

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            if attempt == max_retries:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to fetch data after {max_retries} retries: {str(e)}",
                )
            # Wait before retrying
            delay = base_delay * (2 ** attempt) + (0.1 * attempt)
            await asyncio.sleep(delay)

    # This should never be reached
    raise HTTPException(
        status_code=500,
        detail=f"Failed to fetch data after {max_retries} retries",
    )


async def fetch_fingrid_data(
    dataset_id: int,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    format: str,
    page: int,
    page_size: int,
) -> Dict[str, Any]:
    """Fetch data from Fingrid API"""
    url = f"https://data.fingrid.fi/api/datasets/{dataset_id}/data"
    headers = {
        "Accept": "application/json",
        "x-api-key": settings.fingrid_api_key,
    }
    params = {
        "format": format,
        "page": page,
        "pageSize": page_size,
    }
    if start_time:
        params["start_time"] = start_time.isoformat()
    if end_time:
        params["end_time"] = end_time.isoformat()

    async with httpx.AsyncClient(timeout=40.0) as client:
        try:
            response = await fetch_with_retry(
                client, url, headers=headers, params=params,
                max_retries=3, base_delay=1.0
            )
            return response.json()
        except HTTPException:
            # Re-raise HTTPException as-is
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch data from Fingrid API: {str(e)}",
            )


async def fetch_open_meteo_data(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch data from Open-Meteo API"""
    url = f"{settings.open_meteo_base_url}/{endpoint}"

    async with httpx.AsyncClient(timeout=40.0) as client:
        try:
            response = await fetch_with_retry(
                client, url, params=params,
                max_retries=3, base_delay=1.0
            )
            return response.json()
        except HTTPException:
            # Re-raise HTTPException as-is
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch data from Open-Meteo API: {str(e)}",
            )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)