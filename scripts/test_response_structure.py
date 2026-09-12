
import os
import requests
import json

def test_api():
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("Error: GOOGLE_MAPS_API_KEY not set")
        return

    url = "https://areainsights.googleapis.com/v1:computeInsights"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
    }
    
    # Request body with INSIGHT_PLACES
    body = {
        "insights": ["INSIGHT_COUNT", "INSIGHT_PLACES"],
        "filter": {
            "locationFilter": {
                "circle": {
                    "latLng": {
                        "latitude": 37.7749, # San Francisco
                        "longitude": -122.4194,
                    },
                    "radius": 500,
                }
            },
            "typeFilter": {
                "includedTypes": ["restaurant"]
            }
        }
    }
    
    print("Sending request...")
    try:
        response = requests.post(url, headers=headers, json=body)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
