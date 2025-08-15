
##-------------- Both the original and updated versions are valid, but the updated version is more flexible and easier to maintain. --------------##

## The new version for Weather class is based on: 
##  The updates to the skills manager and the use of lists and dictionaries for signatures options.
##  See below in the commented out section for the original code.


import json
import requests
import logging
import threading
import inspect
from datetime import datetime

from HoloLink import HoloLink

logger = logging.getLogger(__name__)

class Weather:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(Weather, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        self._initComponents()
        self.initialized = True

    def _initComponents(self):
        self.holoLink = HoloLink()
        ##------------- When defining signatures, you can choose between dictSig or listSig -------------##
        # dictSig is more descriptive and allows you to specify types for function arguments
        # listSig is simpler and just specifies argument names without types
        # This is useful for the model to understand what arguments are expected
        # You can use dicts and lists together, but it's generally better to choose one style for consistency per skill class so not to confuse the model.
        self.dictSig = {
            "_getWeather":     {"latitude": "float", "longitude": "float"},
            "_getTemperature": {"latitude": "float", "longitude": "float"},
            "_getHumidity":    {"latitude": "float", "longitude": "float"},
            "_getWindSpeed":   {"latitude": "float", "longitude": "float"},
        }
        # self.listSig = {
        #     "_getWeather":     ["latitude", "longitude"],
        #     "_getTemperature": ["latitude", "longitude"],
        #     "_getHumidity":    ["latitude", "longitude"],
        #     "_getWindSpeed":   ["latitude", "longitude"]
        ##--------- You can specify the arguments in a list format as well to help the model, but it's not 100% reliable ---------##
        ##     "_getWeather":     ["latitude(float)", "longitude(float)"],
        # }
        self.actionMap = {
            "get-weather":     self._getWeather,
            "get-temperature": self._getTemperature,
            "get-humidity":    self._getHumidity,
            "get-wind-speed":  self._getWindSpeed
        }

    def _metaData(self):
        return {
            "className": f"{self.__class__.__name__}", 
            "description": "Get current weather information such as temperature, humidity, and wind speed for a given location.",
        }

    def weatherSkill(self, action: str, *args):
        self.holoLink.calledActions(self, locals())
        name = inspect.currentframe().f_code.co_name
        return self.holoLink.executeSkill('system', name, self.actionMap, action, *args)

    def _getWeather(self, infoDict: dict) -> str:
        latitude = infoDict.get("latitude")
        longitude = infoDict.get("longitude")
        temperature_info = self._getTemperature([latitude, longitude])
        humidity_info = self._getHumidity([latitude, longitude])
        wind_speed_info = self._getWindSpeed([latitude, longitude])
        return f"{temperature_info}\n{humidity_info}\n{wind_speed_info}"


    def _getTemperature(self, infoDict: dict) -> str:
        latitude = infoDict.get("latitude")
        longitude = infoDict.get("longitude")
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

    def _getHumidity(self, infoDict: dict) -> str:
        latitude = infoDict.get("latitude")
        longitude = infoDict.get("longitude")
        response = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true&hourly=relative_humidity_2m"
        )
        data = response.json()
        try:
            now = datetime.utcnow().replace(minute=0, second=0, microsecond=0).isoformat()
            times = data['hourly']['time']
            humidities = data['hourly']['relative_humidity_2m']
            idx = times.index(now)
            humidity = humidities[idx]
            return f"Current humidity: {humidity}%"
        except Exception:
            return f"Could not fetch humidity. Response: {data}"

    def _getWindSpeed(self, infoDict: dict) -> str:
        latitude = infoDict.get("latitude")
        longitude = infoDict.get("longitude")
        response = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
        )
        data = response.json()
        try:
            wind_speed = data['current_weather']['windspeed']
            return f"Current wind speed: {wind_speed} m/s"
        except Exception:
            return f"Could not fetch wind speed. Response: {data}"

    # def _getWeather(self, infoList: list) -> str:
    #     latitude, longitude = infoList
    #     temperature_info = self._getTemperature([latitude, longitude])
    #     humidity_info = self._getHumidity([latitude, longitude])
    #     wind_speed_info = self._getWindSpeed([latitude, longitude])
    #     return f"{temperature_info}\n{humidity_info}\n{wind_speed_info}"

    # def _getTemperature(self, infoList: list) -> str:
    #     latitude, longitude = infoList
    #     response = requests.get(
    #         f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    #     )
    #     data = response.json()
    #     if "current_weather" in data and "temperature" in data["current_weather"]:
    #         c = data["current_weather"]["temperature"]
    #         f = c * 9/5 + 32
    #         return f"Current temperature: {c:.1f} C / {f:.1f} F"
    #     else:
    #         return f"Could not fetch current weather. Response: {json.dumps(data)}"

    # def _getHumidity(self, infoList: list) -> str:
    #     latitude, longitude = infoList
    #     response = requests.get(
    #         f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true&hourly=relative_humidity_2m"
    #     )
    #     data = response.json()
    #     try:
    #         now = datetime.utcnow().replace(minute=0, second=0, microsecond=0).isoformat()
    #         times = data['hourly']['time']
    #         humidities = data['hourly']['relative_humidity_2m']
    #         idx = times.index(now)
    #         humidity = humidities[idx]
    #         return f"Current humidity: {humidity}%"
    #     except Exception:
    #         return f"Could not fetch humidity. Response: {data}"

    # def _getWindSpeed(self, infoList: list) -> str:
    #     latitude, longitude = infoList
    #     response = requests.get(
    #         f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    #     )
    #     data = response.json()
    #     try:
    #         wind_speed = data['current_weather']['windspeed']
    #         return f"Current wind speed: {wind_speed} m/s"
    #     except Exception:
    #         return f"Could not fetch wind speed. Response: {data}"



