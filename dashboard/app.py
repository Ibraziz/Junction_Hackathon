import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Power Plant Monitoring Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
TELEMETRY_API_URL = "http://localhost:8002"
EXTERNAL_API_URL = "http://localhost:8000"

def check_telemetry_health():
    """Check if the telemetry API server is running."""
    try:
        response = requests.get(f"{TELEMETRY_API_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def check_external_health():
    """Check if the external service is running."""
    try:
        response = requests.get(f"{EXTERNAL_API_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def fetch_telemetry_data(asset_id: str, start_time: str, end_time: str):
    """Fetch telemetry data from the API."""
    try:
        url = f"{TELEMETRY_API_URL}/telemetry/{asset_id}"
        params = {
            "start_time": start_time,
            "end_time": end_time
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching telemetry data: {e}")
        return None

def fetch_external_data_endpoint(endpoint: str):
    """Fetch data from a specific external service endpoint."""
    try:
        url = f"{EXTERNAL_API_URL}/{endpoint}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', []) if 'data' in data else []
        return []
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not fetch {endpoint}: {e}")
        return []

def main():
    # Header
    st.title("⚡ Power Plant Monitoring Dashboard")
    st.markdown("**Real-time power plant telemetry and Finnish national energy grid data**")
    st.markdown("---")
    
    # Check service health
    telemetry_healthy = check_telemetry_health()
    external_healthy = check_external_health()
    
    # Service status
    col1, col2 = st.columns(2)
    with col1:
        if telemetry_healthy:
            st.success("✅ Telemetry Service: Connected")
        else:
            st.error("❌ Telemetry Service: Offline")
            
    with col2:
        if external_healthy:
            st.success("✅ External Service: Connected") 
        else:
            st.error("❌ External Service: Offline")
    
    if not telemetry_healthy:
        st.error("🚫 Cannot connect to the telemetry API server. Please ensure it's running on port 8002.")
        return
    
    # Fixed parameters
    asset_id = "GEN-001"
    now = datetime.now()
    end_datetime = now - timedelta(hours=1)  # 1 hour ago
    start_datetime = end_datetime - timedelta(hours=24)  # 24 hours of data
    
    start_time_str = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time_str = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    st.info(f"📊 Showing data from {start_datetime.strftime('%Y-%m-%d %H:%M')} to {end_datetime.strftime('%Y-%m-%d %H:%M')}")
    
    # Fetch telemetry data
    with st.spinner("🔄 Fetching power plant telemetry data..."):
        telemetry_data = fetch_telemetry_data(asset_id, start_time_str, end_time_str)
    
    if not telemetry_data:
        st.error("❌ Failed to fetch telemetry data. Please check the telemetry service.")
        return
    
    # Convert telemetry data to DataFrame
    df = pd.DataFrame(telemetry_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Display telemetry data summary
    st.success(f"✅ Retrieved {len(df)} telemetry data points")
    
    # Key Performance Metrics - Telemetry Only
    st.subheader("🏭 Power Plant Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_power = df['power_gen_MW'].mean()
        max_power = df['power_gen_MW'].max()
        st.metric(
            "Average Power Output", 
            f"{avg_power:.1f} MW",
            delta=f"Peak: {max_power:.1f} MW"
        )
    
    with col2:
        avg_efficiency = df['efficiency_percent'].mean()
        st.metric(
            "Average Efficiency", 
            f"{avg_efficiency:.1f}%"
        )
    
    with col3:
        avg_fuel_flow = df['fuel_flow_kg_h'].mean()
        st.metric(
            "Avg Fuel Consumption", 
            f"{avg_fuel_flow:.0f} kg/h"
        )
    
    with col4:
        avg_engine_load = df['engine_load_percent'].mean()
        st.metric(
            "Average Engine Load", 
            f"{avg_engine_load:.1f}%"
        )
    
    st.markdown("---")
    
    # Chart 1: Power Plant Generation Over Time
    st.subheader("📈 Power Plant Generation Over Time")
    
    fig_plant = go.Figure()
    
    fig_plant.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['power_gen_MW'],
            mode='lines+markers',
            name='Power Output',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=4),
            hovertemplate='<b>Power Output</b><br>Time: %{x}<br>Power: %{y:.1f} MW<extra></extra>'
        )
    )
    
    fig_plant.update_layout(
        title='Power Generation Output',
        xaxis_title='Time',
        yaxis_title='Power Generation (MW)',
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig_plant, use_container_width=True)
    
    # Fetch external data if available
    external_data = {}
    if external_healthy:
        with st.spinner("🔄 Fetching national energy data..."):
            external_data['nuclear'] = fetch_external_data_endpoint('api/production/nuclear-power')
            external_data['wind'] = fetch_external_data_endpoint('api/production/wind-power')
            external_data['hydro'] = fetch_external_data_endpoint('api/production/hydro-power')
            external_data['consumption'] = fetch_external_data_endpoint('api/consumption/electricity')
            external_data['emission'] = fetch_external_data_endpoint('api/market/emission-factor')
    
    # Display external data availability
    if external_healthy and any(external_data.values()):
        available_sources = [k for k, v in external_data.items() if v]
        st.success(f"✅ National grid data available: {', '.join(available_sources)}")
        
        # Chart 2: Power Generation Mix Pie Chart
        st.subheader("🥧 Finnish Energy Production Mix")
        
        # Calculate average values for each power type
        power_averages = {}
        power_sources = ['nuclear', 'wind', 'hydro']
        
        for source in power_sources:
            if external_data.get(source):
                source_data = external_data[source]
                if source_data:
                    values = [item['value'] for item in source_data if 'value' in item]
                    if values:
                        power_averages[source.title()] = sum(values) / len(values)
        
        if power_averages:
            # Create pie chart
            fig_pie = go.Figure(data=[go.Pie(
                labels=list(power_averages.keys()),
                values=list(power_averages.values()),
                hole=0.3,
                marker_colors=['#ff6b35', '#2ca02c', '#17becf'],
                textinfo='label+percent+value',
                texttemplate='<b>%{label}</b><br>%{percent}<br>%{value:.0f} MW',
                hovertemplate='<b>%{label}</b><br>Average Power: %{value:.0f} MW<br>Share: %{percent}<extra></extra>'
            )])
            
            fig_pie.update_layout(
                title='Average Power Generation Distribution',
                height=400,
                annotations=[dict(text='Energy<br>Sources', x=0.5, y=0.5, font_size=14, showarrow=False)]
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("⚠️ No power generation data available for pie chart")
        
        # Chart 3: Electricity Consumption and Emission Factor (Separate Charts)
        if external_data.get('consumption') or external_data.get('emission'):
            st.subheader("📊 National Electricity Metrics")
            
            col1, col2 = st.columns(2)
            
            # Left column: Electricity Consumption
            with col1:
                if external_data.get('consumption'):
                    consumption_data = external_data['consumption']
                    consumption_df = pd.DataFrame(consumption_data)
                    
                    if not consumption_df.empty and 'startTime' in consumption_df.columns:
                        consumption_df['timestamp'] = pd.to_datetime(consumption_df['startTime'])
                        consumption_df = consumption_df.sort_values('timestamp').tail(50)  # Last 50 points
                        
                        fig_consumption = go.Figure()
                        
                        fig_consumption.add_trace(
                            go.Scatter(
                                x=consumption_df['timestamp'],
                                y=consumption_df['value'],
                                mode='lines+markers',
                                name='Electricity Consumption',
                                line=dict(color='#d62728', width=3),
                                marker=dict(size=4),
                                fill='tonexty',
                                fillcolor='rgba(214, 39, 40, 0.1)',
                                hovertemplate='<b>Consumption</b><br>Time: %{x}<br>Power: %{y:.0f} MW<extra></extra>'
                            )
                        )
                        
                        fig_consumption.update_layout(
                            title='National Electricity Consumption',
                            xaxis_title='Time',
                            yaxis_title='Consumption (MW)',
                            height=400,
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig_consumption, use_container_width=True)
                    else:
                        st.warning("⚠️ No consumption data available")
                else:
                    st.warning("⚠️ Consumption data not available")
            
            # Right column: Emission Factor
            with col2:
                if external_data.get('emission'):
                    emission_data = external_data['emission']
                    emission_df = pd.DataFrame(emission_data)
                    
                    if not emission_df.empty and 'startTime' in emission_df.columns:
                        emission_df['timestamp'] = pd.to_datetime(emission_df['startTime'])
                        emission_df = emission_df.sort_values('timestamp').tail(50)  # Last 50 points
                        
                        fig_emission = go.Figure()
                        
                        fig_emission.add_trace(
                            go.Scatter(
                                x=emission_df['timestamp'],
                                y=emission_df['value'],
                                mode='lines+markers',
                                name='Emission Factor',
                                line=dict(color='#ff7f0e', width=3),
                                marker=dict(size=4),
                                fill='tonexty',
                                fillcolor='rgba(255, 127, 14, 0.1)',
                                hovertemplate='<b>Emissions</b><br>Time: %{x}<br>Factor: %{y:.1f} gCO2/kWh<extra></extra>'
                            )
                        )
                        
                        fig_emission.update_layout(
                            title='Carbon Emission Factor',
                            xaxis_title='Time',
                            yaxis_title='Emission Factor (gCO2/kWh)',
                            height=400,
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig_emission, use_container_width=True)
                    else:
                        st.warning("⚠️ No emission data available")
                else:
                    st.warning("⚠️ Emission data not available")
        else:
            st.warning("⚠️ No external data available for consumption or emissions")
    
    else:
        st.error("❌ Failed to fetch telemetry data. Please check the telemetry service.")

if __name__ == "__main__":
    main()