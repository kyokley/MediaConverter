FROM python:3.8-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV VIRTUAL_ENV=/venv

RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apk add --update --no-cache \
        linux-headers \
        python3-dev \
        musl-dev \
        gcc \
        curl

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

WORKDIR /workspace

COPY pyproject.toml /workspace/pyproject.toml
COPY poetry.lock /workspace/poetry.lock

# Set up virtual environment
RUN pip install pip --upgrade && \
    /root/.poetry/bin/poetry install --no-dev

FROM python:3.8-alpine AS base
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV VIRTUAL_ENV=/venv

RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY --from=builder /venv /venv
WORKDIR /workspace

FROM base as prod
COPY . /workspace
CMD /bin/sh

FROM base as dev
RUN apk add --update --no-cache \
        curl

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

COPY pyproject.toml /workspace/pyproject.toml
COPY poetry.lock /workspace/poetry.lock

RUN pip install pip --upgrade && \
    /root/.poetry/bin/poetry install

CMD /bin/sh
