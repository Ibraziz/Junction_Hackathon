from fastapi import FastAPI, HTTPException, Query
from datetime import datetime, UTC
from typing import List, Dict, Any
from telemetry_generator import TelemetryGenerator

app = FastAPI(
    title="Telemetry Service API",
    description="Realistic time-series telemetry generator for power assets",
    version="1.0.0"
)

# Store generator instances for each asset
_generators: Dict[str, TelemetryGenerator] = {}


def _parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string with timezone awareness."""
    try:
        # Try parsing with timezone first
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        # Fall back to naive datetime
        return datetime.fromisoformat(dt_str)


@app.get("/telemetry/{asset_id}", response_model=List[Dict[str, Any]])
async def get_telemetry(
    asset_id: str,
    start_time: str = Query(..., description="Start time in ISO format (e.g., 2024-01-01T00:00:00Z)"),
    end_time: str = Query(..., description="End time in ISO format (e.g., 2024-01-01T01:00:00Z)")
) -> List[Dict[str, Any]]:
    """Get telemetry data for a specific asset within a time range.

    Returns 1-minute interval data with realistic patterns for:
    - Power generation
    - Fuel consumption
    - Engine metrics
    - Electrical characteristics
    - Battery status
    - CO2 emissions

    The data is seeded based on the asset_id and start_time to ensure
    deterministic yet realistic progression.
    """
    try:
        start = _parse_datetime(start_time)
        end = _parse_datetime(end_time)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid datetime format: {e}. Use ISO format like '2024-01-01T00:00:00Z'"
        )

    if start >= end:
        raise HTTPException(
            status_code=400,
            detail="start_time must be before end_time"
        )

    # Limit query range to prevent excessive responses
    duration = end - start
    if duration.total_seconds() > 7 * 24 * 60 * 60:  # 7 days
        raise HTTPException(
            status_code=400,
            detail="Time range cannot exceed 7 days"
        )

    # Get or create generator for this asset
    if asset_id not in _generators:
        _generators[asset_id] = TelemetryGenerator(asset_id)

    generator = _generators[asset_id]
    telemetry = generator.generate_telemetry(start, end)

    return telemetry


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "telemetry-service"}


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "service": "Telemetry Service",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoint": "/telemetry/{asset_id}?start_time=...&end_time=..."
    }