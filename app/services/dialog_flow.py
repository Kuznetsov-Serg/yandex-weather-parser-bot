# Dialog_Flow
import datetime
import re
import types

from collections.abc import Iterable
from itertools import chain

from aiogram.types import BufferedInputFile
from loguru import logger

from app.adapters.db_adapter import WeatherParser
from app.utils.utils import run_async, table_writer


class DialogFlow(object):
    """
    *********************************************************************
    The class Dialog-Flow
    *********************************************************************
    """

    command_dict = {
        "flow_start": {
            "description": "Стартовое меню",
            "list": ["start", "старт", "привет"],
        },
        "flow_help": {
            "description": "Список доступных команд (помощь)",
            "list": ["help", "h", "?", "помощь", "список команд"],
            "img": "ℹ",
        },
        "flow_main_menu": {
            "description": "Основное меню (разделы информации)",
            "list": ["меню", "основное меню", "main menu", "menu"],
            "img": "🔝",
        },
        "flow_user_get": {
            "description": "Информация обо мне",
            "list": ["информация обо мне"],
            "img": "ℹ️",
        },
        "flow_weather_menu": {
            "description": "Прогноз погоды",
            "list": ["прогноз погоды"],
            "img": "🌦",
        },
        "flow_weather_get": {
            "description": "Прогноз погоды в Excel",
            "list": ["прогноз погоды в excel"],
            "img": "🧾",
        },
        "flow_log_get": {
            "description": "Логи запросов прогноза погоды",
            "list": ["логи", "лог", "лог последних запросов", "история"],
            "img": "📄",
        },
        "flow_city_get": {
            "description": "Справочник городов",
            "list": ["города", "справочник городов"],
            "img": "🌇",
        },
        "flow_city_enter": {
            "description": "Ввести город вручную",
            "list": ["ввести город вручную"],
            "img": "",
        },
        "flow_exit": {
            "description": "Выход",
            "list": ["выйти", "выход", "завершить", "закончить", "конец", "отмена",
                     "finish", "close", "end", "exit", "stop"],
            "img": "🔚",
        },
    }

    command_exit = command_dict["flow_exit"]["list"]
    button_default = ["Основное меню", "Прогноз погоды" , "Список команд"]

    def __init__(self, weather_parser: WeatherParser):
        self.weather_parser = weather_parser
        self.command_list = list(chain.from_iterable([el["list"] for el in self.command_dict.values()])) + list(
            self.command_dict)

    def add_img_in_command(self, command: str) -> str:
        img = ""
        for key, value in self.command_dict.items():
            if command.lower() in value["list"] + [key]:
                try:
                    img = value["img"] + " "
                except:
                    pass
                break
        return img + command

    def get_command_from_str(self, arg_str: str) -> tuple:
        def _is_command_in_dict(command: str) -> bool:
            for key, value in self.command_dict.items():
                if command in list(map(str.lower, (value["list"] + [key]))):
                    return True
            return False

        # remove the img from the content
        img_list = [self.command_dict[el]["img"] for el in self.command_dict if "img" in self.command_dict[el]]
        command = re.sub(r"|".join(map(re.escape, ["/"] + img_list)), "", arg_str.lower()).strip()

        if _is_command_in_dict(command):
            return command, None

        if len(command.split(" ")) < 2:
            return None, None

        # finding the index of last space
        index = command.rfind(" ")
        command, param = command[:index], command[index + 1:]
        return (command, param) if _is_command_in_dict(command) else (None, None)

    def dialog_flow(self, function_or_generator=None, chat_id=None, username='', text='', param: str = None):
        if self.is_command_dialog_flow(text):  # Ответ является командой
            # выберем и запустим локальный генератор
            function_or_generator = self.get_dialog_flow(text, chat_id=chat_id, username=username, param=param)
            answer = next(function_or_generator)  # в первый раз - next (.send() срабатывает только после первого yield)
        else:
            if isinstance(function_or_generator, types.GeneratorType):  # если функция - Генератор
                try:
                    answer = function_or_generator.send(HTML(text))  # запрос в локальный DialogFlow
                except StopIteration:  # если генератор закончился, продолжаем общение с DEFAULT
                    # function_or_generator = globals()['flow_default'](chat_id, username)
                    function_or_generator = self.__getattribute__("flow_default")(chat_id, username)
                    answer = next(
                        function_or_generator)  # в первый раз - next (.send() срабатывает только после первого yield)
                    # answer = ask_google_dialog_flow(text, chat_id)  # запрос в Google DialogFlow
            else:
                # function_or_generator = globals()['flow_default'](chat_id, username)
                function_or_generator = self.__getattribute__("flow_default")(chat_id, username)
                answer = next(
                    function_or_generator)  # в первый раз - next (.send() срабатывает только после первого yield)
                # answer = ask_google_dialog_flow(text, chat_id)  # запрос в Google DialogFlow
        return answer, function_or_generator

    '''
    *********************************************************************
     Блок определения скрипта DialogFlow по спец-командам
    *********************************************************************
    '''

    def is_command_dialog_flow(self, arg_str: str) -> bool:
        command, param = self.get_command_from_str(arg_str)
        return command in self.command_list

    def get_dialog_flow(self, arg_str: str, chat_id=None, username=None, param: str = None):
        command, param_ = self.get_command_from_str(arg_str)
        for key, value in self.command_dict.items():
            if command in value["list"] + [key]:
                return self.__getattribute__(key)(chat_id, username, param=(param or param_))
                # return globals()[key](chat_id, username)
        return None

    def flow_start(self, chat_id=None, username=None, *args, **kwargs):
        """
        *********************************************************************
         DialogFlow стартовый, для ...
        *********************************************************************
        """
        try:
            with open("app/static/megafon_logo.png", "rb") as in_file:  # opening for [r]eading as [b]inary
                logo = in_file.read()
        except:
            logo = None

        answer = yield (
            Photo(logo) if logo else None,
            HTML(f"Привет <b>{username}</b>, я - <b>Прогноз погоды Yandex Bot</b>:)\n"
                 "Ваш помощник в погодных данных.\nБудем знакомы.\nКак лучше к тебе обращаться?\n"),
            [username]
        )
        # убираем ведущие знаки пунктуации, оставляем только
        # первую компоненту имени, пишем её с заглавной буквы
        try:
            username = answer.text.rstrip(".!").capitalize()
            result = run_async(self.weather_parser.user_add, self.weather_parser, chat_id, username)
        except:
            pass

        answer = yield "Отлично!", self.button_default
        return answer

    def flow_default(self, chat_id=None, username=None, *args, **kwargs):
        """
        *********************************************************************
         DialogFlow "by default"
        *********************************************************************
        """
        answer, choice = yield from self.ask_list_answer(HTML(f"<b>{username}</b>, сделайте выбор:"),
                                                         self.button_default)
        return answer

    def flow_exit(self, chat_id=None, username=None, *args, **kwargs):
        """
        *********************************************************************
         DialogFlow "exit"
        *********************************************************************
        """
        return self.flow_default(chat_id, username, *args, **kwargs)

    def flow_help(self, chat_id=None, username=None, *args, **kwargs):
        """
        *********************************************************************
         Dialog Flow to display a list of commands
        *********************************************************************
        """
        answer = ""
        for el in self.command_dict.values():
            answer += f"\n<b>{el['list'][0]}</b> - {el['description']}\n<i>{el['list'][1:]}</i>"
        answer = yield HTML(f"Перечень <b>команд</b>:\n{answer}"), self.button_default
        return answer

    def flow_main_menu(self, chat_id=None, username=None, *args, **kwargs):
        """
        *********************************************************************
         Dialog Flow for main Menu
        *********************************************************************
        """
        main_menu = ["Прогноз погоды", "Информация обо мне", "Лог последних запросов"]
        answer = ""
        while not answer or answer.text.lower() in self.command_list:
            answer = yield HTML(f"Просьба выбрать <b>действие</b>:"), main_menu

        return answer

    def flow_user_get(self, chat_id=None, username=None, *args, **kwargs):
        """
        *********************************************************************
         Dialog Flow for getting User info
        *********************************************************************
        """
        content = run_async(self.weather_parser.user_get, self.weather_parser, chat_id)
        answer = yield HTML(str(content)), self.button_default
        return answer

    def flow_log_get(self, chat_id=None, username=None, *args, **kwargs):
        """
        *********************************************************************
         Dialog Flow for getting last logs
        *********************************************************************
        """
        content = run_async(self.weather_parser.log_get, self.weather_parser)
        answer = yield HTML(str(content)), self.button_default
        return answer

    def flow_weather_menu(self, chat_id=None, username=None, *args, **kwargs):
        """
        *********************************************************************
         Dialog Flow to ...
        *********************************************************************
        """
        result = run_async(self.weather_parser.user_city_get, chat_id)
        button = [["Ввести город (первые буквы) вручную", "flow_city_enter"], ["Основное меню", "Основное меню"]]
        if result is None:
            content = "Ваша история парсинга по городам пуста"
        else:
            content = "Выберите город:"
            button += [[el['name_ru'].capitalize(), f"flow_weather_get {el['name_en']}"] for el in result]

        answer = yield HTML(content), button
        return answer

    def flow_city_enter(self, chat_id=None, username=None, *args, **kwargs):
        """
        *********************************************************************
         Dialog Flow for getting City name from chat
        *********************************************************************
        """
        answer = ""
        while not answer:
            answer = yield HTML(f"Просьба ввести <b>наименование города</b> <i>(несколько первых букв)</i>, "
                                f"или нажать кнопку <b>ВЫЙТИ</b>:"), ["Выйти"]
            if answer.text.lower() in self.command_exit:
                return answer
            result = run_async(self.weather_parser.city_get, self.weather_parser, answer.text)
            if not result:
                answer = yield HTML(f"Города, включающего `{answer.text}` в справочнике не обнаружено..."), ["Основное меню"]

        # if len(result) == 1:
        #     answer = yield self.flow_weather_get(chat_id, param=result[0]["name_en"])
        # else:
        button = [["Основное меню", "Основное меню"]] + [[el['name_ru'].capitalize(), f"flow_weather_get {el['name_en']}"] for el in result]
        answer = yield HTML("Выберите город:"), button
        return answer

    def flow_weather_get(self, chat_id=None, username=None, *args, **kwargs):
        city = kwargs['param']
        result = run_async(self.weather_parser.weather_get, self.weather_parser, chat_id, city)
        if result["is_error"]:
            answer = yield HTML(result["message"]), self.button_default
        else:
            stream = table_writer(dataframes={f"{city}": result["result_df"]}, param="xlsx")
            answer = yield File(stream.getvalue(), f"{datetime.date.today()}_{city}.xlsx"), self.button_default
        return answer

    def flow_city_get(self, chat_id=None, username=None, *args, **kwargs):
        """
        *********************************************************************
         Dialog Flow for getting City from spr
        *********************************************************************
        """
        result = run_async(self.weather_parser.city_get, self.weather_parser)
        if result is None:
            content = "Справочник городов пуст"
            button = self.button_default
        else:
            content = "Выберите город:"
            button = [[el['name_ru'], f"flow_weather_get {el['name_en']}"] for el in result]
            button.append(["Основное меню", "Основное меню"])

        answer = yield HTML(content), button
        return answer

    '''
    *********************************************************************
    Блок универсальных вопросов-ответов
    *********************************************************************
    '''

    @staticmethod
    def ask_yes_or_no(question):
        """Спросить вопрос и дождаться ответа, содержащего «да» или «нет».
        Возвращает:
            bool
        """
        try:
            # return ask_list_answer(question)
            answer = yield (question, ["Да ✅", "Нет ❌"])
            logger.info(f"answer={answer}")
            while not ("да" in answer.text.lower() or "нет" in answer.text.lower()):
                answer = yield HTML("Так <b>да</b> или <b>нет</b>?")
                logger.info(f"answer2={answer}")
                # answer_ = answer.text.lower() if answer else ""
            return "да" in answer.text.lower()
        except:
            return False

    def ask_list_answer(self, question, list_answer, photo_obj=None):
        """Спросить вопрос и дождаться ответ, из списка вариантов.
        Возвращает:
            number
        """
        if photo_obj:  # Есть фото - поставим первым
            answer = yield (photo_obj, question, list_answer)
        else:
            answer = yield (question, list_answer)
        list_answer = list(self.flatten_lower(list_answer))  # избавимся от вложенности в массиве и переведем в lower
        while not (answer.text.lower() in list_answer):
            answer = yield HTML("Прошу ввести вариант или нажать кнопку?")
        return answer.text, list_answer.index(answer.text.lower())

    @staticmethod
    def ask_list_answer1(question, list_yes=['да', 'ок', 'yes', 'ok'], list_no=['нет', 'not']):
        """Спросить вопрос и дождаться ответа, содержащегоcя в списке list_yes или list_no

        Возвращает:
            bool
        """
        answer = yield question
        while not (answer.text.lower() in list_yes or answer.text.lower() in list_no):
            answer = yield HTML(
                "Так все-же, выберете?\n(<b>" + ', '.join(list_yes) + "</b>)\nили\n(<b>" + ', '.join(list_no) + "</b>)")
        return answer.text.lower() in list_yes

    def flatten_lower(self, list):
        """ Функция разворачивания списка любой вложенности с переводом текста в нижний регистр """
        for item in list:
            if isinstance(item, Iterable) and not isinstance(item, str):
                for x in self.flatten_lower(item):
                    yield x
            else:
                yield item.lower()

    @staticmethod
    def get_chart_path(string):
        """
        Автоматически добавляет относительный URL-путь к медиафайлам диаграм
        chart/product1.jpg --> /media/chart/product1.jpg
        если это не является ссылкой в интернете http:// https:// и т.д.
        """
        if not string:
            string = 'chart/default.jpg'
            # string = 'media/chart/cat_avatar.jpg'
        elif string.name.find(':') != -1:
            return string

        return f'MEDIA_URL{string}'
        # return f'{MEDIA_URL}{string}'


# Класс для текста без "украшательств"
class Message(object):
    def __init__(self, text, **options):
        self.text = text
        self.options = options


# Класс для текста в HTML-формате
class HTML(Message):
    def __init__(self, text, **options):
        super(HTML, self).__init__(text, parse_mode="HTML", **options)


# Класс для картинок
class Photo(object):
    def __init__(self, image: bytes = None, content: str = None, **options):
        self.image = BufferedInputFile(image, "test.png") if image else None
        self.content = content


# Класс для файлов
class File(object):
    def __init__(self, file: bytes = None, file_name: str = "file_name.txt", content: str = None, **options):
        self.file = BufferedInputFile(file, file_name) if file else None
        self.content = content


class CommandToBack(object):
    def __init__(self, chat_id: int, command: str, content: str = None):
        self.chat_id = chat_id
        self.command = command
        self.content = content


class CommandToTelegram(object):
    def __init__(self, command: str, content: str = None):
        self.command = command
        self.content = content
