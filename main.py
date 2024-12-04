import requests
import os
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from typing import Optional, List
from pydantic import BaseModel, Field

# загружаем значение API KEY из файла .env
load_dotenv()
api_key = os.getenv("WEATHER_API_KEY")

app = FastAPI(title="Weather")


class WeatherRequest(BaseModel):
    city_name: str = ""
    lon: Optional[float] = Field(ge=-180, le=180, default=0)
    lat: Optional[float] = Field(ge=-90, le=90, default=0)
    lang: str = "eng"


class WeatherInfo(BaseModel):
    weather_main: str = "Unknown"
    weather_description: str = "Unknown"


class CityInfo(BaseModel):
    city_name: str = "Unknown"
    city_country: str = "Unknown"


class WeatherResponse(BaseModel):
    city_info: List[CityInfo]
    lon: float
    lat: float
    weather_info: List[WeatherInfo]
    temperature: float
    feels_like_temperature: float
    wind_speed: float


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def perform_request(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def save_request_in_txt_file(result_dict: dict, file_name: str = "request_results",
                             access_mode: str = "a"):
    with open(file_name, access_mode) as convert_file:
        if access_mode == "a" and convert_file.tell() != 0:  # Проверяем, не является ли файл пустым
            convert_file.write('\n')  # Добавляем новую строку перед записью новых данных
        result_string = f"{str(result_dict)}\n{datetime.now()}"
        convert_file.write(result_string)


@app.post("/get_weather", response_model=WeatherResponse)
def get_weather_from_api(request: WeatherRequest) -> dict:
    try:
        # если название города неизвестно, осуществляется поиск по координатам
        if request.city_name == "":
            url = f"https://api.openweathermap.org/data/2.5/weather?units=metric&lat={request.lat}&lon={request.lon}&appid={api_key}"
        else:
            url = f"https://api.openweathermap.org/data/2.5/weather?units=metric&q={request.city_name}&appid={api_key}"

        if request.lang != "eng":
            url += f"&lang={request.lang}"
            print(url)
        data = perform_request(url)

    except RetryError:
        # обработка ошибки повторных попыток
        raise HTTPException(status_code=404, detail="Ошибка при повторных попытках запроса")

    city_name = data["name"] if "name" in data else "Unknown"
    city_country = data["sys"]["country"] if "sys" in data and "country" in data["sys"] else "Unknown"
    city_info = dict(CityInfo(city_name=city_name, city_country=city_country))

    weather_main = data["weather"][0]["main"] if "weather" in data else ""
    weather_description = data["weather"][0]["description"] if "weather" in data else ""
    weather_info = dict(WeatherInfo(weather_main=weather_main, weather_description=weather_description))
    # получение конкретных данных
    lat = data["coord"]["lat"]
    lon = data["coord"]["lon"]
    temperature = data["main"]["temp"]
    feels_like_temperature = data["main"]["feels_like"]
    wind_speed = data["wind"]["speed"]

    result_response = WeatherResponse(city_info=[city_info], lat=lat, lon=lon, weather_info=[weather_info],
                                      temperature=temperature,
                                      feels_like_temperature=feels_like_temperature, wind_speed=wind_speed)
    result_dict = dict(result_response)
    save_request_in_txt_file(result_dict=result_dict)
    return result_dict
