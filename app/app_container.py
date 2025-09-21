from dependency_injector import containers, providers

from app.adapters.db_adapter import WeatherParser
from app.adapters.telegram import TelegramService
from app.services.dialog_flow import DialogFlow
from app.services.main_telegram_service import MainTelegramBotService
from app.settings import PARSED_CONFIG


class ApplicationContainer(containers.DeclarativeContainer):
    """
    The main application container
    """
    dialog_flow = providers.Singleton(
        DialogFlow,
        WeatherParser,
    )
    bot = providers.Singleton(
        TelegramService,
        token=PARSED_CONFIG.telegram_token,
        dialog_flow=dialog_flow,
        proxy=PARSED_CONFIG.proxy,
    )
    main_telegram_bot_service = providers.Factory(
        MainTelegramBotService,
        bot=bot,
    )

