import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import json
from llm_pipeline import run_analysis_pipeline, run_analysis_pipeline_with_tools, run_query_pipeline

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

def fetch_external_data_endpoint(endpoint: str, start_time: str = None, end_time: str = None):
    """Fetch data from a specific external service endpoint with optional date range."""
    try:
        url = f"{EXTERNAL_API_URL}/{endpoint}"
        params = {}
        if start_time:
            params['start_time'] = start_time
        if end_time:
            params['end_time'] = end_time
            
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', []) if 'data' in data else []
        return []
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not fetch {endpoint}: {e}")
        return []

def get_external_data_date_range(external_data):
    """Determine the actual date range of received external data."""
    all_times = []
    for source_data in external_data.values():
        if source_data:
            for item in source_data:
                if 'startTime' in item:
                    all_times.append(pd.to_datetime(item['startTime']))
                elif 'endTime' in item:
                    all_times.append(pd.to_datetime(item['endTime']))
    
    if all_times:
        return min(all_times), max(all_times)
    return None, None

def render_chart(chart_config: dict, chart_id: str):
    """Renders a Chart.js chart using Streamlit's HTML component."""
    chart_options = chart_config.get('options', {})
    if 'plugins' not in chart_options:
        chart_options['plugins'] = {}
    chart_options['plugins']['title'] = {
        'display': True,
        'text': chart_config.get('title', 'Chart'),
        'font': {'size': 16},
        'color': '#FFFFFF' # White title for dark mode
    }
    # Ensure legend labels are visible in dark mode
    chart_options['plugins']['legend'] = {
        'labels': {'color': '#FFFFFF'}
    }

    config = {
        'type': chart_config.get('type'),
        'data': chart_config.get('data'),
        'options': chart_options,
    }
    config_json = json.dumps(config)

    chart_html = f"""
    <div style="width: 100%; height: 400px;">
        <canvas id="{chart_id}"></canvas>
    </div>
    <script>
    const ctx_{chart_id} = document.getElementById('{chart_id}');
    if (ctx_{chart_id}) {{
        new Chart(ctx_{chart_id}, {config_json});
    }}
    </script>
    """
    # Use st.components.v1.html to render the component, including the Chart.js library
    st.components.v1.html(f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    {chart_html}
    """, height=400)

def render_html_component(html_content: str, component_id: str = None):
    """Renders an HTML component using Streamlit's HTML component."""
    if not html_content:
        return

    # Estimate height based on content length and structure
    # Count line breaks and estimate height
    line_count = html_content.count('\n') + html_content.count('<br>') + html_content.count('<p>')
    table_count = html_content.count('<table>')
    list_count = html_content.count('<ul>') + html_content.count('<ol>')
    
    # Base height calculation
    estimated_height = max(200, min(800, 50 + line_count * 25 + table_count * 100 + list_count * 50))

    # Create a container with proper styling
    container_style = """
    <style>
    .html-component-container {
        border: 1px solid #4e8b8e;
        border-radius: 8px;
        padding: 16px;
        margin: 16px 0;
        background-color: #0e1117;
        overflow-y: auto;
        max-height: 100vh;
    }
    .html-component-container h3 {
        color: #fafafa;
        margin-top: 0;
        margin-bottom: 16px;
    }
    .html-component-container p {
        color: #fafafa;
        margin-bottom: 8px;
    }
    .html-component-container ul, .html-component-container ol {
        color: #fafafa;
    }
    .html-component-container table {
        color: #fafafa;
        border-collapse: collapse;
        width: 100%;
    }
    .html-component-container th, .html-component-container td {
        border: 1px solid #4e8b8e;
        padding: 8px;
        text-align: left;
    }
    </style>
    """

    html_with_container = f"""
    {container_style}
    <div class="html-component-container" id="{'html_component_' + component_id if component_id else 'html_component'}">
        {html_content}
    </div>
    """

    st.components.v1.html(html_with_container, height=estimated_height, scrolling=True)

def main():
    # Header
    st.title("⚡ Power Plant Monitoring Dashboard")
    st.markdown("**Real-time power plant telemetry and Finnish national energy grid data**")
    st.markdown("---")
    
    # Check service health
    telemetry_healthy = check_telemetry_health()
    external_healthy = check_external_health()
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["📊 Dashboard", "💬 AI Chat"])
    
    with tab1:
        render_dashboard_tab(telemetry_healthy, external_healthy)
    
    with tab2:
        render_chat_tab()

