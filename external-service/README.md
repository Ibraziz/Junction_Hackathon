# External Service

This directory contains the external API service that provides data from external sources like Fingrid API and Open-Meteo weather API.

## Files

- `app.py` - Main FastAPI application with API endpoints
- `pyproject.toml` - Project dependencies and configuration
- `.env.example` - Environment variables template

## Setup

1. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Fingrid API key:
   ```
   FINGRID_API_KEY=your_fingrid_api_key_here
   ```

3. Install dependencies:
   ```bash
   uv add fastapi httpx uvicorn pydantic-settings
   ```

4. Run the service:
   ```bash
   uv run app.py
   ```

The service will be available at: http://localhost:8000

## API Endpoints

The service provides various endpoints for:
- Production data (nuclear, hydro, wind power)
- Consumption & grid data
- Market & pricing data
- Storage & forecast data
- Weather data from Open-Meteo API

For detailed API documentation, visit http://localhost:8000/docs when the service is running.