## Original code for Weather class

# import json
# import requests

# import logging
# import subprocess
# import os
# import threading
# import inspect

# from HoloLink import HoloLink

# logger = logging.getLogger(__name__)


# class Weather:
#     _instance = None
#     _lock = threading.Lock()

#     def __new__(cls, *args, **kwargs):
#         if not cls._instance:
#             with cls._lock:
#                 if not cls._instance:
#                     cls._instance = super(Weather, cls).__new__(cls, *args, **kwargs)
#         return cls._instance

#     def __init__(self):
#         if hasattr(self, 'initialized'):
#             return
#         self._initComponents()
#         self.initialized = True

#     def _initComponents(self):
#         self.holoLink = HoloLink()
#         self.actionMap = {
#             "get-weather":     self._getWeather,
#             "get-temperature": self._getTemperature,
#             "get-humidity":    self._getHumidity,
#             "get-wind-speed":  self._getWindSpeed
#         }

#     def _metaData(self):
#         return {
#             "className": f"{self.__class__.__name__}", 
#             "description": "Get current weather information such as temperature, humidity, and wind speed for a given location.",
#         }

#     def weatherSkill(self, action: str, *args):
#         self.holoLink.calledActions(self, locals())
#         name = inspect.currentframe().f_code.co_name
#         return self.holoLink.executeSkill('system', name, self.actionMap, action, *args)

#     def _getWeather(self, latitude: float, longitude: float) -> str:
#         """
#         Description: "Get current weather summary (temperature, humidity, wind speed) for provided coordinates."
#         Returns: Formatted string with all three values.
#         """
#         temperature_info = self._getTemperature(latitude, longitude)
#         humidity_info = self._getHumidity(latitude, longitude)
#         wind_speed_info = self._getWindSpeed(latitude, longitude)

#         return f"{temperature_info}\n{humidity_info}\n{wind_speed_info}"

#     def _getTemperature(self, latitude: float, longitude: float) -> str:
#         """
#         Description: "Get current temperature for provided coordinates in celsius."
#         Additional Information: "Provide the temperature in both Celsius and Fahrenheit."
#         """
#         response = requests.get(
#             f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
#         )
#         data = response.json()
#         if "current_weather" in data and "temperature" in data["current_weather"]:
#             c = data["current_weather"]["temperature"]
#             f = c * 9/5 + 32
#             return f"Current temperature: {c:.1f} C / {f:.1f} F"
#         else:
#             return f"Could not fetch current weather. Response: {json.dumps(data)}"

#     def _getHumidity(self, latitude: float, longitude: float) -> str:
#         """
#         Description: "Get current relative humidity for provided coordinates."
#         Additional Information: "Returns humidity as a percentage."
#         """
#         response = requests.get(
#             f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true&hourly=relative_humidity_2m"
#         )
#         data = response.json()
#         try:
#             # Returns current hour's humidity
#             humidity = data['hourly']['relative_humidity_2m'][0]
#             return f"Current humidity: {humidity}%"
#         except Exception:
#             return f"Could not fetch humidity. Response: {data}"

#     def _getWindSpeed(self, latitude: float, longitude: float) -> str:
#         """
#         Description: "Get current wind speed for provided coordinates."
#         Additional Information: "Returns wind speed in meters per second (m/s)."
#         """
#         response = requests.get(
#             f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
#         )
#         data = response.json()
#         try:
#             wind_speed = data['current_weather']['windspeed']
#             return f"Current wind speed: {wind_speed} m/s"
#         except Exception:
#             return f"Could not fetch wind speed. Response: {data}"



