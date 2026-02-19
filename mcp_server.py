# server.py
from datetime import datetime
from typing import Literal, Dict
import random
import httpx
from fastmcp import FastMCP


mcp = FastMCP("Demo 🚀")


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"


# # --- Internal Weather Logic ---
# SEASON_TEMP_BASE = {
#     "winter": 5,
#     "spring": 18,
#     "summer": 32,
#     "autumn": 20,
# }


# def get_season(month: int) -> str:
#     if month in [12, 1, 2]:
#         return "winter"
#     elif month in [3, 4, 5]:
#         return "spring"
#     elif month in [6, 7, 8]:
#         return "summer"
#     return "autumn"


# CITY_TEMP_OFFSET = {
#     "seoul": -3,
#     "london": -2,
#     "dubai": 8,
#     "new york": 0,
#     "bangalore": 4,
# }


# @mcp.tool
# def predict_weather(
#     city: str, forecast_days: int = 1, unit: Literal["C", "F"] = "C"
# ) -> Dict:
#     """
#     Predict weather for a given city.

#     Args:
#         city: City name
#         forecast_days: Days ahead (1-7)
#         unit: Temperature unit (C or F)

#     Returns:
#         Structured weather prediction
#     """

#     if forecast_days < 1 or forecast_days > 7:
#         return {"error": "forecast_days must be between 1 and 7"}

#     city_key = city.lower()
#     city_offset = CITY_TEMP_OFFSET.get(city_key, 0)

#     month = datetime.utcnow().month
#     season = get_season(month)
#     base_temp = SEASON_TEMP_BASE[season]

#     predictions = []

#     for day in range(forecast_days):
#         variation = random.randint(-3, 3)
#         temp_c = base_temp + city_offset + variation

#         if unit == "F":
#             temp = round((temp_c * 9 / 5) + 32, 1)
#         else:
#             temp = round(temp_c, 1)

#         predictions.append(
#             {
#                 "day": day + 1,
#                 "temperature": temp,
#                 "unit": unit,
#                 "condition": random.choice(
#                     ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Windy"]
#                 ),
#             }
#         )

#     return {
#         "city": city.title(),
#         "season": season,
#         "forecast": predictions,
#         "model": "heuristic-seasonal-v1",
#     }


# ------------------------------------------------------------
# Utility: Convert city → lat/lon using Open-Meteo geocoding
# ------------------------------------------------------------
async def geocode_city(city: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city, "count": 1}

    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        data = r.json()

    if not data.get("results"):
        return None

    result = data["results"][0]
    return result["latitude"], result["longitude"], result.get("country")


# ------------------------------------------------------------
# MCP Tool
# ------------------------------------------------------------
@mcp.tool
async def get_weather(city: str, forecast_days: int = 7) -> Dict:
    """
    Get real weather forecast for a city (up to 16 days).
    """

    if forecast_days < 1 or forecast_days > 16:
        return {"error": "forecast_days must be between 1 and 16 (API limit)."}

    geo = await geocode_city(city)
    if not geo:
        return {"error": f"Could not find city '{city}'"}

    lat, lon, country = geo

    weather_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "auto",
        "forecast_days": forecast_days,
    }

    async with httpx.AsyncClient() as client:
        r = await client.get(weather_url, params=params)
        weather_data = r.json()

    daily = weather_data.get("daily", {})

    forecast = []
    for i in range(len(daily.get("time", []))):
        forecast.append(
            {
                "date": daily["time"][i],
                "temp_max_C": daily["temperature_2m_max"][i],
                "temp_min_C": daily["temperature_2m_min"][i],
            }
        )

    return {
        "city": city,
        "country": country,
        "forecast_days": forecast_days,
        "source": "Open-Meteo (free)",
        "forecast": forecast,
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
    #mcp.serve_http(host="127.0.0.1", port=8080)
