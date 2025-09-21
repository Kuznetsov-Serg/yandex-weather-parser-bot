import asyncio

from dependency_injector.wiring import inject, Provide
from loguru import logger

from app.adapters.db_adapter import WeatherParser
from app.app_container import ApplicationContainer
from app.services.main_telegram_service import MainTelegramBotService
from app.settings import setup_logging, PARSED_CONFIG
# from app.utils.scheduler import app as app_scheduler


# def main():
#     logger.info('App started')
#     try:
#         bot.infinity_polling()
#     except ApiException as e:
#         logger.error(str(e))
@inject
async def main(
    message_consumer_broker: MainTelegramBotService = Provide[
        ApplicationContainer.main_telegram_bot_service
    ],
):
    setup_logging(PARSED_CONFIG.logging)
    WeatherParser()     # Create DB if not enable
    consuming_bot = asyncio.create_task(message_consumer_broker.start_bot())
    await asyncio.gather(consuming_bot)


if __name__ == "__main__":
    try:
        logger.info("App started")
        container = ApplicationContainer()
        container.init_resources()
        container.wire(modules=[__name__])
        asyncio.run(main())
        # main(*sys.argv[1:])
    except Exception as e:
        logger.error(str(e))
