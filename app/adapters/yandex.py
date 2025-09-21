import re

import pandas as pd
from bs4 import BeautifulSoup

from pandas import DataFrame

from app.adapters.base import get_page_content
from app.utils.utils import clean_html


async def get_yandex_weather(city: str) -> dict:
    try:
        page_address = f"https://yandex.ru/pogoda/ru/{city}"
        content = get_page_content(page_address)
        soup = BeautifulSoup(content, "html.parser")
        # forecasts = soup.find_all(class_="AppForecastDay_container__AnH4J")
        forecasts = soup.find_all(class_=re.compile("AppForecastDay_container", re.I))
    except Exception as err:
        return {"is_error": True, "message": err}
        # return {"status": MyLogTypeEnum.ERROR, "message": err}

    error_msg = ""
    result_df = DataFrame()
    for  index, forecast in enumerate(forecasts):
        if index >= 7: # only 7 days
            break
        try:
            date_day = forecast.attrs["data-day"][forecast.attrs["data-day"].rfind("_")+1:]
            # date_day_month = forecast.find(class_="AppForecastDayHeader_dayTitle__23ecF").contents[0]
            date_day_month = clean_html(
                forecast.find(class_=re.compile("AppForecastDayHeader_dayTitle", re.I)).contents[0]
            )
            magnetic_field = ""
            fields = forecast.find_all(class_=re.compile("AppForecastDayDuration_item", re.I))
            for el in fields:
                if el.text.find("Магнитное поле") >= 0:
                    magnetic_field = el.contents[1].text
                    break
            # part of the day (morning, afternoon, evening, night)
            fields = forecast.find_all(style=re.compile("-part", re.I))
            part_day = [el.text for el in fields]
            # temperature
            fields = forecast.find_all(class_=re.compile("AppForecastDayPart_temp", re.I))
            temperature = [int(el.contents[0][:-1]) for el in fields] # remove the degree sign ('+12°' => 12)
            temperature_avg = sum(temperature[:-1]) / len(temperature[:-1])
            # pressure
            fields = forecast.find_all(style=re.compile("-press", re.I))
            pressure = [int(el.text) for el in fields]
            min_, max_ = min(pressure), max(pressure)
            pressure_text = "" if max_ - min_ < 5 else (
                "ожидается резкое увеличение атмосферного давления" if pressure.index(min_) < pressure.index(max_)
                else "ожидается резкое падение атмосферного давления")
            # wetness
            fields = forecast.find_all(style=re.compile("-hum", re.I))
            wetness = [el.text for el in fields]
            # погодное явление (event)
            fields = forecast.find_all(style=re.compile("-text", re.I))
            event = [el.text for el in fields]

            result_df = pd.concat([
                result_df,
                DataFrame({
                    "Дата": date_day_month,
                    "Время суток": part_day,
                    "Температура": temperature,
                    "Средняя температура за световой день": temperature_avg,
                    "Давление": pressure,
                    "Давление (комментарий)": pressure_text,
                    "Влажность": wetness,
                    "Погодное явление": event,
                    "Магнитное поле": magnetic_field,
                })],
                ignore_index=True, sort=False)

        except Exception as err:
            error_msg += f"{err}\n"

    if result_df.empty:
        error_msg = f"Ошибка парсинга сайта: `{page_address}`"

    result = {"message": "", "is_error": False, "result_df": result_df}
    if error_msg:
        result["message"] += f"\nError: {error_msg}"
        result["is_error"] = True

    return result