def render_dashboard_tab(telemetry_healthy, external_healthy):
    """Render the main dashboard content."""
    if not telemetry_healthy:
        st.error("🚫 Cannot connect to the telemetry API server. Please ensure it's running on port 8002.")
        return
    
    # Fixed parameters
    asset_id = "GEN-001"
    now = datetime.now()
    
    # Telemetry data - 24 hours
    telemetry_end_datetime = now - timedelta(hours=1)  # 1 hour ago
    telemetry_start_datetime = telemetry_end_datetime - timedelta(hours=24)  # 24 hours of data
    telemetry_start_time_str = telemetry_start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    telemetry_end_time_str = telemetry_end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # External data - last 24 hours (more realistic for real-time data)
    external_end_datetime = now
    external_start_datetime = external_end_datetime - timedelta(hours=24)  # 24 hours of data
    external_start_time_str = external_start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    external_end_time_str = external_end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Fetch telemetry data
    with st.spinner("🔄 Fetching power plant telemetry data..."):
        telemetry_data = fetch_telemetry_data(asset_id, telemetry_start_time_str, telemetry_end_time_str)
    
    if not telemetry_data:
        st.error("❌ Failed to fetch telemetry data. Please check the telemetry service.")
        return
    
    # Convert telemetry data to DataFrame
    df = pd.DataFrame(telemetry_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Key Performance Metrics - Telemetry Only
    st.subheader("🏭 Power Plant Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_power = df.get('power_gen_MW', pd.Series(dtype=float)).mean()
        max_power = df.get('power_gen_MW', pd.Series(dtype=float)).max()
        st.metric(
            "Average Power Output",
            f"{avg_power:.1f} MW",
            delta=f"Peak: {max_power:.1f} MW"
        )

    with col2:
        avg_efficiency = df.get('efficiency_percent', pd.Series(dtype=float)).mean()
        st.metric(
            "Average Efficiency",
            f"{avg_efficiency:.1f}%"
        )

    with col3:
        avg_fuel_flow = df.get('fuel_flow_kg_h', pd.Series(dtype=float)).mean()
        st.metric(
            "Avg Fuel Consumption",
            f"{avg_fuel_flow:.0f} kg/h"
        )

    with col4:
        avg_engine_load = df.get('engine_load_percent', pd.Series(dtype=float)).mean()
        st.metric(
            "Average Engine Load", 
            f"{avg_engine_load:.1f}%"
        )
    
    st.markdown("---")
    
    # Chart 1: Power Plant Generation Over Time
    st.subheader("📈 Power Plant Generation Over Time")
    st.caption(f"Data from: {telemetry_start_datetime.strftime('%B %d, %Y %H:%M')} to {telemetry_end_datetime.strftime('%B %d, %Y %H:%M')}")
    
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
    
    # Fetch external data if available (get recent data without strict date constraints)
    external_data = {}
    if external_healthy:
        with st.spinner("🔄 Fetching national energy data (most recent available)..."):
            external_data['nuclear'] = fetch_external_data_endpoint('api/production/nuclear-power')
            external_data['wind'] = fetch_external_data_endpoint('api/production/wind-power')
            external_data['hydro'] = fetch_external_data_endpoint('api/production/hydro-power')
            external_data['consumption'] = fetch_external_data_endpoint('api/consumption/electricity')
            external_data['emission'] = fetch_external_data_endpoint('api/market/emission-factor')
    
    # Display charts if data is available
    if external_healthy and any(external_data.values()):
        # Get actual date range of external data
        ext_start_time, ext_end_time = get_external_data_date_range(external_data)
        
        # Chart 2: Power Generation Mix Pie Chart
        st.subheader("🥧 Finnish Energy Production Mix")
        if ext_start_time and ext_end_time:
            st.caption(f"Data from: {ext_start_time.strftime('%B %d, %Y %H:%M')} to {ext_end_time.strftime('%B %d, %Y %H:%M')}")
        else:
            st.caption("Recent data from Fingrid API")
        
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
            if ext_start_time and ext_end_time:
                st.caption(f"Data from: {ext_start_time.strftime('%B %d, %Y %H:%M')} to {ext_end_time.strftime('%B %d, %Y %H:%M')}")
            else:
                st.caption("Recent data from Fingrid API")
            
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

        # --- AI-Powered Analysis Section ---
        st.markdown("---")
        st.subheader("🤖 Operational Analysis")
        st.markdown("Click the button below to get an AI-driven summary, suggested action, and insightful charts based on the latest data from all sources.")

        if st.button("Run Analysis", type="primary"):
            with st.spinner("🧠 Analyzing data with Gemini... This may take a moment."):
                analysis_result = run_analysis_pipeline_with_tools()

            if "error" in analysis_result:
                st.error(f"**Analysis Failed:** {analysis_result['error']}")
            else:
                col1, col2 = st.columns([2, 2])
                with col1:
                    st.metric(
                        label="Suggested Action",
                        value=analysis_result.get("suggested_action", "N/A").replace("_", " ").title()
                    )
                    st.info(f"**Reasoning:** {analysis_result.get('action_reasoning', 'N/A')}")

                with col2:
                    st.markdown(f"**Summary:** {analysis_result.get('summary', 'N/A')}")
                    keywords = analysis_result.get("keywords", [])
                    st.markdown(f"**Keywords:** `{'`, `'.join(keywords)}`")

                # Display HTML component if provided
                html_component = analysis_result.get("html_component")
                if html_component:
                    st.markdown("---")
                    render_html_component(html_component, "ai_analysis")

                st.markdown("---")

                charts = analysis_result.get("charts", [])
                if not charts:
                    st.warning("The AI analysis did not generate any charts.")
                else:
                    for i, chart_conf in enumerate(charts):
                        render_chart(chart_conf, f"ai_chart_{i}")

    else:
        st.error("❌ Failed to fetch telemetry data. Please check the telemetry service.")

def render_chat_tab():
    """Render the AI chat interface."""
    st.markdown("### 🤖 AI Energy Assistant")
    st.markdown("Ask questions about energy data, power plant operations, or request charts and analysis.")
    
    # Check if API is configured
    try:
        from llm_pipeline import client
        if not client:
            st.info("💡 **Demo Mode**: GEMINI_API_KEY not configured. The chat will return sample responses to demonstrate functionality.")
    except:
        st.info("💡 **Demo Mode**: AI service not fully configured. Showing sample responses.")
    
    # Initialize session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("#### Chat History")
        for i, (question, response_data) in enumerate(st.session_state.chat_history):
            with st.expander(f"💬 Q{i+1}: {question[:60]}{'...' if len(question) > 60 else ''}", expanded=(i == len(st.session_state.chat_history) - 1)):
                st.markdown(f"**Question:** {question}")
                
                if "error" in response_data:
                    st.error(f"**Error:** {response_data['error']}")
                else:
                    st.markdown(f"**Response:** {response_data.get('response', 'No response available.')}")
                    
                    # Display charts if available
                    charts = response_data.get('charts')
                    if charts:
                        for j, chart_conf in enumerate(charts):
                            render_chart(chart_conf, f"chat_chart_{i}_{j}")
                    
                    # Display HTML component if available
                    html_component = response_data.get('html_component')
                    if html_component:
                        st.markdown("**Additional Information:**")
                        render_html_component(html_component, f"chat_html_{i}")
        
        # Clear chat history button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Chat input
    st.markdown("---")
    st.markdown("#### Ask a Question")
    
    # Example questions
    with st.expander("💡 Example Questions"):
        example_questions = [
            "What were the peak electricity consumption hours in Finland during 2019?",
            "How does wind generation correlate with electricity consumption?",
            "Show me a chart comparing summer and winter electricity consumption patterns",
            "What is the current status of the power plant?",
            "Analyze the efficiency trends over the past month",
            "What were the typical load patterns during weekdays vs weekends in 2020?"
        ]
        for question in example_questions:
            if st.button(f"📋 {question}", key=f"example_{hash(question)}", help="Click to use this question"):
                # Directly process the example question
                with st.spinner("🧠 Processing your query..."):
                    try:
                        response_data = run_query_pipeline(question, include_context=True)
                        st.session_state.chat_history.append((question, response_data))
                        st.rerun()
                    except Exception as e:
                        error_response = {"error": f"Failed to process query: {str(e)}"}
                        st.session_state.chat_history.append((question, error_response))
                        st.error(f"Error processing query: {str(e)}")
                        st.rerun()
    
    # Query input
    user_query = st.text_area(
        "Enter your question:",
        height=100,
        placeholder="Ask about energy data, power plant operations, request charts, or general energy questions...",
        key="user_query_input"
    )
    
    # Send button
    if st.button("🚀 Send Query", type="primary", disabled=not user_query.strip()):
        if user_query.strip():
            with st.spinner("🧠 Processing your query..."):
                try:
                    # Run the query pipeline
                    response_data = run_query_pipeline(user_query.strip(), include_context=True)
                    
                    # Add to chat history
                    st.session_state.chat_history.append((user_query.strip(), response_data))
                    
                    # Clear the input and rerun
                    st.session_state.user_query_input = ""
                    st.rerun()
                    
                except Exception as e:
                    error_response = {"error": f"Failed to process query: {str(e)}"}
                    st.session_state.chat_history.append((user_query.strip(), error_response))
                    st.error(f"Error processing query: {str(e)}")
                    st.rerun()

if __name__ == "__main__":
    main()