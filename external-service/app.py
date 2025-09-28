from datetime import datetime
from typing import Optional, List, Dict, Any, Union
import asyncio
import math
import random
from datetime import datetime, timedelta

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


# Power Generation Weather Models
class SolarRadiation(BaseModel):
    direct_normal_irradiance: float  # W/m²
    diffuse_horizontal_irradiance: float  # W/m²
    global_horizontal_irradiance: float  # W/m²
    direct_horizontal_irradiance: float  # W/m²
    extra_terrestrial_irradiance: float  # W/m²
    sunshine_duration: float  # minutes
    uv_index: float
    uv_index_clear_sky: float
    photovoltaic_power_output: float  # MW/km²
    photovoltaic_power_output_clear_sky: float  # MW/km²


class WindProfile(BaseModel):
    wind_speed_10m: float  # m/s
    wind_speed_20m: float  # m/s
    wind_speed_30m: float  # m/s
    wind_speed_40m: float  # m/s
    wind_speed_50m: float  # m/s
    wind_speed_80m: float  # m/s
    wind_speed_100m: float  # m/s
    wind_speed_120m: float  # m/s
    wind_direction_10m: float  # degrees
    wind_direction_80m: float  # degrees
    wind_direction_100m: float  # degrees
    wind_gusts_10m: float  # m/s
    wind_power_output: float  # MW/km²
    wind_power_density: float  # W/m²


class AtmosphericConditions(BaseModel):
    temperature_2m: float  # °C
    temperature_10m: float  # °C
    temperature_80m: float  # °C
    temperature_100m: float  # °C
    relative_humidity_2m: float  # %
    dew_point_2m: float  # °C
    pressure_msl: float  # hPa
    pressure_surface: float  # hPa
    cloud_cover_low: float  # %
    cloud_cover_mid: float  # %
    cloud_cover_high: float  # %
    cloud_cover_total: float  # %
    visibility: float  # km
    weather_code: int
    precipitation: float  # mm
    precipitation_probability: float  # %
    showers: float  # mm
    snowfall: float  # cm
    rain: float  # mm
    freezing_level_height: float  # m
    is_day: int  # 0 or 1


class HydroConditions(BaseModel):
    precipitation: float  # mm
    snowfall: float  # cm
    snow_depth: float  # cm
    runoff: float  # mm
    soil_moisture_0_to_1cm: float  # m³/m³
    soil_moisture_1_to_3cm: float  # m³/m³
    soil_moisture_3_to_9cm: float  # m³/m³
    soil_moisture_9_to_27cm: float  # m³/m³
    soil_moisture_27_to_81cm: float  # m³/m³
    river_discharge: float  # m³/s
    reservoir_level: float  # %
    stream_flow_index: float  # normalized


class PowerGenerationWeatherData(BaseModel):
    time: datetime
    latitude: float
    longitude: float
    solar_radiation: SolarRadiation
    wind_profile: WindProfile
    atmospheric_conditions: AtmosphericConditions
    hydro_conditions: HydroConditions
    total_renewable_power_potential: float  # MW
    thermal_efficiency_factor: float  # 0-1
    grid_transmission_efficiency: float  # 0-1
    demand_forecast_factor: float  # normalized


class PowerGenerationWeatherResponse(BaseModel):
    location_name: str
    latitude: float
    longitude: float
    timezone: str
    elevation: float  # meters
    generation_data: List[PowerGenerationWeatherData]
    summary: Dict[str, Any]


def get_location_name(latitude: float, longitude: float) -> str:
    """Get location name based on coordinates (simplified)"""
    # This is a simplified function for demo purposes
    # In production, you'd use a proper geocoding service
    if 60 <= latitude <= 70 and 19 <= longitude <= 31:
        return "Finland"
    elif 55 <= latitude <= 58 and 10 <= longitude <= 15:
        return "Denmark"
    elif 58 <= latitude <= 60 and 3 <= longitude <= 12:
        return "Norway"
    elif 55 <= latitude <= 69 and 11 <= longitude <= 24:
        return "Sweden"
    else:
        return f"Location {latitude:.2f}, {longitude:.2f}"


