import datetime
import sqlite3

import pandas as pd
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import BufferedInputFile

from app.settings import PARSED_CONFIG
from app.utils.utils import table_writer, run_async

def create_city_spr():
        df = pd.read_csv("city_spr.csv")
        df.rename(columns={"name-en": "name_en", "name-ru": "name_ru"}, inplace=True)
        df["name_ru"] = df["name_ru"].str.lower()
        df["name_en"] = df["name_en"].str.replace(" ", "-").str.lower()
        df["id"] = df.index
        connection = sqlite3.connect(PARSED_CONFIG.sqlite_db)
        df[["name_en", "name_ru"]].to_sql(name='City', con=connection, if_exists='append', index=False)

def send_excel_to_bot():
        session = AiohttpSession(proxy=PARSED_CONFIG.proxy) if PARSED_CONFIG.proxy else AiohttpSession()
        bot = Bot(token=PARSED_CONFIG.telegram_token, session=session)

        # initialize data of lists.
        data = {'Name': ['Tom', 'nick', 'krish', 'jack'],
                'Age': [20, 21, 19, 18]}

        # Create DataFrame
        df = pd.DataFrame(data)
        stream = table_writer(dataframes={f"{datetime.date.today()}_": df}, param="xlsx")

        try:
                with open("../static/megafon_logo.png", "rb") as in_file:  # opening for [r]eading as [b]inary
                        logo = in_file.read()
                # run_async(bot.send_photo, 178698488, BufferedInputFile(logo, "megafon_logo.png"))
        except Exception as err:
                print(err)

        file = BufferedInputFile(stream.getvalue(), "ttt.xlsx")
        run_async(bot.send_document, 178698488, file)


create_city_spr()



