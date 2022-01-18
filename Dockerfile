ARG BASE_IMAGE=python:3.10-slim

FROM ${BASE_IMAGE} AS base

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV POETRY_VENV=/poetry_venv
RUN python3 -m venv $POETRY_VENV

ENV VIRTUAL_ENV=/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN sed -i -e's/ main/ main contrib non-free/g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y \
        g++ \
        git \
        wget \
        yasm \
        nasm \
        cmake \
        cmake-curses-gui \
        libvorbis-dev \
        libx264-dev \
        libx265-dev \
        libnuma-dev \
        libvpx-dev \
        libass-dev \
        libfdk-aac-dev \
        libmp3lame-dev \
        libopus-dev \
        libtheora-dev

WORKDIR /tmp
RUN git clone https://github.com/videolan/x265
WORKDIR  /tmp/x265
RUN cmake source && \
        make && \
        make install

WORKDIR /tmp/ffmpeg_sources
RUN wget http://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 && \
        tar xjvf ffmpeg-snapshot.tar.bz2

WORKDIR /tmp/ffmpeg_sources/ffmpeg
RUN PKG_CONFIG_PATH="/usr/bin/pkg-config" ./configure \
        --prefix="$HOME/ffmpeg_build" \
        --pkg-config-flags="--static" \
        --extra-cflags="-I$HOME/ffmpeg_build/include" \
        --extra-ldflags="-L$HOME/ffmpeg_build/lib -L/usr/local/lib" \
        --bindir="/usr/local/bin" \
        --enable-static \
        --enable-gpl \
        --enable-libass \
        --enable-libfdk-aac \
        --enable-libfreetype \
        --enable-libmp3lame \
        --enable-libopus \
        --enable-libtheora \
        --enable-libvorbis \
        --enable-libvpx \
        --enable-libx264 \
        --enable-libx265 \
        --enable-nonfree && \
        make && \
        make install && \
        ldconfig && \
        rm -rf /tmp/x265 /tmp/ffmpeg_sources $HOME/ffmpeg_build

RUN $POETRY_VENV/bin/pip install -U pip poetry && $VIRTUAL_ENV/bin/pip install -U pip

WORKDIR /code
COPY poetry.lock pyproject.toml /code/

RUN $POETRY_VENV/bin/pip install poetry && $POETRY_VENV/bin/poetry install --no-dev

CMD ["/venv/bin/celery", "-A", "main", "worker", "--loglevel=info", "--concurrency=1"]


# ********************* Begin Prod Image ******************
FROM base AS prod
COPY . /code


# ********************* Begin Dev Image ******************
FROM base AS dev
RUN $POETRY_VENV/bin/poetry install