def generate_power_weather_data(
    latitude: float,
    longitude: float,
    start_time: datetime,
    end_time: datetime,
    time_step_minutes: int = 5
) -> List[PowerGenerationWeatherData]:
    """Generate realistic weather data for power generation with time-based seeding"""

    # Set random seed based on location and start time for reproducibility
    location_seed = int(latitude * 100 + longitude * 100 + start_time.timestamp())
    random.seed(location_seed)

    # Initialize base conditions that will evolve naturally
    base_temp = 15 + random.uniform(-10, 10)  # Base temperature
    base_pressure = 1013 + random.uniform(-20, 20)  # Base pressure
    base_humidity = 60 + random.uniform(-20, 20)  # Base humidity
    seasonal_factor = math.sin((start_time.timetuple().tm_yday / 365) * 2 * math.pi)  # Seasonal variation

    data_points = []
    current_time = start_time

    # Initialize weather patterns that evolve slowly
    weather_system_speed = random.uniform(0.1, 0.3)  # How fast weather changes
    cloud_pattern = random.uniform(0.2, 0.8)  # Base cloud cover
    wind_pattern_base = random.uniform(3, 12)  # Base wind speed

    while current_time <= end_time:
        # Time-based factors
        hour_of_day = current_time.hour + current_time.minute / 60
        day_of_year = current_time.timetuple().tm_yday

        # Solar calculations
        solar_elevation = max(0, 90 - abs(90 * math.sin((hour_of_day - 6) * math.pi / 12)))
        is_day = 1 if 6 <= hour_of_day <= 18 else 0

        # Calculate cloud cover with natural variation
        cloud_cover = cloud_pattern + 0.2 * math.sin(current_time.timestamp() * weather_system_speed * 0.01)
        cloud_cover = max(0, min(1, cloud_cover))

        # Temperature variation (daily + weather pattern)
        temp_variation = 8 * math.sin((hour_of_day - 6) * math.pi / 12)
        weather_temp_variation = 5 * math.sin(current_time.timestamp() * weather_system_speed * 0.02)
        temperature = base_temp + temp_variation + weather_temp_variation + seasonal_factor * 10

        # Wind speed with gusts and natural variation
        wind_base = wind_pattern_base + 2 * math.sin(current_time.timestamp() * weather_system_speed * 0.015)
        wind_gust_factor = 1 + 0.3 * random.random() if random.random() > 0.7 else 1
        wind_speed_10m = max(0, wind_base)

        # Wind profile with height (wind shear)
        wind_shear_exponent = 0.15 if wind_speed_10m < 5 else 0.25
        wind_speed_80m = wind_speed_10m * (80 / 10) ** wind_shear_exponent
        wind_speed_100m = wind_speed_10m * (100 / 10) ** wind_shear_exponent

        # Solar radiation calculations
        if is_day:
            clear_sky_ghi = 1000 * solar_elevation / 90
            ghi = clear_sky_ghi * (1 - cloud_cover * 0.75)
            dhi = clear_sky_ghi * cloud_cover * 0.2
            dni = max(0, ghi - dhi)
            sunshine_duration = max(0, 60 - cloud_cover * 60)
        else:
            ghi = 0
            dhi = 0
            dni = 0
            sunshine_duration = 0

        # UV index
        uv_index = (ghi / 100) * (1 if is_day else 0)

        # Photovoltaic power output (simplified model)
        pv_efficiency = 0.2  # 20% efficiency
        pv_temp_coefficient = -0.004  # -0.4% per °C
        pv_temp_derate = 1 + pv_temp_coefficient * (temperature - 25)
        pv_power = ghi * pv_efficiency * pv_temp_derate / 1000  # MW/km²

        # Wind power output
        wind_power_coefficient = 0.4  # Power coefficient
        air_density = 1.225 * (pressure_msl := base_pressure) / 1013 * (273.15 / (temperature + 273.15))
        wind_power_density = 0.5 * air_density * wind_speed_100m ** 3
        wind_power = wind_power_density * wind_power_coefficient / 1e6  # MW/km²

        # Precipitation
        precip_prob = cloud_cover * 0.3
        if random.random() < precip_prob * 0.1:  # 10% chance of precip per time step
            precipitation = random.uniform(0.1, 2.0)
        else:
            precipitation = 0

        # Soil moisture (slowly changing)
        soil_moisture_base = 0.3 + 0.2 * math.sin(day_of_year * math.pi / 365)
        soil_moisture = soil_moisture_base + precipitation * 0.01

        # Calculate all values
        solar_data = SolarRadiation(
            direct_normal_irradiance=dni,
            diffuse_horizontal_irradiance=dhi,
            global_horizontal_irradiance=ghi,
            direct_horizontal_irradiance=ghi * math.sin(solar_elevation * math.pi / 180) if is_day else 0,
            extra_terrestrial_irradiance=1367 * (1 + 0.033 * math.cos(day_of_year * 2 * math.pi / 365)),
            sunshine_duration=sunshine_duration,
            uv_index=uv_index,
            uv_index_clear_sky=uv_index / (1 - cloud_cover * 0.75) if cloud_cover < 1 else uv_index,
            photovoltaic_power_output=pv_power,
            photovoltaic_power_output_clear_sky=pv_power / (1 - cloud_cover * 0.75) if cloud_cover < 1 else pv_power
        )

        wind_data = WindProfile(
            wind_speed_10m=wind_speed_10m,
            wind_speed_20m=wind_speed_10m * (20/10) ** wind_shear_exponent,
            wind_speed_30m=wind_speed_10m * (30/10) ** wind_shear_exponent,
            wind_speed_40m=wind_speed_10m * (40/10) ** wind_shear_exponent,
            wind_speed_50m=wind_speed_10m * (50/10) ** wind_shear_exponent,
            wind_speed_80m=wind_speed_80m,
            wind_speed_100m=wind_speed_100m,
            wind_speed_120m=wind_speed_10m * (120/10) ** wind_shear_exponent,
            wind_direction_10m=random.uniform(0, 360),
            wind_direction_80m=random.uniform(0, 360),
            wind_direction_100m=random.uniform(0, 360),
            wind_gusts_10m=wind_speed_10m * wind_gust_factor,
            wind_power_output=wind_power,
            wind_power_density=wind_power_density
        )

        atmospheric_data = AtmosphericConditions(
            temperature_2m=temperature,
            temperature_10m=temperature - 0.5,
            temperature_80m=temperature - 2,
            temperature_100m=temperature - 2.5,
            relative_humidity_2m=max(0, min(100, base_humidity + 10 * math.sin(current_time.timestamp() * 0.001))),
            dew_point_2m=temperature - ((100 - base_humidity) / 5),
            pressure_msl=base_pressure + 5 * math.sin(current_time.timestamp() * 0.0005),
            pressure_surface=base_pressure + 100,
            cloud_cover_low=cloud_cover * 100 * random.uniform(0.3, 0.6),
            cloud_cover_mid=cloud_cover * 100 * random.uniform(0.2, 0.4),
            cloud_cover_high=cloud_cover * 100 * random.uniform(0.1, 0.3),
            cloud_cover_total=cloud_cover * 100,
            visibility=30 - cloud_cover * 20 if precipitation == 0 else 10,
            weather_code=0 if precipitation == 0 else (61 if temperature > 0 else 71),
            precipitation=precipitation,
            precipitation_probability=precip_prob * 100,
            showers=precipitation * 0.5 if random.random() < 0.3 else 0,
            snowfall=precipitation if temperature < 0 else 0,
            rain=precipitation if temperature >= 0 else 0,
            freezing_level_height=max(0, 1000 * (1 + temperature / 10)),
            is_day=is_day
        )

        hydro_data = HydroConditions(
            precipitation=precipitation,
            snowfall=precipitation if temperature < 0 else 0,
            snow_depth=max(0, 10 + precipitation * 0.5 - (temperature if temperature > 0 else 0) * 0.1),
            runoff=precipitation * 0.7,
            soil_moisture_0_to_1cm=soil_moisture,
            soil_moisture_1_to_3cm=soil_moisture * 0.9,
            soil_moisture_3_to_9cm=soil_moisture * 0.8,
            soil_moisture_9_to_27cm=soil_moisture * 0.7,
            soil_moisture_27_to_81cm=soil_moisture * 0.6,
            river_discharge=100 + precipitation * 10 + 20 * math.sin(day_of_year * math.pi / 365),
            reservoir_level=70 + 10 * math.sin(day_of_year * math.pi / 365),
            stream_flow_index=0.5 + 0.3 * math.sin(day_of_year * math.pi / 365)
        )

        # Calculate summary metrics
        total_renewable_potential = pv_power + wind_power  # MW/km²
        thermal_efficiency = max(0.3, min(0.5, 0.4 - (temperature - 15) * 0.005))  # Temperature affects thermal plants
        grid_efficiency = 0.95 - 0.05 * (precipitation / 10)  # Weather affects transmission
        demand_factor = 0.7 + 0.3 * math.sin((hour_of_day - 6) * math.pi / 12) + 0.1 * (temperature - 15) / 10

        data_point = PowerGenerationWeatherData(
            time=current_time,
            latitude=latitude,
            longitude=longitude,
            solar_radiation=solar_data,
            wind_profile=wind_data,
            atmospheric_conditions=atmospheric_data,
            hydro_conditions=hydro_data,
            total_renewable_power_potential=total_renewable_potential,
            thermal_efficiency_factor=thermal_efficiency,
            grid_transmission_efficiency=grid_efficiency,
            demand_forecast_factor=demand_factor
        )

        data_points.append(data_point)

        # Move to next time step
        current_time += timedelta(minutes=time_step_minutes)

        # Slowly evolve base patterns
        cloud_pattern += random.uniform(-0.01, 0.01)
        cloud_pattern = max(0.1, min(0.9, cloud_pattern))
        wind_pattern_base += random.uniform(-0.1, 0.1)
        wind_pattern_base = max(1, min(20, wind_pattern_base))

    return data_points



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
@app.get("/api/weather/current", response_model=PowerGenerationWeatherResponse)
async def current_weather(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude between -90 and 90"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude between -180 and 180"),
):
    """Get current weather data with comprehensive power generation metrics"""
    now = datetime.utcnow()

    # Generate data for current time and next hour for context
    generation_data = generate_power_weather_data(
        latitude=latitude,
        longitude=longitude,
        start_time=now,
        end_time=now + timedelta(hours=1),
        time_step_minutes=5
    )

    # Get elevation (simplified)
    elevation = abs(latitude) * 10 + random.uniform(-50, 200)

    # Calculate summary for current conditions
    current_data = generation_data[0] if generation_data else None
    summary = {}
    if current_data:
        summary = {
            "current_conditions": {
                "solar_power_potential_mw_km2": round(current_data.solar_radiation.photovoltaic_power_output, 3),
                "wind_power_potential_mw_km2": round(current_data.wind_profile.wind_power_output, 3),
                "total_renewable_potential_mw_km2": round(current_data.total_renewable_power_potential, 3),
                "thermal_efficiency_percent": round(current_data.thermal_efficiency_factor * 100, 1),
                "grid_efficiency_percent": round(current_data.grid_transmission_efficiency * 100, 1),
                "demand_factor": round(current_data.demand_forecast_factor, 3),
                "generation_advisory": "Optimal for solar" if current_data.solar_radiation.global_horizontal_irradiance > 500 and current_data.atmospheric_conditions.cloud_cover_total < 30
                    else "Optimal for wind" if current_data.wind_profile.wind_speed_100m > 8
                    else "Mixed conditions" if current_data.total_renewable_power_potential > 0.3
                    else "Challenging for renewables"
            },
            "immediate_forecast": {
                "next_hour_trend": "Increasing" if generation_data and generation_data[-1].total_renewable_power_potential > current_data.total_renewable_power_potential
                    else "Decreasing" if generation_data and generation_data[-1].total_renewable_power_potential < current_data.total_renewable_power_potential
                    else "Stable",
                "weather_stability": "High" if current_data.wind_profile.wind_gusts_10m - current_data.wind_profile.wind_speed_10m < 3
                    else "Moderate"
            }
        }

    return PowerGenerationWeatherResponse(
        location_name=get_location_name(latitude, longitude),
        latitude=latitude,
        longitude=longitude,
        timezone="UTC",
        elevation=round(elevation, 1),
        generation_data=generation_data[:1],  # Return only current data point
        summary=summary
    )


