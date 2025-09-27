from datetime import datetime
from typing import Optional, List, Dict, Any

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


# Open-Meteo Placeholder Endpoints
@app.get("/api/weather/current")
async def current_weather(
    latitude: float = Query(..., description="Latitude"),
    longitude: float = Query(..., description="Longitude"),
):
    """Get current weather data (placeholder)"""
    # TODO: Implement actual Open-Meteo integration
    return {
        "message": "Open-Meteo integration placeholder",
        "latitude": latitude,
        "longitude": longitude,
        "data": None,
    }


@app.get("/api/weather/forecast")
async def weather_forecast(
    latitude: float = Query(..., description="Latitude"),
    longitude: float = Query(..., description="Longitude"),
    days: int = Query(7, ge=1, le=14, description="Number of forecast days"),
):
    """Get weather forecast (placeholder)"""
    # TODO: Implement actual Open-Meteo integration
    return {
        "message": "Open-Meteo forecast integration placeholder",
        "latitude": latitude,
        "longitude": longitude,
        "days": days,
        "data": None,
    }


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

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=e.response.status_code if hasattr(e, "response") else 500,
                detail=f"Failed to fetch data from Fingrid API: {str(e)}",
            )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)