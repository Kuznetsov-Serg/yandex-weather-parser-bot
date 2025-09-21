import asyncio
import collections
import time

from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from loguru import logger

from app.services.dialog_flow import CommandToBack, DialogFlow, HTML, Message, Photo, CommandToTelegram, File
from app.utils.utils import run_async


class TelegramService:
    """
    Class for working with Telegram
    """

    def __init__(self, token: str, proxy: str, dialog_flow: DialogFlow, generator=None):
        self.dialog_flow = dialog_flow
        self.generator = generator

        self.session = AiohttpSession(proxy=proxy) if proxy else AiohttpSession()
        self.bot = Bot(token=token, session=self.session)

        self.dispatcher = Dispatcher()
        # self.dispatcher = Dispatcher(self.bot)
        self._set_handlers_for_dispatcher()
        self.combined_messages = {}
        self.handlers = collections.defaultdict(
            self.generator
        )  # заводим мапу "id чата -> генератор"

    def _set_handlers_for_dispatcher(self):
        """
        Adding handlers for events from Telegram
        """
        # self.dispatcher.message.register(self.start_handler, Command("start"))
        self.dispatcher.message.register(self.end_handler, Command("end"))
        # dp.add_handler(MessageHandler(Filters.text, parrot))  # обработчкик текстового сообщения
        self.dispatcher.message.register(self.process_messages)
        self.dispatcher.callback_query.register(self.callback_inline)

    async def start_listener(self):
        """
        Start listening to messages from Telegram
        """
        while True:
            try:
                await self.dispatcher.start_polling(self.bot)
            except Exception as e:
                logger.error({str(e)})
                time.sleep(5)

    async def send_message(self, *args, **kwargs):
        await self.bot.send_message(*args, **kwargs)

    async def start_handler(self, message: types.Message):
        try:
            with open("app/static/logo.png", "rb") as in_file:  # opening for [r]eading as [b]inary
                logo = in_file.read()
        except:
            logo = None
        # await self.bot.send_message(message.chat.id, "Бот запущен")
        username = message.chat.first_name
        await self.send_answer(
            message.chat.id,
            [
                Photo(logo) if logo else None,
                HTML(
                    f"Привет, <b>{username}</b>, я - <b>Yandex Weather Bot</b>, "
                    "ваш помощник в получении информации о погоде в формате 24/7.\n"
                    f"Будем знакомы.\nКак лучше к тебе обращаться?\n"
                ),
                [[username, f"flow_user_name_add {username}"]],
            ],
        )

    async def end_handler(self, message: types.Message):
        await self.bot.send_message(message.chat.id, "Бот остановлен")

    async def process_messages(self, message: types.Message):
        """
        Telegram message processing function
        """
        chat_id = message.chat.id
        user_id = message.from_user.id

        if user_id in self.combined_messages:
            self.combined_messages[user_id] += f"\n{message.text}"
        else:
            self.combined_messages[user_id] = message.text
        await asyncio.sleep(1)

        if self.combined_messages.get(user_id) and (
            message.forward_from_chat is None
            or message.forward_from_chat.type != "channel"
        ):
            try:
                mes = self.combined_messages[user_id]
                del self.combined_messages[user_id]
                logger.info("Received", mes)
                if mes == "/start":
                    # если передана команда /start, начинаем всё с начала -- для
                    # этого удаляем состояние текущего чатика, если оно есть
                    self.handlers.pop(chat_id, None)

                if chat_id not in self.handlers:  # начало общения
                    # self.handlers[chat_id] = flow_default()  # значит, запустим default DialogFlow
                    self.handlers[chat_id] = None  # значит, запустим default DialogFlow

                # в получаемом кортеже может смениться активный DialogFlow (команды)
                answer, self.handlers[chat_id] = self.dialog_flow.dialog_flow(
                    function_or_generator=self.handlers[chat_id],
                    chat_id=chat_id,
                    username=message.from_user.first_name,
                    text=mes,
                )
                # отправляем полученный ответ пользователю
                logger.info(f"answer={answer}")
                await self.send_answer(chat_id, answer)
                # await self.bot.send_message(chat_id, f"Задача на получение информации создана\n{answer}")
                logger.info(f"через БОТ в чат {chat_id} направлен ответ: {answer}")

            except KeyError as e:
                logger.error(str(e))

    async def send_answer(self, chat_id, answer):
        # logger.info("Sending answer %r to %s" % (answer, chat_id))
        if answer == "":  # Google не всегда отвечает
            return
        if isinstance(answer, collections.abc.Iterable) and not isinstance(answer, str):
            # мы получили несколько объектов -- сперва каждый надо обработать
            answer = [self._convert_answer_part(el, chat_id) for el in answer]
        else:
            # мы получили один объект -- сводим к более общей задаче
            answer = [self._convert_answer_part(answer, chat_id)]

        # перед тем, как отправить очередное сообщение, идём вперёд в поисках
        # «довесков» -- клавиатуры там или в перспективе ещё чего-нибудь
        current_message = None
        command = None
        for part in answer:
            if isinstance(part, CommandToBack):
                # for sending to KAFKA
                # message = MessageScheme(user_id=chat_id, command=part.command, content=part.content)
                # await self.kafka.send_message(dict(message), partition_key=b"to_back")
                # print(f"Send to KAFKA {dict(message)}")
                logger.info(f"в KAFKA отпралено сообщение: {part}")
            if isinstance(part, CommandToTelegram):
                # for sending to Telegram
                command = part
            if isinstance(part, Photo):
                if part.image:
                    if current_message is not None:
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=current_message.text,
                            **current_message.options,
                        )
                        current_message = None
                    await self.bot.send_photo(chat_id=chat_id, photo=part.image)
                # part = Message(part.text)
            if isinstance(part, File):
                if part.file:
                    if current_message is not None:
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=current_message.text,
                            **current_message.options,
                        )
                        current_message = None
                    await self.bot.send_document(chat_id=chat_id, document=part.file)
                # part = Message(part.text)
            if isinstance(part, Message):
                if current_message is not None:
                    options = dict(current_message.options)
                    options.setdefault("disable_notification", True)
                    self.bot.message.reply_text(text=current_message.text, **options)
                current_message = part
            if isinstance(part, ReplyKeyboardMarkup | InlineKeyboardMarkup):
                if current_message is None:
                    current_message = HTML("Просьба, выбрать <b>пункт меню</b>:")
                current_message.options["reply_markup"] = part

        if current_message is not None:
            await self.bot.send_message(
                chat_id=chat_id, text=current_message.text, **current_message.options
            )
        if command:
            answer_add, self.handlers[chat_id] = self.dialog_flow.dialog_flow(
                # function_or_generator=self.handlers[chat_id],
                chat_id=chat_id,
                text=command.command,
            )
            await self.send_answer(chat_id=chat_id, answer=answer_add)

    def _convert_answer_part(self, answer_part, user_id: int):
        buttons_per_row = 2
        if not answer_part or answer_part == []:
            return None
        if isinstance(answer_part, str):
            return Message(answer_part)
        if isinstance(answer_part, collections.abc.Iterable):  # Кнопки
            answer_part = list(answer_part)
            if isinstance(answer_part[0], str):  # кнопки из локального DialogFlow
                # она! оформляем как горизонтальный ряд кнопок.
                # кстати, все наши клавиатуры одноразовые -- нам пока хватит.
                # return ReplyKeyboardMarkup([answer_part], one_time_keyboard=True, resize_keyboard=True)

                # For InLine Buttons with CallBack
                buttons = [InlineKeyboardButton(text=self.dialog_flow.add_img_in_command(el), callback_data=el) for el
                           in answer_part]
                buttons = self._buttons_in_rows(buttons, user_id)    # forced into one line
                # buttons = [buttons[i:i + buttons_per_row] for i in range(0, len(buttons), buttons_per_row)]
                return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=buttons_per_row)
            if isinstance(answer_part[0], list):  # кнопки с подписями из локального DialogFlow
                # For InLine Buttons with CallBack or ref
                buttons = []
                for el in answer_part:
                    if el[1].lower().startswith("https://") or el[1].lower().startswith("http://"):
                        buttons.append(InlineKeyboardButton(text=self.dialog_flow.add_img_in_command(el[0]), url=el[1]))
                    else:
                        buttons.append(
                            InlineKeyboardButton(text=self.dialog_flow.add_img_in_command(el[0]), callback_data=el[1]))
                # buttons = [InlineKeyboardButton(text=self.dialog_flow.add_img_in_command(el[0]), callback_data=el[1])
                #            for el in answer_part]
                buttons = self._buttons_in_rows(buttons, user_id)    # forced into one line
                # buttons = [buttons[i:i + buttons_per_row] for i in range(0, len(buttons), buttons_per_row)]
                return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)
            elif isinstance(answer_part[0], dict):  # кнопки от Google DialogFlow
                # return ReplyKeyboardMarkup([answer_part], one_time_keyboard=True, resize_keyboard=True)
                buttons_url = [InlineKeyboardButton(text=el['text'], url=el['action']) for el in answer_part if
                               el['action'] != 'callback']
                buttons = [el['text'] for el in answer_part if el['action'] == 'callback']
                # buttons = [InlineKeyboardButton(text=el['text'], callback_data=el['text']) for el in answer_part if el['action'] == 'callback']
                if len(buttons):
                    # хоть и пришли кнопки с CallBack, не будем заморачиваться и отправим их в нижню строку
                    return ReplyKeyboardMarkup([buttons], one_time_keyboard=True, resize_keyboard=True)
                else:
                    return InlineKeyboardMarkup([buttons_url], row_width=1)  # кнопки с URL
            elif isinstance(answer_part[0], collections.abc.Iterable):  # двумерная клавиатура внутреннего DialogFlow
                if isinstance(answer_part[0][0], str):
                    # она!
                    # return InlineKeyboardMarkup(map(list, answer_part), url='https://github.com/markdrrr/interview_questions_python_junior/')
                    return ReplyKeyboardMarkup(map(list, answer_part), one_time_keyboard=True, resize_keyboard=True)
        return answer_part

    def _buttons_in_rows(self, buttons: list, user_id: int):
        result = []
        current_row = []
        current_len = 0
        try:
            user = run_async(self.dialog_flow.weather_parser.user_get, self.dialog_flow.weather_parser, user_id)
            menu_scale = (user.menu_scale or 0)
        except:
            menu_scale = 0
        for count in range(len(buttons)):
            button_len = len(buttons[count].text) + 2
            if current_len and current_len + button_len > 34 - menu_scale * 5 \
                    or self.dialog_flow.get_command_from_str(buttons[count].text.lower())[0] in self.dialog_flow.command_exit:
                result.append(current_row)
                current_row = []
                current_len = 0
            current_row.append(buttons[count])
            current_len += button_len
        if current_row:
            result.append(current_row)
        return result

    async def callback_inline(self, call: CallbackQuery):
        if not call.data:
            return
        try:
            chat_id = call.from_user.id
            command = call.data
            param = None
            logger.info(f"Received command: '{command}'")
            if command == "/start":
                # если передана команда /start, начинаем всё с начала -- для
                # этого удаляем состояние текущего чатика, если оно есть
                self.handlers.pop(chat_id, None)
            command_startswith = command.split(" ")[0]
            if command_startswith in list(self.dialog_flow.command_dict):
                try:
                    param = command.split(" ")[1]
                except:
                    param = None
                command = command_startswith

            if chat_id not in self.handlers:  # начало общения
                self.handlers[chat_id] = None  # значит, запустим default DialogFlow

            # в получаемом кортеже может смениться активный DialogFlow (команды)
            answer, self.handlers[chat_id] = self.dialog_flow.dialog_flow(
                function_or_generator=self.handlers[chat_id],
                chat_id=chat_id,
                username=call.from_user.first_name,
                text=command,
                param=param,
            )
            # отправляем полученный ответ пользователю
            # logger.info(f"answer={answer}")
            await self.send_answer(chat_id, answer)
            # logger.info(f"через БОТ в чат {chat_id} направлен ответ: {answer}")

        except KeyError as e:
            logger.error(str(e))

    async def close(self):
        await self.dispatcher.stop_polling()
        await self.session.close()
