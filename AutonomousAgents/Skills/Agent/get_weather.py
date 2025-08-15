
import json
import requests

from HoloAI import HoloLink

holoLink = HoloLink()


def get_weather(latitude: float, longitude: float) -> str:
    """
    Description: "Get current temperature for provided coordinates in celsius."
    Additional Information: "Provide the temperature in both Celsius and Fahrenheit."
    """
    holoLink.calledActions(__name__, locals())
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    )
    data = response.json()
    if "current_weather" in data and "temperature" in data["current_weather"]:
        c = data["current_weather"]["temperature"]
        f = c * 9/5 + 32
        return f"Current temperature: {c:.1f} C / {f:.1f} F"
    else:
        return f"Could not fetch current weather. Response: {json.dumps(data)}"



def get_humidity(latitude: float, longitude: float) -> str:
    """
    Description: "Get current relative humidity for provided coordinates."
    Additional Information: "Returns humidity as a percentage."
    """
    holoLink.calledActions(__name__, locals())
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true&hourly=relative_humidity_2m"
    )
    data = response.json()
    try:
        # Returns current hour's humidity
        humidity = data['hourly']['relative_humidity_2m'][0]
        return f"Current humidity: {humidity}%"
    except Exception:
        return f"Could not fetch humidity. Response: {data}"


def get_wind_speed(latitude: float, longitude: float) -> str:
    """
    Description: "Get current wind speed for provided coordinates."
    Additional Information: "Returns wind speed in meters per second (m/s)."
    """
    holoLink.calledActions(__name__, locals())
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    )
    data = response.json()
    try:
        wind_speed = data['current_weather']['windspeed']
        return f"Current wind speed: {wind_speed} m/s"
    except Exception:
        return f"Could not fetch wind speed. Response: {data}"



