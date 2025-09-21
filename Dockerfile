FROM nexus.pgk.ru/base-images/python:3.11-bookworm-postgres AS builder

WORKDIR /opt

COPY app ./app
COPY config.yaml ./
COPY main.py  ./
COPY poetry.lock ./
COPY pyproject.toml ./

RUN apt-get update; \
    apt-get install -y \
        wget \
        unzip \
        python3-dev \
        slapd \
        build-essential

RUN poetry config virtualenvs.in-project true; \
    poetry install --no-root;

FROM nexus.pgk.ru/base-images/python:3.11-bookworm-slim-postgres

WORKDIR /opt

RUN apt-get update; \
    apt-get install -y \
        firefox-esr \
        procps; \
    apt-get autoremove -y; \
    apt-get clean -y; \
#    chmod ugo+x ./app/driver/geckodriver; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/log/*; 

ENV TZ=Europe/Moscow \
    VIRTUAL_ENV=/opt/.venv \
    PATH="/opt/.venv/bin:$PATH" \
    PYTHONPATH=/opt/.venv

COPY --from=builder /opt .

CMD ["python", "main.py"]
