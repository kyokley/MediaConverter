FROM python:3.8-alpine AS builder

ARG PREFIX=/opt/ffmpeg
ARG LD_LIBRARY_PATH=/opt/ffmpeg/lib
ARG MAKEFLAGS="-j4"

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV VIRTUAL_ENV=/venv

RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apk add --update --no-cache \
        autoconf \
        automake \
        build-base \
        cmake \
        coreutils \
        curl \
        fdk-aac-dev \
        freetype-dev \
        g++ \
        gcc \
        git \
        lame-dev \
        libass-dev \
        libogg-dev \
        libtheora-dev \
        libtool \
        libvorbis-dev \
        libvpx-dev \
        libwebp-dev \
        linux-headers \
        musl-dev \
        nasm \
        openssl \
        openssl-dev \
        opus-dev \
        pkgconf \
        pkgconfig \
        python3-dev \
        rtmpdump-dev \
        wget \
        x264-dev \
        x265-dev \
        yasm

RUN mkdir /tmp/ffmpeg_sources && \
cd /tmp/ffmpeg_sources && \
wget http://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 && \
tar xjvf ffmpeg-snapshot.tar.bz2 && \
cd ffmpeg && \
PKG_CONFIG_PATH="/usr/bin/pkg-config" ./configure \
  --extra-cflags="-I${PREFIX}/include" \
  --extra-ldflags="-L${PREFIX}/lib" \
  --extra-libs="-lpthread -lm" \
  --prefix="${PREFIX}" \
  --bindir="/usr/local/bin" \
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
make install

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

RUN apk add --update --no-cache \
        ca-certificates \
        openssl \
        pcre \
        lame \
        libogg \
        libass \
        libvpx \
        libvorbis \
        libwebp \
        libtheora \
        opus \
        rtmpdump \
        x264-dev \
        x265-dev

COPY --from=builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=builder /usr/lib/libfdk-aac.so.2 /usr/lib/libfdk-aac.so.2
COPY --from=builder /venv /venv
WORKDIR /workspace

FROM base as prod
COPY . /workspace
CMD celery -A main worker --loglevel=debug --concurrency=1

FROM base as dev
RUN apk add --update --no-cache \
        linux-headers \
        musl-dev \
        gcc \
        git \
        curl

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

COPY pyproject.toml /workspace/pyproject.toml
COPY poetry.lock /workspace/poetry.lock

RUN pip install pip --upgrade && \
    /root/.poetry/bin/poetry install

CMD /bin/sh
