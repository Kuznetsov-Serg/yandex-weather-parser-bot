# Yandex Weather parser
### "Yandex Weather parser for Telegram bot"

_(Parsing of trading platforms (https://yandex.ru/pogoda/ru) to inform about Weather in the Telegram channel.)_<br>


## Features:
## Установка и запуск проекта

Перейти в корень проекта: /yandex_weather_parser/


```bash
pip install poetry==1.7.1 # Установка poetry
poetry install # Установка зависимостей из файла pyproject.toml
```

#### pre-commit hooks:

После клонирования репозитория установить pre-commit hooks.<br>
<i>(ToDo)</i><br>
Через poetry

```bash
poetry add -D pre-commit
poetry run pre-commit install
```

Глобальное окружение

```bash
pip install pre-commit
pre-commit install
```


## Requirements:


 - Debian / Ubuntu / Windows Subsystem for Linux
 - Python 3
 - Poetry

## Environments
**_(necessary environment variables)_**

Description of the project:
- PROJECT_NAME="Yandex Weather parser for Telegram bot"
- PROJECT_VERSION=0.1.0
- PROJECT_ENVIRONMENT=prod


- TELEGRAM_TOKEN=***
- PROXY=""
