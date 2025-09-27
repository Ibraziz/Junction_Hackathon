"""
Demo script to verify the complete dashboard functionality.
This script tests the API and demonstrates key features.
"""

import requests

def test_complete_setup():
    """Test the complete telemetry dashboard setup."""
    
    print("🧪 Testing Power Plant Telemetry Dashboard Setup")
    print("=" * 55)
    
    # Test 1: API Health Check
    print("\n1️⃣ Testing API Health...")
    try:
        response = requests.get("http://localhost:8002/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ API server is running successfully!")
            print(f"   📊 Response: {response.json()}")
        else:
            print(f"   ❌ API health check failed with status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Cannot connect to API server: {e}")
        return False
    
    # Test 2: API Documentation
    print("\n2️⃣ Checking API Documentation...")
    try:
        response = requests.get("http://localhost:8002/docs", timeout=5)
        if response.status_code == 200:
            print("   ✅ API documentation is accessible at http://localhost:8002/docs")
        else:
            print(f"   ⚠️  API docs returned status: {response.status_code}")
    except requests.exceptions.RequestException:
        print("   ⚠️  Could not access API documentation")
    
    # Test 3: Telemetry Data Retrieval
    print("\n3️⃣ Testing Telemetry Data Retrieval...")
    test_cases = [
        {
            "name": "Quick 5-minute test",
            "asset_id": "power-plant-001",
            "start_time": "2024-01-01T10:00:00Z",
            "end_time": "2024-01-01T10:05:00Z",
            "expected_points": 5
        },
        {
            "name": "1-hour analysis",
            "asset_id": "generator-002", 
            "start_time": "2024-01-01T08:00:00Z",
            "end_time": "2024-01-01T09:00:00Z",
            "expected_points": 60
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n   Test 3.{i}: {test_case['name']}")
        
        try:
            url = f"http://localhost:8002/telemetry/{test_case['asset_id']}"
            params = {
                "start_time": test_case["start_time"],
                "end_time": test_case["end_time"]
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Retrieved {len(data)} data points for {test_case['asset_id']}")
                
                if data:
                    sample_point = data[0]
                    print(f"   📈 Sample metrics: Power={sample_point['power_gen_MW']}MW, "
                          f"Load={sample_point['engine_load_percent']}%, "
                          f"Efficiency={sample_point['efficiency_percent']}%")
            else:
                print(f"   ❌ Failed to retrieve data: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
    
    # Test 4: Dashboard Accessibility
    print("\n4️⃣ Testing Dashboard Accessibility...")
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        if response.status_code == 200:
            print("   ✅ Dashboard is accessible at http://localhost:8501")
        else:
            print(f"   ❌ Dashboard returned status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Cannot connect to dashboard: {e}")
        print("   💡 Make sure Streamlit is running: streamlit run app.py --server.port 8501")
    
    # Summary
    print("\n" + "=" * 55)
    print("🎯 Setup Test Complete!")
    print("\n📋 Next Steps:")
    print("1. Open http://localhost:8501 in your browser")
    print("2. Enter an asset ID (e.g., 'power-plant-001')")
    print("3. Select a time range (start with 'Last 1 Hour' button)")
    print("4. Click 'Fetch Data' to load telemetry")
    print("5. Explore the interactive charts and correlation analysis")
    
    print("\n🎨 Dashboard Features to Test:")
    print("• Time series plots with dual y-axis")
    print("• Temperature and emissions monitoring")
    print("• Interactive correlation scatter plots")
    print("• Performance metrics and statistics")
    print("• Raw data table view")
    
    return True

if __name__ == "__main__":
    test_complete_setup()