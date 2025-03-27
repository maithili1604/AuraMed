import requests

def get_coordinates(address):
    # OpenCage API key
    api_key = 'e9a9d9a03ee24b22819f993dd6077a0c'
    base_url = "https://api.opencagedata.com/geocode/v1/json"
    params = {'q': address, 'key': api_key}  # 'q' is the query parameter for OpenCage
    response = requests.get(base_url, params=params)
    
    print(f"Fetching coordinates for address: {address}")  # Debug statement
    if response.status_code == 200:
        data = response.json()
        # Check for success in the response
        if data['status']['code'] == 200:
            if data['results']:  # Check if results are present
                location = data['results'][0]['geometry']  # Extract geometry (lat, lng)
                print(f"Coordinates found: {location}")  # Debug statement
                return location['lat'], location['lng']
            else:
                print("No results found for the given address.")  # Debug statement
        else:
            print(f"OpenCage API returned error code: {data['status']['code']}")  # Debug statement
    else:
        print(f"OpenCage API HTTP error: {response.status_code}")  # Debug statement
    
    return None

# Example usage
coordinates = get_coordinates("heritage Institute Of tecchnology,Kolkata")
if coordinates:
    print(f"Latitude: {coordinates[0]}, Longitude: {coordinates[1]}")
else:
    print("Failed to fetch coordinates.")
