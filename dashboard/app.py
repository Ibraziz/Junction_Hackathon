import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Combined Energy Monitoring Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
API_BASE_URL = "http://localhost:8002"
EXTERNAL_API_URL = "http://localhost:8000"

def fetch_telemetry_data(asset_id: str, start_time: str, end_time: str):
    """Fetch telemetry data from the API."""
    try:
        url = f"{API_BASE_URL}/telemetry/{asset_id}"
        params = {
            "start_time": start_time,
            "end_time": end_time
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching telemetry data: {e}")
        return None

def check_api_health():
    """Check if the telemetry API server is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def check_external_service_health():
    """Check if the external service is running."""
    try:
        response = requests.get(f"{EXTERNAL_API_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def fetch_external_data():
    """Fetch real data from external service."""
    try:
        # Fetch nuclear power data
        nuclear_response = requests.get(f"{EXTERNAL_API_URL}/api/production/nuclear-power", timeout=10)
        nuclear_data = nuclear_response.json()['data'] if nuclear_response.status_code == 200 else []
        
        # Fetch wind power data
        wind_response = requests.get(f"{EXTERNAL_API_URL}/api/production/wind-power", timeout=10)
        wind_data = wind_response.json()['data'] if wind_response.status_code == 200 else []
        
        # Fetch electricity consumption data
        consumption_response = requests.get(f"{EXTERNAL_API_URL}/api/consumption/electricity", timeout=10)
        consumption_data = consumption_response.json()['data'] if consumption_response.status_code == 200 else []
        
        # Fetch grid frequency data
        frequency_response = requests.get(f"{EXTERNAL_API_URL}/api/grid/frequency", timeout=10)
        frequency_data = frequency_response.json()['data'] if frequency_response.status_code == 200 else []
        
        # Process and combine the data
        processed_data = []
        
        # Use the dataset with most data points as the base
        datasets = [
            ('nuclear_power', nuclear_data),
            ('wind_power', wind_data),
            ('consumption', consumption_data),
            ('grid_frequency', frequency_data)
        ]
        
        # Find the maximum length to determine how many data points we can use
        max_length = max(len(data) for _, data in datasets) if datasets else 0
        
        if max_length == 0:
            raise Exception("No data received from external service")
        
        # Take up to 50 most recent data points to avoid overwhelming the dashboard
        limit = min(50, max_length)
        
        for i in range(limit):
            data_point = {}
            
            # Extract nuclear power data
            if i < len(nuclear_data):
                data_point['nuclear_power'] = nuclear_data[i]['value']
                data_point['timestamp'] = nuclear_data[i]['startTime']
            
            # Extract wind power data
            if i < len(wind_data):
                data_point['wind_power'] = wind_data[i]['value']
                if 'timestamp' not in data_point:
                    data_point['timestamp'] = wind_data[i]['startTime']
            
            # Extract consumption data
            if i < len(consumption_data):
                data_point['consumption'] = consumption_data[i]['value']
                if 'timestamp' not in data_point:
                    data_point['timestamp'] = consumption_data[i]['startTime']
            
            # Extract grid frequency data
            if i < len(frequency_data):
                data_point['grid_frequency'] = frequency_data[i]['value']
                if 'timestamp' not in data_point:
                    data_point['timestamp'] = frequency_data[i]['startTime']
            
            # Only add if we have at least timestamp and one data field
            if 'timestamp' in data_point and len(data_point) > 1:
                processed_data.append(data_point)
        
        return processed_data
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching external data: {e}")
        return []
    except Exception as e:
        st.error(f"Error processing external data: {e}")
        return []

def main():
    # Header
    st.title("⚡ Combined Energy Monitoring Dashboard")
    st.markdown("**Real-time power plant telemetry and national energy grid data for the last week**")
    st.markdown("---")
    
    # Check service health
    telemetry_healthy = check_api_health()
    external_healthy = check_external_service_health()
    
    if not telemetry_healthy:
        st.error("🚫 Cannot connect to the telemetry API server. Please ensure it's running on port 8002.")
        st.info("💡 To start the server, run: `python main.py --port 8002` in the telemetry-service directory")
        return
    
    if not external_healthy:
        st.warning("⚠️ External service (port 8000) is not available. National energy data will not be displayed.")
        st.info("💡 To start the external service, run: `python app.py` in the external-service directory")
    
    # Fixed parameters - no user options
    asset_id = "power-plant-001"
    
    # Fixed time range - last week
    now = datetime.now()
    end_datetime = now - timedelta(days=1)  # Yesterday
    start_datetime = end_datetime - timedelta(days=7)  # 7 days before yesterday
    
    # Format for API
    start_time_str = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time_str = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Service status and data info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"📊 Data Period: {start_datetime.strftime('%Y-%m-%d')} to {end_datetime.strftime('%Y-%m-%d')}")
    with col2:
        if telemetry_healthy:
            st.success("✅ Telemetry Service: Connected")
        else:
            st.error("❌ Telemetry Service: Offline")
    with col3:
        if external_healthy:
            st.success("✅ External Service: Connected") 
        else:
            st.error("❌ External Service: Offline")
    
    # Main content area - always display data
    # Fetch telemetry data
    with st.spinner("🔄 Fetching telemetry data..."):
        telemetry_data = fetch_telemetry_data(asset_id, start_time_str, end_time_str)
    
    # Fetch external service data
    with st.spinner("🔄 Fetching external energy data..."):
        external_data = fetch_external_data()
    
    if telemetry_data:
        
        # Convert telemetry data to DataFrame for easier manipulation
        df = pd.DataFrame(telemetry_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Convert external data to DataFrame
        if external_data:
            external_df = pd.DataFrame(external_data)
            external_df['timestamp'] = pd.to_datetime(external_df['timestamp'])
        else:
            external_df = pd.DataFrame()
        
        # Display data overview
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"✅ Power Plant Data: {len(df)} data points")
        with col2:
            if len(external_df) > 0:
                st.success(f"✅ Grid Data: {len(external_df)} data points")
            else:
                st.warning("⚠️ External service data unavailable")
            
        # Simplified Key Metrics Overview
        st.subheader("📋 Power Plant Performance Overview")
        
        # Primary metrics row - Power Plant
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_power = df['power_gen_MW'].mean()
            max_power = df['power_gen_MW'].max()
            st.metric(
                "Plant Power Output", 
                f"{avg_power:.1f} MW",
                delta=f"Peak: {max_power:.1f} MW"
            )
        
        with col2:
            avg_efficiency = df['efficiency_percent'].mean()
            st.metric(
                "Plant Efficiency", 
                f"{avg_efficiency:.1f}%"
            )
        
        with col3:
            if len(external_df) > 0 and 'nuclear_power' in external_df.columns:
                avg_nuclear = external_df['nuclear_power'].mean()
                st.metric(
                    "National Nuclear", 
                    f"{avg_nuclear:.0f} MW"
                )
            else:
                st.metric("National Nuclear", "N/A")
        
        with col4:
            if len(external_df) > 0 and 'wind_power' in external_df.columns:
                avg_wind = external_df['wind_power'].mean()
                st.metric(
                    "National Wind", 
                    f"{avg_wind:.0f} MW"
                )
            else:
                st.metric("National Wind", "N/A")

        st.markdown("---")
        
        # Chart 1: Power Plant Generation
        st.subheader("📈 Power Plant Generation Over Time")
        
        fig_plant = go.Figure()
        
        # Add power generation
        fig_plant.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['power_gen_MW'],
                mode='lines+markers',
                name='Plant Power Output',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=6),
                hovertemplate='<b>Plant Power</b><br>Time: %{x}<br>Power: %{y:.1f} MW<extra></extra>'
            )
        )
        
        fig_plant.update_layout(
            title='Power Plant Output',
            xaxis_title='Time',
            yaxis_title='Power Generation (MW)',
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_plant, use_container_width=True)
        
        # Chart 2: National Energy Production Mix
        st.subheader("⚡ National Energy Production Mix")
        
        if len(external_df) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                fig_energy = go.Figure()
                
                # Add nuclear power if available
                if 'nuclear_power' in external_df.columns:
                    fig_energy.add_trace(
                        go.Scatter(
                            x=external_df['timestamp'],
                            y=external_df['nuclear_power'],
                            mode='lines+markers',
                            name='Nuclear Power',
                            line=dict(color='#ff6b35', width=3),
                            marker=dict(size=5),
                            hovertemplate='<b>Nuclear</b><br>Time: %{x}<br>Power: %{y:.0f} MW<extra></extra>'
                        )
                    )
                
                # Add wind power if available
                if 'wind_power' in external_df.columns:
                    fig_energy.add_trace(
                        go.Scatter(
                            x=external_df['timestamp'],
                            y=external_df['wind_power'],
                            mode='lines+markers',
                            name='Wind Power',
                            line=dict(color='#2ca02c', width=3),
                            marker=dict(size=5),
                            hovertemplate='<b>Wind</b><br>Time: %{x}<br>Power: %{y:.0f} MW<extra></extra>'
                        )
                    )
                
                fig_energy.update_layout(
                    title='Energy Production by Source',
                    xaxis_title='Time',
                    yaxis_title='Power (MW)',
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig_energy, use_container_width=True)
            
            with col2:
                # Chart 3: Grid Frequency and Consumption
                fig_grid = go.Figure()
                
                # Add consumption if available
                if 'consumption' in external_df.columns:
                    fig_grid.add_trace(
                        go.Scatter(
                            x=external_df['timestamp'],
                            y=external_df['consumption'],
                            mode='lines+markers',
                            name='Electricity Consumption',
                            line=dict(color='#d62728', width=3),
                            marker=dict(size=5),
                            yaxis='y1',
                            hovertemplate='<b>Consumption</b><br>Time: %{x}<br>Power: %{y:.0f} MW<extra></extra>'
                        )
                    )
                
                # Add grid frequency if available
                if 'grid_frequency' in external_df.columns:
                    fig_grid.add_trace(
                        go.Scatter(
                            x=external_df['timestamp'],
                            y=external_df['grid_frequency'],
                            mode='lines+markers',
                            name='Grid Frequency',
                            line=dict(color='#9467bd', width=2),
                            marker=dict(size=5),
                            yaxis='y2',
                            hovertemplate='<b>Frequency</b><br>Time: %{x}<br>Freq: %{y:.2f} Hz<extra></extra>'
                        )
                    )
                
                fig_grid.update_layout(
                    title='Grid Performance',
                    xaxis_title='Time',
                    yaxis=dict(
                        title='Consumption (MW)',
                        side='left'
                    ),
                    yaxis2=dict(
                        title='Frequency (Hz)',
                        overlaying='y',
                        side='right'
                    ),
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig_grid, use_container_width=True)
        else:
            st.info("🔄 External energy data is not available. Check external service connection.")
    else:
        st.error("❌ Failed to fetch telemetry data. Please check the telemetry service.")

if __name__ == "__main__":
    main()