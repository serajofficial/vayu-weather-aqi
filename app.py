import os
from flask import Flask, request, render_template
import requests

app = Flask(__name__)

WAQI_TOKEN = os.environ.get("WAQI_TOKEN", "")


def weather_code_to_text(code):
    mapping = {
        0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy",
        3: "Overcast", 45: "Fog", 48: "Icy Fog",
        51: "Light Drizzle", 61: "Rain", 71: "Snow",
        80: "Rain Showers", 95: "Thunderstorm"
    }
    return mapping.get(code, f"Code {code}")


def weather_code_to_icon(code):
    mapping = {
        0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
        45: "🌫️", 48: "🌫️", 51: "🌦️", 61: "🌧️",
        71: "❄️", 80: "🌧️", 95: "⛈️"
    }
    return mapping.get(code, "🌡️")


def aqi_label(aqi):
    if not isinstance(aqi, int):
        return "Unknown", ""
    if aqi <= 50:
        return "Good", "good"
    elif aqi <= 100:
        return "Moderate", "moderate"
    elif aqi <= 150:
        return "Unhealthy for Sensitive", "sensitive"
    elif aqi <= 200:
        return "Unhealthy", "unhealthy"
    return "Hazardous", "hazardous"


@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    error = None

    if request.method == 'POST':
        try:
            pincode = request.form['pincode'].strip()

            # ✅ FIX: specific User-Agent required by Nominatim
            response = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={
                    'postalcode': pincode,
                    'country': 'India',
                    'format': 'json',
                    'limit': 1
                },
                headers={
                    'User-Agent': 'VayuWeatherApp/1.0 (vayu-weather-aqi.onrender.com)'
                },
                timeout=10
            )

            if response.status_code != 200:
                raise Exception("Location service unavailable. Please try again.")

            geo_resp = response.json()

            if not geo_resp:
                raise Exception(f"PIN code '{pincode}' not found. Please check and try again.")

            result = geo_resp[0]
            lat = float(result['lat'])
            lon = float(result['lon'])

            display_parts = result.get('display_name', '').split(',')
            city = display_parts[0].strip() if display_parts else "Unknown"
            state = display_parts[-3].strip() if len(display_parts) >= 3 else ""

            # Fetch weather from Open-Meteo
            weather_resp = requests.get(
                'https://api.open-meteo.com/v1/forecast',
                params={
                    'latitude': lat,
                    'longitude': lon,
                    'current': 'temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m'
                },
                timeout=10
            )

            if weather_resp.status_code != 200:
                raise Exception("Weather service unavailable. Please try again.")

            current = weather_resp.json()['current']
            temp = current['temperature_2m']
            weather_code = current['weather_code']
            humidity = current.get('relative_humidity_2m', '--')
            wind = current.get('wind_speed_10m', '--')

            # Fetch AQI from WAQI
            try:
                aqi_resp = requests.get(
                    f'https://api.waqi.info/feed/geo:{lat};{lon}/?token={WAQI_TOKEN}',
                    timeout=10
                ).json()
                aqi_value = aqi_resp['data']['aqi'] if aqi_resp.get("status") == "ok" else None
            except Exception:
                aqi_value = None

            aqi_text, aqi_cls = aqi_label(aqi_value)

            data = {
                'city': city,
                'state': state,
                'pincode': pincode,
                'lat': lat,
                'lon': lon,
                'temp': temp,
                'weather': weather_code_to_text(weather_code),
                'icon': weather_code_to_icon(weather_code),
                'humidity': humidity,
                'wind': wind,
                'aqi': aqi_value if aqi_value is not None else "N/A",
                'aqi_text': aqi_text,
                'aqi_cls': aqi_cls,
            }

        except Exception as e:
            error = str(e)

    return render_template('index.html', data=data, error=error)


if __name__ == '__main__':
    app.run(debug=True)
