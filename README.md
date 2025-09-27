# Power Plant Monitoring Dashboard

A comprehensive real-time monitoring system that combines power plant telemetry data with national energy grid statistics. The system provides a unified dashboard displaying both local power plant performance and Finnish national energy production data.

## Architecture

The system consists of three main components:

- **Dashboard**: Streamlit-based web interface for visualization
- **Telemetry Service**: FastAPI service providing power plant operational data  
- **External Service**: Fingrid API mirror for Finnish national energy grid data

## Features

- **Real-time Monitoring**: Live power plant telemetry and grid data
- **Unified Dashboard**: Combined view of local and national energy metrics
- **Automatic Data Fetching**: Fixed 7-day data window, no user configuration needed
- **Interactive Visualizations**: Plotly charts for power generation, grid performance
- **Service Health Monitoring**: Real-time connectivity status for all services
- **Clean Architecture**: Microservices design with FastAPI and Streamlit

## Quick Start

### 1. Start All Services

**Terminal 1 - Telemetry Service (Port 8002):**
```powershell
cd telemetry-service
python api.py
```

**Terminal 2 - External Service (Port 8000):**
```powershell
cd external-service  
python app.py
```

**Terminal 3 - Dashboard (Port 8501):**
```powershell
cd dashboard
python app.py
```

### 2. Access the Dashboard

Open your browser and navigate to: `http://localhost:8501`

The dashboard will automatically display:
- Power plant telemetry data (last 7 days)
- Finnish national energy grid statistics
- Combined energy production overview
- Real-time grid performance metrics

## Service Configuration

### External Service Setup

If using your own Fingrid API key, create `external-service/.env`:

```
FINGRID_API_KEY=your_fingrid_api_key_here
```

## Dashboard Features

The monitoring dashboard provides three main visualization sections:

### 1. Power Plant Overview
- **Generator Power Output**: Real-time power generation from plant telemetry
- **Operational Status**: Current plant performance metrics
- **Historical Trends**: 7-day power generation history

### 2. National Energy Mix  
- **Nuclear Power Production**: Finnish nuclear power output
- **Wind Power Generation**: National wind energy production
- **Total Consumption**: Country-wide electricity consumption

### 3. Grid Performance
- **System Frequency**: Real-time grid frequency monitoring
- **Grid Stability**: Power system operational state
- **Service Health**: Connectivity status for all data sources

## API Endpoints

### Telemetry Service (Port 8002)
- `GET /health` - Service health check
- `GET /telemetry` - Power plant operational data (1440 data points)

### External Service (Port 8000)
- `GET /health` - Service health check  
- `GET /api/production/nuclear-power` - Real-time nuclear power production
- `GET /api/production/wind-power` - Real-time wind power production
- `GET /api/consumption/electricity` - Real-time electricity consumption
- `GET /api/grid/frequency` - Grid frequency data

## Data Integration

The system automatically fetches and combines data from multiple sources:

### Telemetry Service
- Provides simulated power plant operational data
- 1440 data points covering 24-hour operational cycles  
- Includes power output, efficiency metrics, and operational status

### External Service (Fingrid API Mirror)
- Real-time Finnish national energy grid data
- Nuclear and wind power production statistics
- National electricity consumption patterns
- Grid frequency and stability metrics

### Fixed Date Range
- Dashboard displays data from the last 7 days
- No user configuration required - fully automated
- Consistent time windows for trend analysis

## Example API Usage

```bash
# Check service health
curl "http://localhost:8002/health"
curl "http://localhost:8000/health"

# Get telemetry data
curl "http://localhost:8002/telemetry"

# Get nuclear power data
curl "http://localhost:8000/api/production/nuclear-power"

# Get wind power data  
curl "http://localhost:8000/api/production/wind-power"
```

## Project Structure

```
Junction_Hackathon/
├── dashboard/                    # Streamlit Dashboard (Port 8501)
│   ├── app.py                   # Main dashboard application
│   └── requirements.txt         # Dashboard dependencies
├── telemetry-service/           # Telemetry API (Port 8002)  
│   ├── api.py                   # FastAPI telemetry service
│   ├── main.py                  # Service entry point
│   ├── telemetry_generator.py   # Data generation logic
│   └── pyproject.toml           # Service dependencies
├── external-service/            # External API Mirror (Port 8000)
│   ├── app.py                   # Fingrid API mirror service
│   └── pyproject.toml           # API mirror dependencies  
├── main.py                      # Project entry point
├── uv.lock                      # Dependency lock file
└── README.md                    # Project documentation
```

## Technical Details

### Dependencies
- **Streamlit**: Web dashboard framework
- **FastAPI**: API service framework  
- **Plotly**: Interactive visualization library
- **Pandas**: Data manipulation and analysis
- **Requests**: HTTP client for API communication
- **Uvicorn**: ASGI server for FastAPI services

### Data Flow
1. **Telemetry Service** generates simulated power plant data
2. **External Service** fetches real Finnish energy grid data from Fingrid API
3. **Dashboard** combines both data sources into unified visualizations
4. All services communicate via REST API calls
5. Dashboard refreshes data automatically every few seconds

### Port Configuration
- **8501**: Streamlit dashboard interface
- **8502**: Telemetry service API  
- **8000**: External service (Fingrid mirror)

## Troubleshooting

### Service Health Checks
The dashboard displays real-time service status. If any service shows as disconnected:

1. Ensure all three services are running on their respective ports
2. Check firewall settings if running on different machines
3. Verify API key configuration for external service if needed

### Common Issues
- **Port conflicts**: Ensure no other services are using ports 8000, 8501, 8502
- **Missing dependencies**: Run `pip install -r requirements.txt` in dashboard folder
- **API timeouts**: Check internet connection for Fingrid API access
