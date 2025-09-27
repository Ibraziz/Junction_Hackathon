import requests

def test_api_connection():
    """Test the telemetry API and print sample data."""
    base_url = "http://localhost:8002"
    
    # Test health endpoint
    try:
        health_response = requests.get(f"{base_url}/health")
        print("Health check:", health_response.json())
        print("✅ API server is running!")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Make sure it's running on port 8002")
        return False
    
    # Test telemetry endpoint
    asset_id = "power-plant-001"
    start_time = "2024-01-01T10:00:00Z"
    end_time = "2024-01-01T10:05:00Z"  # 5 minutes of data
    
    try:
        telemetry_url = f"{base_url}/telemetry/{asset_id}"
        params = {
            "start_time": start_time,
            "end_time": end_time
        }
        
        response = requests.get(telemetry_url, params=params)
        data = response.json()
        
        print(f"\n📊 Sample telemetry data for {asset_id}:")
        print(f"Data points received: {len(data)}")
        
        if data:
            # Show first data point structure
            print("\n🔍 First data point structure:")
            sample_point = data[0]
            for key, value in sample_point.items():
                print(f"  {key}: {value}")
            
            # Show available metrics
            print(f"\n📈 Available metrics ({len(sample_point)} total):")
            metrics = [k for k in sample_point.keys() if k not in ['timestamp', 'asset_id']]
            for i, metric in enumerate(metrics, 1):
                print(f"  {i:2d}. {metric}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error testing telemetry endpoint: {e}")
        return False

if __name__ == "__main__":
    test_api_connection()