@app.get("/api/weather/forecast", response_model=PowerGenerationWeatherResponse)
async def weather_forecast(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude between -90 and 90"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude between -180 and 180"),
    days: int = Query(7, ge=1, le=16, description="Number of forecast days (max 16)"),
    past_days: Optional[int] = Query(None, ge=0, le=90, description="Include past days in forecast (max 90)"),
    hourly_data: bool = Query(True, description="Return hourly data (true) or daily summary (false)"),
):
    """Get comprehensive weather forecast with power generation metrics"""
    now = datetime.utcnow()
    start_time = now - timedelta(days=past_days) if past_days else now
    end_time = now + timedelta(days=days)

    # Generate comprehensive forecast data
    time_step = 60 if not hourly_data else 5  # Use hourly if not explicitly requested
    generation_data = generate_power_weather_data(
        latitude=latitude,
        longitude=longitude,
        start_time=start_time,
        end_time=end_time,
        time_step_minutes=time_step
    )

    # Get elevation
    elevation = abs(latitude) * 10 + random.uniform(-50, 200)

    # Calculate comprehensive summary
    summary = {}
    if generation_data:
        # Filter data for forecast period (excluding past if included)
        forecast_data = [d for d in generation_data if d.time >= now] if past_days else generation_data

        if forecast_data:
            # Daily aggregations
            daily_data = {}
            for data_point in forecast_data:
                day_key = data_point.time.date()
                if day_key not in daily_data:
                    daily_data[day_key] = []
                daily_data[day_key].append(data_point)

            daily_summaries = {}
            for day, day_points in daily_data.items():
                day_summary = {
                    "date": day.isoformat(),
                    "avg_temperature_c": round(sum(d.atmospheric_conditions.temperature_2m for d in day_points) / len(day_points), 1),
                    "avg_wind_speed_100m_ms": round(sum(d.wind_profile.wind_speed_100m for d in day_points) / len(day_points), 2),
                    "avg_cloud_cover_percent": round(sum(d.atmospheric_conditions.cloud_cover_total for d in day_points) / len(day_points), 1),
                    "total_precipitation_mm": round(sum(d.atmospheric_conditions.precipitation for d in day_points), 2),
                    "max_solar_power_mw_km2": round(max(d.solar_radiation.photovoltaic_power_output for d in day_points), 3),
                    "max_wind_power_mw_km2": round(max(d.wind_profile.wind_power_output for d in day_points), 3),
                    "avg_renewable_potential_mw_km2": round(sum(d.total_renewable_power_potential for d in day_points) / len(day_points), 3),
                    "peak_demand_factor": round(max(d.demand_forecast_factor for d in day_points), 3),
                    "total_solar_energy_mwh_km2": round(sum(d.solar_radiation.photovoltaic_power_output for d in day_points) * (time_step / 60), 2),
                    "total_wind_energy_mwh_km2": round(sum(d.wind_profile.wind_power_output for d in day_points) * (time_step / 60), 2),
                    "weather_condition": "Sunny" if sum(d.atmospheric_conditions.cloud_cover_total for d in day_points) / len(day_points) < 20
                        else "Partly Cloudy" if sum(d.atmospheric_conditions.cloud_cover_total for d in day_points) / len(day_points) < 60
                        else "Cloudy" if sum(d.atmospheric_conditions.precipitation for d in day_points) < 5
                        else "Rainy",
                    "generation_outlook": "Excellent" if sum(d.total_renewable_power_potential for d in day_points) / len(day_points) > 0.8
                        else "Good" if sum(d.total_renewable_power_potential for d in day_points) / len(day_points) > 0.5
                        else "Moderate" if sum(d.total_renewable_power_potential for d in day_points) / len(day_points) > 0.3
                        else "Poor"
                }
                daily_summaries[day.isoformat()] = day_summary

            # Overall forecast summary
            avg_ghi = sum(d.solar_radiation.global_horizontal_irradiance for d in forecast_data) / len(forecast_data)
            avg_wind = sum(d.wind_profile.wind_speed_100m for d in forecast_data) / len(forecast_data)
            total_energy_potential = sum(d.total_renewable_power_potential for d in forecast_data) * (time_step / 60)

            summary = {
                "forecast_period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "days": days,
                    "includes_historical": past_days > 0,
                    "data_resolution": "hourly" if hourly_data else "daily"
                },
                "overall_metrics": {
                    "average_ghi_w_m2": round(avg_ghi, 2),
                    "average_wind_speed_100m_ms": round(avg_wind, 2),
                    "total_energy_potential_mwh_km2": round(total_energy_potential, 2),
                    "average_thermal_efficiency_percent": round(sum(d.thermal_efficiency_factor for d in forecast_data) / len(forecast_data) * 100, 1),
                    "average_grid_efficiency_percent": round(sum(d.grid_transmission_efficiency for d in forecast_data) / len(forecast_data) * 100, 1)
                },
                "daily_breakdown": daily_summaries,
                "generation_forecast": {
                    "best_renewable_day": max(daily_summaries.keys(), key=lambda d: daily_summaries[d]["avg_renewable_potential_mw_km2"]) if daily_summaries else None,
                    "peak_generation_day": max(daily_summaries.keys(), key=lambda d: daily_summaries[d]["total_solar_energy_mwh_km2"] + daily_summaries[d]["total_wind_energy_mwh_km2"]) if daily_summaries else None,
                    "highest_demand_day": max(daily_summaries.keys(), key=lambda d: daily_summaries[d]["peak_demand_factor"]) if daily_summaries else None,
                    "forecast_confidence": "High" if len(daily_summaries) <= 3 else "Medium" if len(daily_summaries) <= 7 else "Lower"
                },
                "operational_recommendations": {
                    "optimal_maintenance_windows": [d for d in daily_summaries if daily_summaries[d]["avg_wind_speed_100m_ms"] < 10 and daily_summaries[d]["total_precipitation_mm"] < 2][:3],
                    "high_generation_periods": [d for d in daily_summaries if daily_summaries[d]["generation_outlook"] in ["Excellent", "Good"]],
                    "grid_stability_concerns": "Low" if avg_wind < 15 and sum(d.atmospheric_conditions.precipitation for d in forecast_data) < 20 else "Moderate"
                }
            }

    return PowerGenerationWeatherResponse(
        location_name=get_location_name(latitude, longitude),
        latitude=latitude,
        longitude=longitude,
        timezone="UTC",
        elevation=round(elevation, 1),
        generation_data=generation_data,
        summary=summary
    )


