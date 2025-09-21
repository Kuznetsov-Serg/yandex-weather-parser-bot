import logging
import re
from pydantic import BaseModel, Field, EmailStr, PositiveInt, constr, validator

logger = logging.getLogger(__name__)


class MessageScheme(BaseModel):
    chat_id: int | None = Field(None, description="ИД чата Телеграм")
    user_id: int | None = Field(None, description="ИД пользователя Телеграм")
    content: constr(max_length=1024) | None = Field(None, description="Сообщение")
    command: str | None = Field(None,  description="Команда")
    button: list | None = Field(None,  description="Список кнопок")
    image: bytes | None = Field(None,  description="Картинка")
