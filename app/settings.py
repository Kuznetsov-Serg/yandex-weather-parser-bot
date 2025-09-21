import datetime
import enum
import os

# from logging.config import dictConfig
from logging.config import dictConfig
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, BaseModel, PositiveInt, StrictStr

from app.utils.utils import merge, read_yaml


PROJ_ROOT = Path(__file__).parent.parent
config_env_var = "ONFIG_PATH"
DEFAULT_PATH = PROJ_ROOT / "config.yaml"
ENV_PATH = Path(os.environ.get(config_env_var) or "")

COOKIE_EXPIRATION_TIME = datetime.datetime.now() + datetime.timedelta(days=1000)
COOKIE_EXPIRATION_DATE = COOKIE_EXPIRATION_TIME.strftime("%a, %d %b %Y %H:%M:%S GMT")

dotenv_path = Path(__file__).parent.parent.joinpath(".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

LoggingConfig = dict[str, Any]


def get_variable(name: str, default_value: bool | None = None) -> bool:
    true_ = (
        "true",
        "1",
        "t",
    )  # Add more entries if you want, like: `y`, `yes`, `on`, ...
    false_ = (
        "false",
        "0",
        "f",
    )  # Add more entries if you want, like: `n`, `no`, `off`, ...
    value: str | None = os.getenv(name, None)
    if value is None:
        if default_value is None:
            raise ValueError(f"Variable `{name}` not set!")
        else:
            value = str(default_value)
    if value.lower() not in true_ + false_:
        raise ValueError(f"Invalid value `{value}` for variable `{name}`")
    return value in true_


class EmptyCustomConfig(Exception):
    def __init__(self, path: Path):
        self.path = path

    def __str__(self) -> str:
        return f"Config file {self.path} is empty"


class JWTConfiguration(BaseModel):
    jwt_secret: str
    jwt_algorithm: str = "RS256"
    jwt_access_token_days: int = 2


class RateLimit(BaseModel):
    is_enable: bool = False
    second: int = 10
    minute: int = 100


class Configuration(BaseModel):
    project_name: StrictStr
    project_version: str
    project_environment: str

    sqlite_db: str = str(PROJ_ROOT / "app/db/weather_db.db")

    telegram_token: str
    proxy: str = ""

    logging: LoggingConfig


# @lru_cache
def load_configuration(path: Path = "") -> Configuration:
    arg_path = Path(path)
    default_config = read_yaml(DEFAULT_PATH)

    custom_config_path = (arg_path.is_file() and arg_path) or (
        ENV_PATH.is_file() and ENV_PATH
    )
    if custom_config_path:
        custom_config = read_yaml(custom_config_path)

        if not custom_config:
            raise EmptyCustomConfig(path=custom_config_path)
        config_data = merge(default_config, custom_config)
    else:
        config_data = default_config

    config_data = {
        key: {key1: val1 for key1, val1 in val.items() if val1 != "None"}
        if isinstance(val, dict)
        else val
        for key, val in config_data.items()
        if val != "None"
    }

    return Configuration(**config_data)

#
# def setup_logging(logging_config: LoggingConfig):
#     dictConfig(logging_config)


def dump_config(config: Configuration) -> str:
    return config.json(indent=2, sort_keys=True)


def setup_logging(logging_config: LoggingConfig):
    dictConfig(logging_config)


PARSED_CONFIG = load_configuration()
EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
