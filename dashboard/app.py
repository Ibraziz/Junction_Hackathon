import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Power Plant Telemetry Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_BASE_URL = "http://localhost:8002"

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
        st.error(f"Error fetching data: {e}")
        return None

def check_api_health():
    """Check if the API server is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def main():
    # Header
    st.title("⚡ Power Plant Telemetry Dashboard")
    st.markdown("---")
    
    # Check API health
    if not check_api_health():
        st.error("🚫 Cannot connect to the telemetry API server. Please ensure it's running on port 8002.")
        st.info("💡 To start the server, run: `python main.py --port 8002` in the telemetry-service directory")
        return
    
    # Sidebar for controls
    with st.sidebar:
        st.header("📊 Dashboard Controls")
        
        # Asset selection
        asset_id = st.text_input(
            "Asset ID", 
            value="power-plant-001",
            help="Enter the ID of the power plant asset"
        )
        
        st.markdown("### 📅 Time Range Selection")
        
        # Date and time inputs
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now().date() - timedelta(days=1),
                help="Select the start date for data retrieval"
            )
            start_time = st.time_input(
                "Start Time",
                value=datetime.now().time().replace(hour=10, minute=0, second=0, microsecond=0),
                help="Select the start time"
            )
        
        with col2:
            end_date = st.date_input(
                "End Date", 
                value=datetime.now().date() - timedelta(days=1),
                help="Select the end date for data retrieval"
            )
            end_time = st.time_input(
                "End Time",
                value=datetime.now().time().replace(hour=12, minute=0, second=0, microsecond=0),
                help="Select the end time"
            )
        
        # Quick time range buttons
        st.markdown("### ⚡ Quick Select")
        col1, col2 = st.columns(2)
        
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        with col1:
            if st.button("Last 1 Hour"):
                start_date = yesterday.date()
                start_time = yesterday.replace(hour=10, minute=0, second=0, microsecond=0).time()
                end_date = yesterday.date()
                end_time = yesterday.replace(hour=11, minute=0, second=0, microsecond=0).time()
        
        with col2:
            if st.button("Last 6 Hours"):
                start_date = yesterday.date()
                start_time = yesterday.replace(hour=6, minute=0, second=0, microsecond=0).time()
                end_date = yesterday.date()
                end_time = yesterday.replace(hour=12, minute=0, second=0, microsecond=0).time()
        
        # Combine date and time
        start_datetime = datetime.combine(start_date, start_time)
        end_datetime = datetime.combine(end_date, end_time)
        
        # Format for API
        start_time_str = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time_str = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Fetch data button
        fetch_data = st.button("🔄 Fetch Data", type="primary", use_container_width=True)
    
    # Main content area
    if fetch_data or 'telemetry_data' in st.session_state:
        if fetch_data:
            # Validate time range
            if start_datetime >= end_datetime:
                st.error("❌ Start time must be before end time!")
                return
            
            duration = end_datetime - start_datetime
            if duration.total_seconds() > 7 * 24 * 60 * 60:  # 7 days
                st.error("❌ Time range cannot exceed 7 days!")
                return
            
            # Fetch data
            with st.spinner("🔄 Fetching telemetry data..."):
                data = fetch_telemetry_data(asset_id, start_time_str, end_time_str)
                
                if data:
                    st.session_state.telemetry_data = data
                    st.session_state.asset_id = asset_id
                    st.session_state.time_range = f"{start_time_str} to {end_time_str}"
                else:
                    return
        
        # Use cached data if available
        data = st.session_state.get('telemetry_data')
        
        if data:
            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Display data overview
            st.success(f"✅ Successfully loaded {len(df)} data points for asset: {st.session_state.get('asset_id', asset_id)}")
            
            # Enhanced Key metrics summary
            st.subheader("📋 Performance Overview")
            
            # Primary metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_power = df['power_gen_MW'].mean()
                max_power = df['power_gen_MW'].max()
                power_delta = ((max_power - avg_power) / avg_power * 100) if avg_power > 0 else 0
                st.metric(
                    "Average Power", 
                    f"{avg_power:.1f} MW",
                    delta=f"{power_delta:+.1f}% peak variation"
                )
            
            with col2:
                avg_efficiency = df['efficiency_percent'].mean()
                max_efficiency = df['efficiency_percent'].max()
                efficiency_delta = max_efficiency - avg_efficiency
                st.metric(
                    "Average Efficiency", 
                    f"{avg_efficiency:.1f}%",
                    delta=f"{efficiency_delta:+.1f}% peak boost"
                )
            
            with col3:
                avg_load = df['engine_load_percent'].mean()
                load_stability = 100 - (df['engine_load_percent'].std() / avg_load * 100) if avg_load > 0 else 0
                st.metric(
                    "Average Load", 
                    f"{avg_load:.1f}%",
                    delta=f"{load_stability:.1f}% stability"
                )
            
            with col4:
                total_co2 = df['co2_emissions_kg_min'].sum()
                avg_co2_rate = df['co2_emissions_kg_min'].mean()
                st.metric(
                    "Total CO₂ Emissions", 
                    f"{total_co2:.1f} kg",
                    delta=f"{avg_co2_rate:.2f} kg/min avg rate"
                )
            
            # Secondary metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_fuel = df['fuel_flow_kg_h'].mean()
                fuel_efficiency = (df['power_gen_MW'] / df['fuel_flow_kg_h']).mean() if df['fuel_flow_kg_h'].mean() > 0 else 0
                st.metric(
                    "Fuel Consumption", 
                    f"{avg_fuel:.1f} kg/h",
                    delta=f"{fuel_efficiency:.3f} MW/kg·h efficiency"
                )
            
            with col2:
                avg_temp = df['engine_temp_C'].mean()
                temp_range = df['engine_temp_C'].max() - df['engine_temp_C'].min()
                st.metric(
                    "Engine Temperature", 
                    f"{avg_temp:.1f}°C",
                    delta=f"{temp_range:.1f}°C range"
                )
            
            with col3:
                avg_voltage = df['voltage_V'].mean()
                voltage_stability = (1 - df['voltage_V'].std() / avg_voltage) * 100 if avg_voltage > 0 else 0
                st.metric(
                    "Average Voltage", 
                    f"{avg_voltage:.0f} V",
                    delta=f"{voltage_stability:.2f}% stability"
                )
            
            with col4:
                duration_hours = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600
                energy_generated = (df['power_gen_MW'].mean() * duration_hours) if duration_hours > 0 else 0
                st.metric(
                    "Energy Generated", 
                    f"{energy_generated:.2f} MWh",
                    delta=f"{duration_hours:.1f} hours runtime"
                )
            
            st.markdown("---")
            
            # Chart 1: Time Series Plot - Power Generation and Key Metrics
            st.subheader("📈 Power Generation & Key Metrics Over Time")
            
            # Create subplot with secondary y-axis
            fig = go.Figure()
            
            # Add power generation (primary y-axis)
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['power_gen_MW'],
                    mode='lines',
                    name='Power Generation (MW)',
                    line=dict(color='#1f77b4', width=3),
                    hovertemplate='<b>Power Generation</b><br>Time: %{x}<br>Power: %{y:.1f} MW<extra></extra>'
                )
            )
            
            # Add engine load (secondary y-axis)
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['engine_load_percent'],
                    mode='lines',
                    name='Engine Load (%)',
                    line=dict(color='#ff7f0e', width=2, dash='dash'),
                    yaxis='y2',
                    hovertemplate='<b>Engine Load</b><br>Time: %{x}<br>Load: %{y:.1f}%<extra></extra>'
                )
            )
            
            # Add efficiency (secondary y-axis)
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['efficiency_percent'],
                    mode='lines',
                    name='Efficiency (%)',
                    line=dict(color='#2ca02c', width=2),
                    yaxis='y2',
                    hovertemplate='<b>Efficiency</b><br>Time: %{x}<br>Efficiency: %{y:.1f}%<extra></extra>'
                )
            )
            
            # Update layout for dual y-axis
            fig.update_layout(
                title={
                    'text': 'Power Generation, Engine Load, and Efficiency Over Time',
                    'x': 0.5,
                    'xanchor': 'center'
                },
                xaxis=dict(
                    title='Time',
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='lightgray'
                ),
                yaxis=dict(
                    title=dict(text='Power Generation (MW)', font=dict(color='#1f77b4')),
                    tickfont=dict(color='#1f77b4'),
                    side='left'
                ),
                yaxis2=dict(
                    title=dict(text='Percentage (%)', font=dict(color='#ff7f0e')),
                    tickfont=dict(color='#ff7f0e'),
                    anchor='x',
                    overlaying='y',
                    side='right'
                ),
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=1.02,
                    xanchor='right',
                    x=1
                ),
                hovermode='x unified',
                height=500,
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Additional metrics in a second row
            st.subheader("🌡️ Temperature & Emissions Monitoring")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Temperature plot
                fig_temp = go.Figure()
                
                fig_temp.add_trace(
                    go.Scatter(
                        x=df['timestamp'],
                        y=df['engine_temp_C'],
                        mode='lines+markers',
                        name='Engine Temperature',
                        line=dict(color='#d62728', width=2),
                        marker=dict(size=4),
                        hovertemplate='<b>Engine Temp</b><br>Time: %{x}<br>Temp: %{y:.1f}°C<extra></extra>'
                    )
                )
                
                fig_temp.add_trace(
                    go.Scatter(
                        x=df['timestamp'],
                        y=df['ambient_temp_C'],
                        mode='lines+markers',
                        name='Ambient Temperature',
                        line=dict(color='#17becf', width=2),
                        marker=dict(size=4),
                        hovertemplate='<b>Ambient Temp</b><br>Time: %{x}<br>Temp: %{y:.1f}°C<extra></extra>'
                    )
                )
                
                fig_temp.update_layout(
                    title='Temperature Monitoring',
                    xaxis_title='Time',
                    yaxis_title='Temperature (°C)',
                    hovermode='x unified',
                    height=400,
                    showlegend=True
                )
                
                st.plotly_chart(fig_temp, use_container_width=True)
            
            with col2:
                # CO2 Emissions plot
                fig_co2 = go.Figure()
                
                fig_co2.add_trace(
                    go.Scatter(
                        x=df['timestamp'],
                        y=df['co2_emissions_kg_min'],
                        mode='lines+markers',
                        name='CO₂ Emissions',
                        line=dict(color='#8c564b', width=2),
                        marker=dict(size=4),
                        fill='tonexty' if len(df) > 1 else None,
                        fillcolor='rgba(140, 86, 75, 0.2)',
                        hovertemplate='<b>CO₂ Emissions</b><br>Time: %{x}<br>Rate: %{y:.2f} kg/min<extra></extra>'
                    )
                )
                
                fig_co2.update_layout(
                    title='CO₂ Emissions Rate',
                    xaxis_title='Time',
                    yaxis_title='CO₂ Emissions (kg/min)',
                    hovermode='x unified',
                    height=400,
                    showlegend=True
                )
                
                st.plotly_chart(fig_co2, use_container_width=True)
            
            # Chart 2: Correlation Analysis
            st.subheader("🔗 Correlation Analysis")
            
            # Let users select what to compare
            col1, col2 = st.columns(2)
            
            with col1:
                x_metric = st.selectbox(
                    "X-Axis Metric",
                    options=['power_gen_MW', 'fuel_flow_kg_h', 'engine_load_percent', 'engine_rpm', 
                            'engine_temp_C', 'efficiency_percent', 'co2_emissions_kg_min'],
                    index=0,  # default to power_gen_MW
                    key='x_metric'
                )
            
            with col2:
                y_metric = st.selectbox(
                    "Y-Axis Metric",
                    options=['fuel_flow_kg_h', 'co2_emissions_kg_min', 'engine_load_percent', 
                            'engine_temp_C', 'efficiency_percent', 'power_gen_MW', 'engine_rpm'],
                    index=0,  # default to fuel_flow_kg_h
                    key='y_metric'
                )
            
            # Create scatter plot
            fig_scatter = px.scatter(
                df,
                x=x_metric,
                y=y_metric,
                color='engine_load_percent',  # Color by engine load for additional insight
                size='power_gen_MW',  # Size by power generation
                hover_data=['timestamp', 'efficiency_percent'],
                color_continuous_scale='Viridis',
                title=f'Relationship between {x_metric.replace("_", " ").title()} and {y_metric.replace("_", " ").title()}',
                labels={
                    x_metric: x_metric.replace('_', ' ').title(),
                    y_metric: y_metric.replace('_', ' ').title(),
                    'engine_load_percent': 'Engine Load (%)'
                }
            )
            
            # Add trend line
            fig_scatter.add_trace(
                px.scatter(df, x=x_metric, y=y_metric, trendline="ols").data[1]
            )
            
            # Update layout
            fig_scatter.update_layout(
                height=500,
                showlegend=True,
                hovermode='closest'
            )
            
            # Update traces for better visibility
            fig_scatter.update_traces(
                marker=dict(
                    line=dict(width=0.5, color='DarkSlateGrey'),
                    opacity=0.7
                ),
                selector=dict(mode='markers')
            )
            
            st.plotly_chart(fig_scatter, use_container_width=True)
            
            # Show correlation coefficient
            correlation = np.corrcoef(df[x_metric], df[y_metric])[0, 1]
            
            # Interpretation of correlation
            if abs(correlation) > 0.7:
                strength = "Strong"
                color = "🔴" if correlation > 0 else "🔵"
            elif abs(correlation) > 0.3:
                strength = "Moderate"
                color = "🟠" if correlation > 0 else "🟡"
            else:
                strength = "Weak"
                color = "⚪"
            
            direction = "Positive" if correlation > 0 else "Negative"
            
            st.info(
                f"{color} **Correlation Analysis**: {strength} {direction.lower()} correlation "
                f"({correlation:.3f}) between {x_metric.replace('_', ' ')} and {y_metric.replace('_', ' ')}"
            )
            
            # Statistical insights
            with st.expander("📊 Statistical Insights"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        f"Mean {x_metric.replace('_', ' ').title()}", 
                        f"{df[x_metric].mean():.2f}"
                    )
                    st.metric(
                        f"Std {x_metric.replace('_', ' ').title()}", 
                        f"{df[x_metric].std():.2f}"
                    )
                
                with col2:
                    st.metric(
                        f"Mean {y_metric.replace('_', ' ').title()}", 
                        f"{df[y_metric].mean():.2f}"
                    )
                    st.metric(
                        f"Std {y_metric.replace('_', ' ').title()}", 
                        f"{df[y_metric].std():.2f}"
                    )
                
                with col3:
                    st.metric("Correlation Coefficient", f"{correlation:.3f}")
                    st.metric("Data Points", len(df))
            
            # Data table (expandable)
            with st.expander("📋 Raw Data Table"):
                st.dataframe(df, use_container_width=True)
        
    else:
        # Welcome message
        st.info("👈 Use the sidebar to select an asset and time range, then click 'Fetch Data' to begin.")
        
        # Show sample data structure
        st.markdown("### 📊 Available Metrics")
        metrics_info = {
            "Power Generation": ["power_gen_MW", "Power output in megawatts"],
            "Engine Metrics": ["engine_load_percent", "engine_rpm", "engine_temp_C"],
            "Fuel & Emissions": ["fuel_flow_kg_h", "co2_emissions_kg_min"],
            "Electrical": ["voltage_V", "current_A", "frequency_Hz"],
            "Battery": ["battery_soc_percent", "battery_power_MW"],
            "Environment": ["ambient_temp_C"],
            "Performance": ["efficiency_percent"]
        }
        
        for category, metrics in metrics_info.items():
            with st.expander(f"📈 {category}"):
                for metric in metrics:
                    st.write(f"• `{metric}`")

if __name__ == "__main__":
    main()