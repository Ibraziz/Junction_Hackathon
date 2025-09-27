# Power Plant Telemetry Dashboard

A comprehensive dashboard for visualizing and analyzing power plant telemetry data in real-time.

## Features

### 📊 Interactive Visualizations
1. **Time Series Plots**: Power generation, engine load, and efficiency over time with dual y-axis
2. **Temperature Monitoring**: Engine and ambient temperature tracking
3. **Emissions Analysis**: Real-time CO₂ emissions monitoring with area fill
4. **Correlation Analysis**: Interactive scatter plots to explore relationships between metrics
5. **Statistical Insights**: Comprehensive performance metrics and statistics

### 🎛️ Dashboard Controls
- Asset ID selection
- Flexible time range picker with quick select buttons
- Interactive metric selection for correlation analysis
- Real-time data fetching from telemetry API

### 📈 Available Metrics
- **Power Generation**: `power_gen_MW`
- **Engine Metrics**: `engine_load_percent`, `engine_rpm`, `engine_temp_C`
- **Fuel & Emissions**: `fuel_flow_kg_h`, `co2_emissions_kg_min`
- **Electrical**: `voltage_V`, `current_A`, `frequency_Hz`
- **Battery**: `battery_soc_percent`, `battery_power_MW`
- **Environment**: `ambient_temp_C`
- **Performance**: `efficiency_percent`

## Setup and Usage

### Prerequisites
1. **Telemetry API Server**: Must be running on port 8002
2. **Python Environment**: Virtual environment activated with required packages

### Starting the Services

#### 1. Start the Telemetry API Server
```powershell
# Navigate to project root and activate virtual environment
cd "d:\Study\Jvaskyla\Second Year\Junction_hackathon\Fixed_Plots\Junction_Hackathon"
.\.venv\Scripts\Activate.ps1

# Start the API server
cd telemetry-service
python main.py --port 8002
```

The API will be available at: http://localhost:8002

#### 2. Start the Dashboard
```powershell
# In a new terminal, navigate to dashboard directory
cd "d:\Study\Jvaskyla\Second Year\Junction_hackathon\Fixed_Plots\Junction_Hackathon\dashboard"

# Start the Streamlit dashboard
streamlit run app.py --server.port 8501
```

The dashboard will be available at: http://localhost:8501

### Using the Dashboard

1. **Health Check**: The dashboard automatically checks if the API server is running
2. **Select Asset**: Enter an asset ID (default: "power-plant-001")
3. **Choose Time Range**: 
   - Use date/time pickers for precise control
   - Or use quick select buttons (Last 1 Hour, Last 6 Hours)
4. **Fetch Data**: Click "🔄 Fetch Data" to retrieve telemetry information
5. **Analyze**: Explore the various charts and metrics:
   - Review performance overview with key statistics
   - Examine time series trends
   - Monitor temperatures and emissions
   - Analyze correlations between different metrics
   - View detailed statistics and raw data

### Sample Data Queries

The API supports time ranges up to 7 days. Here are some example queries:

- **Quick Test**: 5 minutes of data
  - Asset: `power-plant-001`
  - Start: `2024-01-01T10:00:00Z`
  - End: `2024-01-01T10:05:00Z`

- **Hourly Analysis**: 1 hour of data
  - Asset: `generator-002`
  - Start: `2024-01-01T08:00:00Z`
  - End: `2024-01-01T09:00:00Z`

- **Daily Pattern**: 24 hours of data
  - Asset: `turbine-003`
  - Start: `2024-01-01T00:00:00Z`
  - End: `2024-01-02T00:00:00Z`

## Technical Details

### API Endpoints
- `GET /health` - Health check
- `GET /telemetry/{asset_id}` - Retrieve telemetry data
- `GET /docs` - API documentation (Swagger UI)

### Data Format
Each telemetry data point includes:
- Timestamp (ISO format)
- Asset ID
- Power generation metrics
- Engine performance data
- Electrical characteristics
- Environmental conditions
- Emissions data

### Dependencies
- **streamlit**: Web application framework
- **plotly**: Interactive plotting library
- **pandas**: Data manipulation and analysis
- **requests**: HTTP library for API calls
- **numpy**: Numerical computing

## Troubleshooting

### Common Issues

1. **Cannot connect to API**: 
   - Ensure the telemetry API server is running on port 8002
   - Check that the virtual environment is activated

2. **No data returned**:
   - Verify the time range is valid (start < end)
   - Ensure the time range doesn't exceed 7 days
   - Check the asset ID is correct

3. **Dashboard won't start**:
   - Ensure all dependencies are installed
   - Check that port 8501 is available
   - Activate the virtual environment

### Performance Notes
- The dashboard caches data in session state for better performance
- Time series plots are optimized for up to 10,080 data points (1 week at 1-minute intervals)
- Correlation analysis updates automatically when metrics are changed