@app.get("/api/weather/historical", response_model=PowerGenerationWeatherResponse)
async def historical_weather(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude between -90 and 90"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude between -180 and 180"),
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    hourly_data: bool = Query(True, description="Return hourly data (true) or daily summary (false)"),
    include_analysis: bool = Query(True, description="Include historical analysis and insights"),
):
    """Get comprehensive historical weather data with power generation metrics"""
    # Parse dates
    start_time = datetime.fromisoformat(start_date)
    end_time = datetime.fromisoformat(end_date) + timedelta(days=1) - timedelta(minutes=1)  # End of day

    # Validate date range
    if end_time <= start_time:
        raise HTTPException(
            status_code=400,
            detail="End date must be after start date"
        )

    # Limit to reasonable range
    days_requested = (end_time - start_time).days
    if days_requested > 365:
        raise HTTPException(
            status_code=400,
            detail="Historical data request cannot exceed 1 year"
        )

    # Generate historical data
    time_step = 60 if not hourly_data else 5  # Use hourly resolution if requested
    generation_data = generate_power_weather_data(
        latitude=latitude,
        longitude=longitude,
        start_time=start_time,
        end_time=end_time,
        time_step_minutes=time_step
    )

    # Get elevation
    elevation = abs(latitude) * 10 + random.uniform(-50, 200)

    # Calculate comprehensive historical analysis
    summary = {}
    if generation_data and include_analysis:
        # Monthly aggregations
        monthly_data = {}
        for data_point in generation_data:
            month_key = data_point.time.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(data_point)

        monthly_summaries = {}
        for month, month_points in monthly_data.items():
            month_summary = {
                "month": month,
                "avg_temperature_c": round(sum(d.atmospheric_conditions.temperature_2m for d in month_points) / len(month_points), 1),
                "avg_wind_speed_100m_ms": round(sum(d.wind_profile.wind_speed_100m for d in month_points) / len(month_points), 2),
                "avg_cloud_cover_percent": round(sum(d.atmospheric_conditions.cloud_cover_total for d in month_points) / len(month_points), 1),
                "total_precipitation_mm": round(sum(d.atmospheric_conditions.precipitation for d in month_points), 2),
                "avg_solar_power_mw_km2": round(sum(d.solar_radiation.photovoltaic_power_output for d in month_points) / len(month_points), 3),
                "avg_wind_power_mw_km2": round(sum(d.wind_profile.wind_power_output for d in month_points) / len(month_points), 3),
                "total_solar_energy_mwh_km2": round(sum(d.solar_radiation.photovoltaic_power_output for d in month_points) * (time_step / 60), 2),
                "total_wind_energy_mwh_km2": round(sum(d.wind_profile.wind_power_output for d in month_points) * (time_step / 60), 2),
                "peak_renewable_output_mw_km2": round(max(d.total_renewable_power_potential for d in month_points), 3),
                "capacity_factor_solar_percent": round((sum(d.solar_radiation.photovoltaic_power_output for d in month_points) * (time_step / 60) / (max(d.solar_radiation.photovoltaic_power_output for d in month_points) * len(month_points) * (time_step / 60))) * 100) if max(d.solar_radiation.photovoltaic_power_output for d in month_points) > 0 else 0,
                "capacity_factor_wind_percent": round((sum(d.wind_profile.wind_power_output for d in month_points) * (time_step / 60) / (max(d.wind_profile.wind_power_output for d in month_points) * len(month_points) * (time_step / 60))) * 100) if max(d.wind_profile.wind_power_output for d in month_points) > 0 else 0,
                "weather_events": {
                    "storm_hours": len([d for d in month_points if d.wind_profile.wind_gusts_10m > 20]),
                    "frost_hours": len([d for d in month_points if d.atmospheric_conditions.temperature_2m < 0]),
                    "heat_wave_hours": len([d for d in month_points if d.atmospheric_conditions.temperature_2m > 30]),
                    "high_precipitation_hours": len([d for d in month_points if d.atmospheric_conditions.precipitation > 5])
                }
            }
            monthly_summaries[month] = month_summary

        # Overall statistics
        total_solar_energy = sum(d.solar_radiation.photovoltaic_power_output for d in generation_data) * (time_step / 60)
        total_wind_energy = sum(d.wind_profile.wind_power_output for d in generation_data) * (time_step / 60)
        avg_temperature = sum(d.atmospheric_conditions.temperature_2m for d in generation_data) / len(generation_data)
        avg_wind_speed = sum(d.wind_profile.wind_speed_100m for d in generation_data) / len(generation_data)

        # Find extremes
        max_temp_event = max(generation_data, key=lambda x: x.atmospheric_conditions.temperature_2m)
        min_temp_event = min(generation_data, key=lambda x: x.atmospheric_conditions.temperature_2m)
        max_wind_event = max(generation_data, key=lambda x: x.wind_profile.wind_gusts_10m)
        max_solar_event = max(generation_data, key=lambda x: x.solar_radiation.global_horizontal_irradiance)

        summary = {
            "period": {
                "start": start_date,
                "end": end_date,
                "days": days_requested,
                "data_points": len(generation_data),
                "resolution": "hourly" if hourly_data else "daily"
            },
            "overall_statistics": {
                "total_solar_energy_mwh_km2": round(total_solar_energy, 2),
                "total_wind_energy_mwh_km2": round(total_wind_energy, 2),
                "total_renewable_energy_mwh_km2": round(total_solar_energy + total_wind_energy, 2),
                "average_temperature_c": round(avg_temperature, 1),
                "temperature_range_c": f"{round(min_temp_event.atmospheric_conditions.temperature_2m, 1)} to {round(max_temp_event.atmospheric_conditions.temperature_2m, 1)}",
                "average_wind_speed_100m_ms": round(avg_wind_speed, 2),
                "max_wind_gust_ms": round(max_wind_event.wind_profile.wind_gusts_10m, 2),
                "average_grid_efficiency_percent": round(sum(d.grid_transmission_efficiency for d in generation_data) / len(generation_data) * 100, 1),
                "weather_stability_index": round(1 - (sum(d.wind_profile.wind_gusts_10m - d.wind_profile.wind_speed_10m for d in generation_data) / len(generation_data) / 20), 3)
            },
            "monthly_breakdown": monthly_summaries,
            "extreme_events": {
                "highest_temperature": {
                    "value": round(max_temp_event.atmospheric_conditions.temperature_2m, 1),
                    "timestamp": max_temp_event.time.isoformat(),
                    "impact_on_efficiency": f"{((max_temp_event.thermal_efficiency_factor - 0.4) / 0.4 * 100):+.1f}%"
                },
                "lowest_temperature": {
                    "value": round(min_temp_event.atmospheric_conditions.temperature_2m, 1),
                    "timestamp": min_temp_event.time.isoformat(),
                    "impact_on_efficiency": f"{((min_temp_event.thermal_efficiency_factor - 0.4) / 0.4 * 100):+.1f}%"
                },
                "strongest_winds": {
                    "gust_speed_ms": round(max_wind_event.wind_profile.wind_gusts_10m, 2),
                    "timestamp": max_wind_event.time.isoformat(),
                    "wind_power_mw_km2": round(max_wind_event.wind_profile.wind_power_output, 3)
                },
                "peak_solar_irradiance": {
                    "ghi_w_m2": round(max_solar_event.solar_radiation.global_horizontal_irradiance, 2),
                    "timestamp": max_solar_event.time.isoformat(),
                    "pv_power_mw_km2": round(max_solar_event.solar_radiation.photovoltaic_power_output, 3)
                }
            },
            "generation_analysis": {
                "best_month_for_solar": max(monthly_summaries.keys(), key=lambda m: monthly_summaries[m]["total_solar_energy_mwh_km2"]) if monthly_summaries else None,
                "best_month_for_wind": max(monthly_summaries.keys(), key=lambda m: monthly_summaries[m]["total_wind_energy_mwh_km2"]) if monthly_summaries else None,
                "most_stable_month": min(monthly_summaries.keys(), key=lambda m: monthly_summaries[m]["weather_events"]["storm_hours"]) if monthly_summaries else None,
                "seasonal_pattern": "High solar in summer, high wind in winter" if 60 <= latitude <= 70 else "Mixed patterns throughout year",
                "reliability_assessment": "High renewable availability" if (total_solar_energy + total_wind_energy) / days_requested > 5 else "Moderate renewable availability"
            },
            "operational_insights": {
                "optimal_maintenance_season": [m for m in monthly_summaries if monthly_summaries[m]["weather_events"]["storm_hours"] < 10 and monthly_summaries[m]["avg_temperature_c"] > 5],
                "high_risk_periods": [m for m in monthly_summaries if monthly_summaries[m]["weather_events"]["storm_hours"] > 20 or monthly_summaries[m]["weather_events"]["frost_hours"] > 100],
                "efficiency_optimization": "Summer focus on thermal, winter focus on wind" if 60 <= latitude <= 70 else "Balanced approach recommended",
                "grid_stability_history": "Generally stable" if avg_wind_speed < 15 and sum(d.atmospheric_conditions.precipitation for d in generation_data) / days_requested < 5 else "Variable conditions experienced"
            }
        }

    return PowerGenerationWeatherResponse(
        location_name=get_location_name(latitude, longitude),
        latitude=latitude,
        longitude=longitude,
        timezone="UTC",
        elevation=round(elevation, 1),
        generation_data=generation_data,
        summary=summary
    )


