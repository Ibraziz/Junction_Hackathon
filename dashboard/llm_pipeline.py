# dashboard/llm_pipeline.py

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import openai
import json
from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any, Optional
from sqlite_tools import execute_sql_query, get_table_schema, list_database_tables, get_table_data


SQLITE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql_query",
            "description": "Execute a SQL query on the Finland energy database and return results",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute. Use table 'time_series_60min_singleindex' for hourly data.",
                    },
                    "params": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional parameters for parameterized queries"
                    }
                },
                "required": ["query"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_table_schema",
            "description": "Get schema information for a database table",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to get schema for",
                    }
                },
                "required": ["table_name"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_database_tables",
            "description": "List all tables in the database",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        }
    }
]


# --- 1. Configuration & Setup ---

# Configure OpenAI client for Gemini
# IMPORTANT: Set the GEMINI_API_KEY environment variable for this to work.
try:
    client = openai.OpenAI(
        api_key=os.environ["GEMINI_API_KEY"],
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
except KeyError:
    client = None # Will be handled gracefully in the pipeline

# Constants for API services from the main app
TELEMETRY_API_URL = "http://localhost:8002"
EXTERNAL_API_URL = "http://localhost:8000"

# --- 2. Pydantic Models for Structured LLM Output ---

class ChartJSData(BaseModel):
    labels: List[str]
    datasets: List[Dict[str, Any]]

class ChartJSOptions(BaseModel):
    responsive: bool
    maintainAspectRatio: bool = Field(default=False)
    plugins: Dict[str, Any]
    scales: Dict[str, Any]

class ChartJSConfig(BaseModel):
    type: Literal['bar', 'line', 'pie', 'doughnut', 'radar', 'scatter', 'bubble']
    data: ChartJSData
    options: ChartJSOptions
    title: str = Field(description="A descriptive title for the chart.")

class LLMAnalysisResult(BaseModel):
    summary: str = Field(description="A concise, one-paragraph summary of the overall situation.")
    keywords: List[str] = Field(description="A list of 3-5 relevant keywords.")
    suggested_action: Literal[
        "MAINTAIN_OUTPUT",
        "INCREASE_OUTPUT_FOR_GRID_DEMAND",
        "DECREASE_OUTPUT_DUE_TO_SURPLUS",
        "PREPARE_FOR_RENEWABLE_FLUCTUATION",
        "CONSIDER_MAINTENANCE_DURING_LOW_DEMAND",
        "OPTIMIZE_EFFICIENTLY_DURING_PEAK_PRICING",
        "RAMP_UP_FOR_WIND_SHORTFALL",
        "BALANCE_GRID_FREQUENCY"
    ] = Field(description="The single most appropriate action to take from the provided list.")
    action_reasoning: str = Field(description="A brief justification for the suggested action.")
    charts: List[ChartJSConfig] = Field(description="A list of 2-3 Chart.js configurations for insightful visualizations.")
    html_component: Optional[str] = Field(description="An HTML component for embedding in a dashboard.", default=None)

class LLMQueryResponse(BaseModel):
    response: str = Field(description="A comprehensive response to the user's query.")
    charts: Optional[List[ChartJSConfig]] = Field(description="Optional Chart.js configurations for visualizations relevant to the query.", default=None)
    html_component: Optional[str] = Field(description="An optional HTML component for embedding in a dashboard.", default=None)

# --- 3. Data Fetching Functions ---

def fetch_recent_telemetry(asset_id: str, hours: int = 24) -> pd.DataFrame:
    """Fetches the most recent telemetry data for a given asset."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    url = f"{TELEMETRY_API_URL}/telemetry/{asset_id}"
    params = {
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    try:
        response = requests.get(url, params=params, timeout=40)
        response.raise_for_status()
        df = pd.DataFrame(response.json())
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except requests.exceptions.RequestException:
        return pd.DataFrame()

def fetch_recent_grid_data() -> pd.DataFrame:
    """Fetches recent data from all relevant grid endpoints."""
    endpoints = {
        'nuclear_power': 'production/nuclear-power',
        'wind_power': 'production/wind-power',
        'hydro_power': 'production/hydro-power',
        'consumption': 'consumption/electricity',
        'grid_frequency': 'grid/frequency',
        'day_ahead_price': 'price/day-ahead'
    }

    dfs = []
    for key, endpoint in endpoints.items():
        try:
            url = f"{EXTERNAL_API_URL}/api/{endpoint}"
            response = requests.get(url, params={"page_size": 100}, timeout=10)
            response.raise_for_status()
            data = response.json().get('data', [])
            if data:
                df = pd.DataFrame(data)
                df = df.rename(columns={'value': key, 'startTime': 'timestamp'})
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                dfs.append(df.set_index('timestamp')[[key]])
        except requests.exceptions.RequestException:
            continue

    if not dfs:
        return pd.DataFrame()

    combined_df = pd.concat(dfs, axis=1).sort_index()
    combined_df = combined_df.resample('3T').mean().interpolate(method='time').ffill().bfill()
    return combined_df.reset_index().tail(100)

def fetch_weather_data(lat: float, lon: float) -> dict:
    """Fetches current weather data for a given location."""
    url = f"{EXTERNAL_API_URL}/api/weather/current"
    params = {"latitude": lat, "longitude": lon}
    try:
        response = requests.get(url, params=params, timeout=40)
        response.raise_for_status()
        return response.json().get('current', {})
    except requests.exceptions.RequestException:
        return {}

def fetch_weather_forecast(lat: float, lon: float, days: int = 3) -> dict:
    """Fetches weather forecast data for a given location."""
    url = f"{EXTERNAL_API_URL}/api/weather/forecast"
    params = {"latitude": lat, "longitude": lon, "days": days}
    try:
        response = requests.get(url, params=params, timeout=40)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}

# --- 4. Data Aggregation & Prompt Generation ---

def aggregate_for_llm(telemetry_df: pd.DataFrame, grid_df: pd.DataFrame, weather_data: dict) -> str:
    """Aggregates data into a concise string for the LLM prompt."""
    summary = "## Power Plant & Grid Analysis Data\n\n"

    def safe_format(value, default='N/A', format_spec=None):
        """Safely format values that might be NaN or None"""
        if pd.isna(value) or value is None:
            return default
        if format_spec:
            return f"{value:{format_spec}}"
        return str(value)

    summary += "### Local Power Plant Performance (Last 24 Hours)\n"
    if not telemetry_df.empty:
        # Safely access numeric columns with fallbacks
        power_gen = telemetry_df.get('power_gen_MW', pd.Series(dtype=float))
        efficiency = telemetry_df.get('efficiency_percent', pd.Series(dtype=float))
        engine_load = telemetry_df.get('engine_load_percent', pd.Series(dtype=float))

        summary += f"- **Current Power Output:** {power_gen.iloc[-1] if not power_gen.empty else 0:.1f} MW\n"
        summary += f"- **24h Average Output:** {power_gen.mean():.1f} MW\n"
        summary += f"- **Peak Output:** {power_gen.max():.1f} MW\n"
        summary += f"- **Output Stability (Std Dev):** {power_gen.std():.1f} MW\n"
        summary += f"- **Average Efficiency:** {efficiency.mean():.1f}%\n"
        summary += f"- **Average Engine Load:** {engine_load.mean():.1f}%\n"
    else:
        summary += "- Plant telemetry data unavailable.\n"

    summary += "\n### National Grid Status (Most Recent)\n"
    if not grid_df.empty:
        latest = grid_df.iloc[-1]
        summary += f"- **Grid Frequency:** {safe_format(latest.get('grid_frequency'), 'N/A', '.2f')} Hz (Target: 50.00 Hz)\n"
        summary += f"- **Total Consumption:** {safe_format(latest.get('consumption'), 'N/A', '.0f')} MW\n"
        summary += f"- **Nuclear Power:** {safe_format(latest.get('nuclear_power'), 'N/A', '.0f')} MW ({latest.get('nuclear_power', 0)/latest.get('consumption', 1)*100:.1f}% of demand)\n"
        summary += f"- **Wind Power:** {safe_format(latest.get('wind_power'), 'N/A', '.0f')} MW ({latest.get('wind_power', 0)/latest.get('consumption', 1)*100:.1f}% of demand)\n"
        summary += f"- **Hydro Power:** {safe_format(latest.get('hydro_power'), 'N/A', '.0f')} MW ({latest.get('hydro_power', 0)/latest.get('consumption', 1)*100:.1f}% of demand)\n"
        summary += f"- **Day-Ahead Price:** {safe_format(latest.get('day_ahead_price'), 'N/A', '.1f')} €/MWh\n"

        # Calculate grid balance
        total_renewables = (latest.get('wind_power', 0) + latest.get('hydro_power', 0))
        total_generation = (latest.get('nuclear_power', 0) + total_renewables)
        balance = total_generation - latest.get('consumption', 0)
        summary += f"- **Grid Balance:** {balance:+.0f} MW ({'Surplus' if balance > 0 else 'Deficit'})\n"
    else:
        summary += "- Grid data unavailable.\n"

    summary += "\n### Local Weather Conditions\n"
    if weather_data:
        summary += f"- **Temperature:** {weather_data.get('temperature_2m', 'N/A')} °C\n"
        summary += f"- **Wind Speed:** {weather_data.get('wind_speed_10m', 'N/A')} km/h\n"
        summary += f"- **Cloud Cover:** {weather_data.get('cloud_cover', 'N/A')}%\n"
        summary += f"- **Precipitation:** {weather_data.get('precipitation', 'N/A')} mm\n"
    else:
        summary += "- Weather data unavailable.\n"

    return summary

def create_prompt(aggregated_data: str, telemetry_json: str, grid_json: str, weather_forecast: dict = None) -> List[Dict[str, str]]:
    """Creates the full prompt for the Gemini model."""
    system_prompt = """
You are an expert power plant operations analyst for a thermal power plant. Your task is to analyze real-time data from the local plant, the national energy grid, and local weather to provide a concise summary, suggest a single operational action, and generate insightful visualizations using Chart.js configurations.

**IMPORTANT: For grid and electricity market analysis only, assume the current date is September 2019. Use 2019-era energy market conditions, grid technologies, renewable energy penetration levels, and market regulations. However, use current Chart.js capabilities for visualization configurations.**

Your response MUST be a single, valid JSON object that conforms to the provided Pydantic schema. Do not include any markdown formatting like ```json.

Based on the data, choose ONE action from this list:
- "MAINTAIN_OUTPUT": Conditions are stable, no change needed.
- "INCREASE_OUTPUT_FOR_GRID_DEMAND": Grid consumption is high or other sources (like wind) are low, requiring more power.
- "DECREASE_OUTPUT_DUE_TO_SURPLUS": Grid has a surplus of power (e.g., high wind/nuclear, low consumption), making production uneconomical.
- "PREPARE_FOR_RENEWABLE_FLUCTUATION": Weather forecast suggests wind power will change significantly.
- "CONSIDER_MAINTENANCE_DURING_LOW_DEMAND": Grid demand and prices are low, presenting an opportunity for maintenance.
- "OPTIMIZE_EFFICIENTLY_DURING_PEAK_PRICING": High electricity prices combined with good plant efficiency suggest optimizing for maximum profitable output.
- "RAMP_UP_FOR_WIND_SHORTFALL": Wind power is dropping rapidly while consumption remains high.
- "BALANCE_GRID_FREQUENCY": Grid frequency is deviating from 50Hz, requiring adjustment to help stabilize.

For the charts, create 2-3 insightful visualizations that reveal meaningful relationships. Examples:
1. **Plant vs Grid Correlation**: Scatter plot correlating plant output with grid frequency deviations to show your plant's grid stabilization impact.
2. **Renewable Penetration Analysis**: Stacked area chart showing how renewables (wind + hydro) penetrate total consumption, with your plant's output as balancing power.
3. **Efficiency vs Load Matrix**: Heat map or bubble chart showing efficiency at different load levels and ambient temperatures.
4. **Economic Dispatch Analysis**: Line chart comparing electricity prices with your plant's marginal cost curve and current output.
5. **Weather Impact Analysis**: Multi-axis chart showing wind speed vs wind power generation vs your plant's compensatory output.
6. **Grid Stability Dashboard**: Combination chart with frequency deviations and total generation/consumption balance.
Ensure professional styling with clear labels and appropriate color schemes for power industry visualization.
"""

    user_prompt = f"""
Here is the latest aggregated data summary:
{aggregated_data}

Use the following raw data to construct the charts. Timestamps are in UTC.
### Raw Grid Data for Charting:
{grid_json}

### Raw Telemetry Data for Charting (resampled):
{telemetry_json}

### Weather Forecast (Next 3 days):
{json.dumps(weather_forecast or {}, indent=2)}

Please provide your complete analysis as a single JSON object.
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

# --- 6. Original Pipeline Function (for backward compatibility) ---

def run_analysis_pipeline_with_tools(asset_id: str = "power-plant-001", lat: float = 60.17, lon: float = 24.94) -> dict:
    """
    Enhanced analysis pipeline with SQLite database access tools.
    Returns a dictionary with the analysis result or an error message.
    """
    if not client:
        return {"error": "GEMINI_API_KEY environment variable not set. Please configure it to use the AI analysis feature."}

    # Fetch real-time data as before
    telemetry_df = fetch_recent_telemetry(asset_id)
    grid_df = fetch_recent_grid_data()
    weather_data = fetch_weather_data(lat, lon)
    weather_forecast = fetch_weather_forecast(lat, lon)

    if telemetry_df.empty and grid_df.empty:
        return {"error": "Failed to fetch data from both Telemetry and External services. Please ensure they are running."}

    aggregated_data_str = aggregate_for_llm(telemetry_df, grid_df, weather_data)

    # Prepare raw data for the LLM
    grid_json = "[]"
    if not grid_df.empty:
        grid_df['timestamp'] = grid_df['timestamp'].dt.strftime('%H:%M')
        grid_json = grid_df.tail(25).to_json(orient='records')

    telemetry_json = "[]"
    if not telemetry_df.empty:
        numeric_cols = telemetry_df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            cols_to_resample = ['timestamp'] + list(numeric_cols)
            telemetry_resampled = telemetry_df[cols_to_resample].resample('15T', on='timestamp').mean().reset_index()
            telemetry_resampled['timestamp'] = telemetry_resampled['timestamp'].dt.strftime('%d-%b %H:%M')
            telemetry_json = telemetry_resampled.tail(25).to_json(orient='records')

    # Enhanced system prompt with tool capabilities
    enhanced_system_prompt = """
You are an expert power plant operations analyst for a thermal power plant. You have access to:
1. Real-time plant telemetry and grid data
2. A historical database of Finland's electricity market data (2015-2020)

You can query the historical database to provide deeper context for your analysis. The main table is 'time_series_60min_singleindex' with columns:
- utc_timestamp: UTC timestamp
- FI_load_actual_entsoe_transparency: Finland electricity consumption (MW)
- FI_load_forecast_entsoe_transparency: Day-ahead load forecast (MW)  
- FI_wind_onshore_generation_actual: Wind generation (MW)

**Time Period**: January 1, 2015 - September 30, 2020
**Data Granularity**: Hourly (60-minute intervals)
**Data Level**: Country-level (not plant-level)

## Database Schema

The database contains three tables with different time granularities:
- `time_series_15min_singleindex` - 15-minute intervals
- `time_series_30min_singleindex` - 30-minute intervals
- `time_series_60min_singleindex` - 60-minute intervals (most complete)

### Finland Data Columns

All Finland-specific data uses the "FI_" prefix:

| Column Name | Data Type | Description | Unit |
|-------------|-----------|-------------|------|
| `utc_timestamp` | TEXT | UTC timestamp (ISO 8601 format) | - |
| `cet_cest_timestamp` | TEXT | Local Finnish time (CET/CEST) | - |
| `FI_load_actual_entsoe_transparency` | REAL | Actual electricity consumption | MW |
| `FI_load_forecast_entsoe_transparency` | REAL | Day-ahead load forecast | MW |
| `FI_wind_onshore_generation_actual` | REAL | Actual onshore wind generation | MW |

## Sample Data

### Finland Electricity Load and Wind Generation (Sample)

| utc_timestamp | cet_cest_timestamp | Actual Load (MW) | Forecast Load (MW) | Wind Generation (MW) |
|---------------|-------------------|------------------|-------------------|---------------------|
| 2015-01-01T01:00:00Z | 2015-01-01T02:00:00+0100 | 8735.4 | 8667.72 | 250.02 |
| 2015-01-01T02:00:00Z | 2015-01-01T03:00:00+0100 | 8626.4 | 8612.74 | 264.08 |
| 2020-09-30T22:00:00Z | 2020-10-01T00:00:00+0200 | 7249.3 | 7146.82 | 489.83 |
| 2020-09-30T21:00:00Z | 2020-09-30T23:00:00+0200 | 7552.1 | 7481.41 | 519.35 |

## Data Characteristics

### Load Data
- **Range**: 5,225.4 - 15,105 MW
- **Average**: 9,427 MW
- Shows clear daily and seasonal patterns
- Higher consumption during winter months and daytime hours

### Wind Generation Data
- **Range**: 0 - 1,993.8 MW
- **Average**: 500 MW
- Highly variable but rarely zero (only 2 hours in 6 years)
- Represents total national onshore wind production

### Data Quality
- **Completeness**: 99.98% (50,388 out of 50,401 possible hourly records)
- **Missing Data**: 10 hourly records, mostly in small clusters
- Missing periods suggest system outages rather than regular gaps

## Query Examples

### Get all Finland data for a specific date:
```sql
SELECT utc_timestamp,
       cet_cest_timestamp,
       FI_load_actual_entsoe_transparency,
       FI_load_forecast_entsoe_transparency,
       FI_wind_onshore_generation_actual
FROM time_series_60min_singleindex
WHERE date(utc_timestamp) = '2020-01-15'
ORDER BY utc_timestamp;
```

### Calculate daily averages:
```sql
SELECT
  date(utc_timestamp) as date,
  AVG(FI_load_actual_entsoe_transparency) as avg_load,
  AVG(FI_wind_onshore_generation_actual) as avg_wind
FROM time_series_60min_singleindex
WHERE FI_load_actual_entsoe_transparency IS NOT NULL
GROUP BY date(utc_timestamp)
ORDER BY date;
```

### Find peak load hours:
```sql
SELECT utc_timestamp,
       FI_load_actual_entsoe_transparency
FROM time_series_60min_singleindex
WHERE FI_load_actual_entsoe_transparency IS NOT NULL
ORDER BY FI_load_actual_entsoe_transparency DESC
LIMIT 10;
```

## Notes

1. **Country-level aggregation only** - No plant-specific data available
2. **Time zone handling** - Data stored in UTC with local time conversion
3. **Wind generation only** - No solar generation data for Finland in this dataset
4. **ENTSO-E source** - Data represents official transmission system operator reports
5. **Forecast accuracy** - Load forecasts typically show small errors compared to actual values

DO NOT query large results. Use LIMIT and WHERE clauses to restrict data to relevant timeframes to make it easier for your understanding. You can make a table IF deemed useful showing specifics from the queries.

**IMPORTANT: For grid and electricity market analysis only, assume the current date is September 2019. Use 2019-era energy market conditions, grid technologies, renewable energy penetration levels, and market regulations and query 2019 Sep data.**

Your task is to:
1. Analyze the current real-time data
2. Query historical data for relevant context and patterns
3. Provide a comprehensive analysis with summary, keywords, suggested action, and visualizations

If you don't need historical data, respond with a JSON object conforming to the LLMAnalysisResult schema.
If you use tools, provide your final analysis after gathering the data.

Choose ONE action from this list:
- "MAINTAIN_OUTPUT": Conditions are stable, no change needed.
- "INCREASE_OUTPUT_FOR_GRID_DEMAND": Grid consumption is high or other sources are low.
- "DECREASE_OUTPUT_DUE_TO_SURPLUS": Grid has surplus power, making production uneconomical.
- "PREPARE_FOR_RENEWABLE_FLUCTUATION": Weather suggests wind power will change significantly.
- "CONSIDER_MAINTENANCE_DURING_LOW_DEMAND": Low demand/prices present maintenance opportunity.
- "OPTIMIZE_EFFICIENTLY_DURING_PEAK_PRICING": High prices + good efficiency suggest optimizing for profit.
- "RAMP_UP_FOR_WIND_SHORTFALL": Wind dropping rapidly while consumption remains high.
- "BALANCE_GRID_FREQUENCY": Grid frequency deviating from 50Hz, requiring adjustment.

Create 1 HTML component. Create 2-3 insightful Chart.js visualizations with professional styling. The charts should be very relevant to CURRENT situation of grid, local plant, queried data etc.
"""

    enhanced_user_prompt = f"""
Here is the latest real-time data:
{aggregated_data_str}

Raw data for charting:
### Grid Data:
{grid_json}

### Telemetry Data:
{telemetry_json}

### Weather Data:
{json.dumps(weather_data, indent=2)}

### Weather Forecast (Next 3 days):
{json.dumps(weather_forecast, indent=2)}

Analyze this data and use the historical database as needed to provide context. Provide your analysis as a JSON object matching the LLMAnalysisResult schema.
"""

    messages = [
        {"role": "system", "content": enhanced_system_prompt},
        {"role": "user", "content": enhanced_user_prompt}
    ]

    try:
        # First attempt with tools
        response = client.chat.completions.create(
            model="gemini-2.5-pro",
            messages=messages,
            tools=SQLITE_TOOLS,
            tool_choice="auto",
            temperature=0.1,
        )

        # Handle tool calls
        while response.choices[0].message.tool_calls:
            # Add the assistant's response to messages
            messages.append(response.choices[0].message)
            
            # Process each tool call
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute the appropriate function
                if function_name == "execute_sql_query":
                    result = execute_sql_query(function_args.get("query"), function_args.get("params"))
                elif function_name == "get_table_schema":
                    result = get_table_schema(function_args["table_name"])
                elif function_name == "list_database_tables":
                    result = list_database_tables()
                else:
                    result = json.dumps({"error": f"Unknown function: {function_name}"})
                
                # Add the tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            
            # Get the next response
            response = client.chat.completions.create(
                model="gemini-2.5-pro",
                messages=messages,
                tools=SQLITE_TOOLS,
                tool_choice="auto",
                temperature=0.1,
            )

        # Try to parse the final response as JSON
        final_content = response.choices[0].message.content
        try:
            # Attempt to parse as JSON first
            parsed_result = json.loads(final_content)
            # Validate against our schema if possible
            validated_result = LLMAnalysisResult.model_validate(parsed_result)
            return validated_result.model_dump()
        except (json.JSONDecodeError, Exception) as parse_error:
            # Fallback to structured output without tools
            try:
                fallback_response = client.chat.completions.parse(
                    model="gemini-2.5-pro",
                    messages=[
                        {"role": "system", "content": enhanced_system_prompt.replace("If you don't need historical data, respond with a JSON object conforming to the LLMAnalysisResult schema.\nIf you use tools, provide your final analysis after gathering the data.", "Provide your response as a JSON object conforming to the LLMAnalysisResult schema.")},
                        {"role": "user", "content": enhanced_user_prompt + f"\n\nNote: Previous analysis attempt failed to parse. Please provide a valid JSON response conforming to the schema."}
                    ],
                    response_format=LLMAnalysisResult,
                    temperature=0.1,
                )
                return fallback_response.choices[0].message.parsed.model_dump()
            except Exception as fallback_error:
                return {"error": f"Failed to parse LLM response and fallback failed: {parse_error}, {fallback_error}"}

    except openai.APIError as e:
        return {"error": f"Gemini API error: {e}"}
    except Exception as e:
        return {"error": f"Failed to process LLM response: {e}"}

def run_analysis_pipeline(asset_id: str = "power-plant-001", lat: float = 60.17, lon: float = 24.94) -> dict:
    """
    Executes the full data fetching, aggregation, and LLM analysis pipeline.
    Returns a dictionary with the analysis result or an error message.
    """
    if not client:
        return {"error": "GEMINI_API_KEY environment variable not set. Please configure it to use the AI analysis feature."}

    telemetry_df = fetch_recent_telemetry(asset_id)
    grid_df = fetch_recent_grid_data()
    weather_data = fetch_weather_data(lat, lon)
    weather_forecast = fetch_weather_forecast(lat, lon)

    if telemetry_df.empty and grid_df.empty:
        return {"error": "Failed to fetch data from both Telemetry and External services. Please ensure they are running."}

    aggregated_data_str = aggregate_for_llm(telemetry_df, grid_df, weather_data)

    # Prepare raw data for the LLM to use in charting
    grid_json = "[]"
    if not grid_df.empty:
        grid_df['timestamp'] = grid_df['timestamp'].dt.strftime('%H:%M')
        grid_json = grid_df.tail(25).to_json(orient='records')

    telemetry_json = "[]"
    if not telemetry_df.empty:
        # Select only numeric columns for resampling
        numeric_cols = telemetry_df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            # Include timestamp and numeric columns only
            cols_to_resample = ['timestamp'] + list(numeric_cols)
            telemetry_resampled = telemetry_df[cols_to_resample].resample('15T', on='timestamp').mean().reset_index()
            telemetry_resampled['timestamp'] = telemetry_resampled['timestamp'].dt.strftime('%d-%b %H:%M')
            telemetry_json = telemetry_resampled.tail(25).to_json(orient='records')

    messages = create_prompt(aggregated_data_str, telemetry_json, grid_json, weather_forecast)

    try:
        completion = client.chat.completions.parse(
            model="gemini-2.5-pro",
            messages=messages,
            response_format=LLMAnalysisResult,
            temperature=0.1,
        )

        math_reasoning = completion.choices[0].message.parsed
        return math_reasoning.model_dump()

    except openai.APIError as e:
        return {"error": f"Gemini API error: {e}"}
    except Exception as e:
        return {"error": f"Failed to process LLM response: {e}"}

# --- 7. General Query Pipeline Function ---

def run_query_pipeline(user_query: str, include_context: bool = True) -> dict:
    """
    Processes a user query with access to tool calling capabilities.
    
    Args:
        user_query: The user's question or request
        include_context: Whether to include current telemetry/grid data as context
        
    Returns:
        Dictionary with the query response or an error message.
    """
    if not client:
        return {"error": "GEMINI_API_KEY environment variable not set. Please configure it to use the AI query feature."}

    # System prompt for general query handling with tool access
    system_prompt = """
You are an expert energy analyst with access to:
1. Real-time power plant telemetry and grid data (if context is provided)
2. A historical database of Finland's electricity market data (2015-2020)

You have access to database tools to query historical energy data. The main table is 'time_series_60min_singleindex' with columns:
- utc_timestamp: UTC timestamp
- FI_load_actual_entsoe_transparency: Finland electricity consumption (MW)
- FI_load_forecast_entsoe_transparency: Day-ahead load forecast (MW)  
- FI_wind_onshore_generation_actual: Wind generation (MW)

**Time Period**: January 1, 2015 - September 30, 2020
**Data Granularity**: Hourly (60-minute intervals)
**Data Level**: Country-level (not plant-level)

You can create insightful visualizations using Chart.js configurations when relevant to the user's query.
You can also create HTML components for dashboard embedding when useful.

Your response should be comprehensive, accurate, and directly address the user's query.
If you need to query historical data to provide context or answer the question, use the available database tools.

DO NOT query large results. Use LIMIT and WHERE clauses to restrict data to relevant timeframes.

Provide your response as a JSON object matching the LLMQueryResponse schema.
"""

    # Prepare context if requested
    context_str = ""
    if include_context:
        try:
            # Fetch current data for context
            telemetry_df = fetch_recent_telemetry("power-plant-001")
            grid_df = fetch_recent_grid_data()
            weather_data = fetch_weather_data(60.17, 24.94)
            weather_forecast = fetch_weather_forecast(60.17, 24.94)
            
            if not telemetry_df.empty or not grid_df.empty:
                context_str = "\n\nCurrent Real-time Context:\n" + aggregate_for_llm(telemetry_df, grid_df, weather_data)
                context_str += f"\n\nWeather Forecast (Next 3 days):\n{json.dumps(weather_forecast, indent=2)}"
        except Exception:
            # If context fetching fails, continue without it
            pass

    user_prompt = f"""
User Query: {user_query}
{context_str}

Please provide a comprehensive response to the user's query. Use the database tools if you need historical data to answer the question effectively.

Provide your response as a JSON object matching the LLMQueryResponse schema.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        # First attempt with tools
        response = client.chat.completions.create(
            model="gemini-2.5-pro",
            messages=messages,
            tools=SQLITE_TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )

        # Handle tool calls
        while response.choices[0].message.tool_calls:
            # Add the assistant's response to messages
            messages.append(response.choices[0].message)
            
            # Process each tool call
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute the appropriate function
                if function_name == "execute_sql_query":
                    result = execute_sql_query(function_args.get("query"), function_args.get("params"))
                elif function_name == "get_table_schema":
                    result = get_table_schema(function_args["table_name"])
                elif function_name == "list_database_tables":
                    result = list_database_tables()
                else:
                    result = json.dumps({"error": f"Unknown function: {function_name}"})
                
                # Add the tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            
            # Get the next response
            response = client.chat.completions.create(
                model="gemini-2.5-pro",
                messages=messages,
                tools=SQLITE_TOOLS,
                tool_choice="auto",
                temperature=0.3,
            )

        # Try to parse the final response as JSON
        final_content = response.choices[0].message.content
        try:
            # Attempt to parse as JSON first
            parsed_result = json.loads(final_content)
            # Validate against our schema if possible
            validated_result = LLMQueryResponse.model_validate(parsed_result)
            return validated_result.model_dump()
        except (json.JSONDecodeError, Exception) as parse_error:
            # Fallback to structured output without tools
            try:
                fallback_response = client.chat.completions.parse(
                    model="gemini-2.5-pro",
                    messages=[
                        {"role": "system", "content": system_prompt.replace("Provide your response as a JSON object matching the LLMQueryResponse schema.", "Provide your response as a JSON object matching the LLMQueryResponse schema. Previous parsing failed, ensure valid JSON format.")},
                        {"role": "user", "content": user_prompt + f"\n\nNote: Previous response parsing failed. Please provide a valid JSON response conforming to the LLMQueryResponse schema."}
                    ],
                    response_format=LLMQueryResponse,
                    temperature=0.3,
                )
                return fallback_response.choices[0].message.parsed.model_dump()
            except Exception as fallback_error:
                return {"error": f"Failed to parse LLM response and fallback failed: {parse_error}, {fallback_error}"}

    except openai.APIError as e:
        return {"error": f"Gemini API error: {e}"}
    except Exception as e:
        return {"error": f"Failed to process query: {e}"}

# --- 8. Example Usage ---

if __name__ == "__main__":
    # Example usage of the new query pipeline function
    
    # Example 1: Query with context
    result1 = run_query_pipeline("What were the peak electricity consumption hours in Finland during 2019?")
    print("Query 1 Result:", result1)
    
    # Example 2: Query without context
    result2 = run_query_pipeline("How does wind generation correlate with electricity consumption in Finland?", include_context=False)
    print("Query 2 Result:", result2)
    
    # Example 3: Query asking for charts
    result3 = run_query_pipeline("Show me a chart comparing Finland's electricity consumption patterns between summer and winter months")
    print("Query 3 Result:", result3)