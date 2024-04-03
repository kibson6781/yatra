import urequests

def fetch_weather_data(api_key, city_name):
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = f"{base_url}q={city_name}&appid={api_key}&units=metric"
    response = urequests.get(complete_url)
    data = response.json()
    return data

def extract_rain_data(weather_data):
    print(weather_data)
    if 'rain' in weather_data:
        rain_info = weather_data['rain']
        return rain_info
    else:
        return None

def get_rain_data():
    api_key = "482f5bea526cb4ff80e0ada18e2252de"
    city_name = "Mumbai, India"  # Replace with your desired city and country
    weather_data = fetch_weather_data(api_key, city_name)
    if weather_data['cod'] == 200:
        rain_info = extract_rain_data(weather_data)
        print(rain_info)
        if rain_info:
            print("Rain information:")
            print(rain_info)
            return rain_info
        else:
            print("No rain information available.")
            return 0
    else:
        print("Error fetching weather data.")