@app.get("/api/weather/power-generation", response_model=PowerGenerationWeatherResponse)
async def power_generation_weather(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude between -90 and 90"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude between -180 and 180"),
    start_time: datetime = Query(..., description="Start time in ISO 8601 format"),
    end_time: datetime = Query(..., description="End time in ISO 8601 format"),
    time_step_minutes: int = Query(5, ge=1, le=60, description="Time step in minutes (1-60)"),
    include_summary: bool = Query(True, description="Include summary statistics"),
):
    """Get comprehensive weather data optimized for electricity power generation analysis

    This endpoint provides extensive weather data specifically tailored for power generation
    including solar radiation profiles, wind characteristics at multiple heights, atmospheric
    conditions affecting thermal efficiency, and hydrological parameters. Data is generated
    with realistic temporal patterns and natural transitions between time steps.

    Features:
    - Solar radiation: DNI, DHI, GHI, UV index, and PV power output calculations
    - Wind profile: Speeds from 10m to 120m with wind shear modeling
    - Atmospheric conditions: Temperature, humidity, pressure, cloud cover at multiple levels
    - Hydrological data: Precipitation, soil moisture, river discharge, reservoir levels
    - Power generation metrics: Renewable potential, thermal efficiency, grid efficiency
    - Time-seeded data: Consistent patterns with natural evolution

    Use Cases:
    - Renewable energy forecasting and optimization
    - Grid stability analysis under various weather conditions
    - Power plant efficiency modeling
    - Energy market trading strategies
    - Maintenance scheduling based on weather patterns
    """
    # Validate time range
    if end_time <= start_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time"
        )

    # Limit data points to prevent excessive responses
    max_hours = (end_time - start_time).total_seconds() / 3600
    if max_hours > 168:  # 7 days
        raise HTTPException(
            status_code=400,
            detail="Time range cannot exceed 7 days"
        )

    # Generate weather data
    generation_data = generate_power_weather_data(
        latitude=latitude,
        longitude=longitude,
        start_time=start_time,
        end_time=end_time,
        time_step_minutes=time_step_minutes
    )

    # Calculate summary if requested
    summary = {}
    if include_summary and generation_data:
        # Solar summary
        avg_ghi = sum(d.solar_radiation.global_horizontal_irradiance for d in generation_data) / len(generation_data)
        max_pv_output = max(d.solar_radiation.photovoltaic_power_output for d in generation_data)
        total_solar_energy = sum(d.solar_radiation.photovoltaic_power_output for d in generation_data) * (time_step_minutes / 60)

        # Wind summary
        avg_wind_speed_100m = sum(d.wind_profile.wind_speed_100m for d in generation_data) / len(generation_data)
        max_wind_output = max(d.wind_profile.wind_power_output for d in generation_data)
        total_wind_energy = sum(d.wind_profile.wind_power_output for d in generation_data) * (time_step_minutes / 60)

        # Atmospheric summary
        avg_temp = sum(d.atmospheric_conditions.temperature_2m for d in generation_data) / len(generation_data)
        avg_cloud_cover = sum(d.atmospheric_conditions.cloud_cover_total for d in generation_data) / len(generation_data)
        total_precipitation = sum(d.atmospheric_conditions.precipitation for d in generation_data)

        # Hydro summary
        avg_reservoir_level = sum(d.hydro_conditions.reservoir_level for d in generation_data) / len(generation_data)
        avg_river_discharge = sum(d.hydro_conditions.river_discharge for d in generation_data) / len(generation_data)

        # Overall metrics
        avg_renewable_potential = sum(d.total_renewable_power_potential for d in generation_data) / len(generation_data)
        avg_thermal_efficiency = sum(d.thermal_efficiency_factor for d in generation_data) / len(generation_data)
        avg_grid_efficiency = sum(d.grid_transmission_efficiency for d in generation_data) / len(generation_data)
        peak_demand_factor = max(d.demand_forecast_factor for d in generation_data)

        summary = {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "duration_hours": max_hours,
                "data_points": len(generation_data),
                "time_step_minutes": time_step_minutes
            },
            "solar_energy": {
                "average_ghi_w_m2": round(avg_ghi, 2),
                "max_pv_output_mw_km2": round(max_pv_output, 3),
                "total_energy_potential_mwh_km2": round(total_solar_energy, 2),
                "capacity_factor": round(total_solar_energy / (max_pv_output * max_hours) * 100, 1) if max_pv_output > 0 else 0
            },
            "wind_energy": {
                "average_wind_speed_100m_ms": round(avg_wind_speed_100m, 2),
                "max_wind_output_mw_km2": round(max_wind_output, 3),
                "total_energy_potential_mwh_km2": round(total_wind_energy, 2),
                "capacity_factor": round(total_wind_energy / (max_wind_output * max_hours) * 100, 1) if max_wind_output > 0 else 0
            },
            "atmospheric_conditions": {
                "average_temperature_c": round(avg_temp, 1),
                "average_cloud_cover_percent": round(avg_cloud_cover, 1),
                "total_precipitation_mm": round(total_precipitation, 2),
                "weather_stability": "High" if max(d.wind_profile.wind_gusts_10m for d in generation_data) - min(d.wind_profile.wind_speed_10m for d in generation_data) < 5 else "Moderate"
            },
            "hydro_conditions": {
                "average_reservoir_level_percent": round(avg_reservoir_level, 1),
                "average_river_discharge_m3_s": round(avg_river_discharge, 1),
                "water_availability": "High" if avg_river_discharge > 120 else "Moderate" if avg_river_discharge > 80 else "Low"
            },
            "system_performance": {
                "average_renewable_potential_mw_km2": round(avg_renewable_potential, 3),
                "average_thermal_efficiency_percent": round(avg_thermal_efficiency * 100, 1),
                "average_grid_transmission_efficiency_percent": round(avg_grid_efficiency * 100, 1),
                "peak_demand_factor": round(peak_demand_factor, 3)
            },
            "operational_insights": {
                "optimal_generation_windows": "Daytime hours with low cloud cover" if avg_cloud_cover < 30 and avg_ghi > 400 else "Variable conditions",
                "maintenance_advisory": "Favorable" if avg_wind_speed_100m < 15 and total_precipitation < 5 else "Challenging conditions expected",
                "grid_stability_risk": "Low" if avg_renewable_potential > 0.5 and avg_grid_efficiency > 0.93 else "Moderate"
            }
        }

    # Get elevation (simplified - in production use a proper elevation API)
    elevation = abs(latitude) * 10 + random.uniform(-50, 200)  # Simplified elevation model

    return PowerGenerationWeatherResponse(
        location_name=get_location_name(latitude, longitude),
        latitude=latitude,
        longitude=longitude,
        timezone="UTC",  # Simplified - would calculate proper timezone
        elevation=round(elevation, 1),
        generation_data=generation_data,
        summary=summary
    )


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