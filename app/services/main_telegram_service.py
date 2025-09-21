import asyncio
import base64

from loguru import logger

from app.adapters.telegram import TelegramService
from app.schemes import MessageScheme
from app.services.dialog_flow import HTML, Photo


class MainTelegramBotService:
    """
    Service for working with Telegram
    """

    def __init__(self, bot: TelegramService):
        self.bot = bot
        self.loop = asyncio.get_event_loop()

    async def start_bot(self):
        await self.bot.start_listener()

    async def process_message(self, message: MessageScheme):
        logger.info(
            f"from kafka consume message for User_ID={message.user_id}: {message.content}"
        )

        await self.bot.send_answer(
            chat_id=message.user_id,
            answer=(
                HTML(message.content),
                Photo(base64.b64decode(message.image)) if message.image else None,
                message.button,
            ),
        )

    async def close(self):
        await self.bot.close()
