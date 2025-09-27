# Fingrid API Mirror Service

A clean, minimal FastAPI service that mirrors Fingrid API endpoints for energy data with placeholder Open-Meteo weather integration.

## Features

- **FastAPI Service**: Modern, async Python web framework
- **Fingrid API Mirror**: Clean endpoints mirroring all key Fingrid datasets
- **Open-Meteo Placeholder**: Ready for weather data integration
- **Environment Variables**: Secure API key management
- **Type Safety**: Full Pydantic validation
- **Async HTTP**: Non-blocking requests with httpx

## Setup

### 1. Initialize Virtual Environment

```bash
uv venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
uv add fastapi httpx uvicorn pydantic-settings
```

### 3. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your Fingrid API key:

```
FINGRID_API_KEY=your_fingrid_api_key_here
```

### 4. Run the Service

```bash
uv run app.py
```

Or using uvicorn directly:

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Production Data
- `GET /api/production/nuclear-power` - Real-time nuclear power production
- `GET /api/production/hydro-power` - Real-time hydro power production
- `GET /api/production/wind-power` - Real-time wind power production
- `GET /api/production/total-real-time` - Real-time total production
- `GET /api/production/total` - Total electricity production

### Consumption & Grid
- `GET /api/consumption/electricity` - Real-time electricity consumption
- `GET /api/grid/kinetic-energy` - Nordic power system kinetic energy
- `GET /api/grid/state` - Power system state
- `GET /api/grid/frequency` - Grid frequency

### Market & Pricing
- `GET /api/market/down-regulation-price` - Down-regulation bid price
- `GET /api/market/emission-factor` - Emission factor for Finland

### Storage & Forecast
- `GET /api/storage/battery-charging` - Battery storage charging power
- `GET /api/forecast/wind-power` - Wind power generation forecast

### Weather (Placeholder)
- `GET /api/weather/current` - Current weather data
- `GET /api/weather/forecast` - Weather forecast

## Query Parameters

All Fingrid endpoints support these optional parameters:
- `start_time`: ISO 8601 formatted datetime
- `end_time`: ISO 8601 formatted datetime
- `format`: json, xml, or csv (default: json)
- `page`: Page number (default: 1)
- `page_size`: Items per page, 1-1000 (default: 100)

## Example Usage

```bash
# Get nuclear power data for the last 24 hours
curl "http://localhost:8000/api/production/nuclear-power?start_time=2025-09-26T00:00:00Z&end_time=2025-09-27T00:00:00Z"

# Get wind power forecast
curl "http://localhost:8000/api/forecast/wind-power"

# Get weather placeholder (lat/lon required)
curl "http://localhost:8000/api/weather/current?latitude=60.1699&longitude=24.9384"
```

## Project Structure

```
├── app.py              # Main FastAPI application
├── .env                # Environment variables (not tracked)
├── .env.example        # Environment variables template
├── .venv/              # Virtual environment (ignored)
├── .python-version     # Python version pin
├── pyproject.toml      # Project dependencies
└── README.md           # This file
```

## Security Notes

- The Fingrid API key is loaded from environment variables
- Never commit your actual `.env` file to version control
- The service includes rate limiting considerations
- All endpoints include proper error handling

## Next Steps

To complete the Open-Meteo integration:
1. Visit [Open-Meteo API docs](https://open-meteo.com/)
2. Implement the actual weather data fetching in the placeholder endpoints
3. Add weather models to `app.py`
4. Update the README with available weather parameters
