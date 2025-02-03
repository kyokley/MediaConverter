ARG BASE_IMAGE=python:3.12-slim

FROM ${BASE_IMAGE} AS base-builder

RUN sed -i -e's/ main/ main contrib non-free non-free-firmware/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
        g++ \
        git \
        wget \
        yasm \
        nasm \
        cmake \
        cmake-curses-gui \
        libavcodec-dev \
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

WORKDIR /build


FROM base-builder AS x265-builder
RUN git clone --depth=1 https://github.com/videolan/x265.git
WORKDIR  /build/x265
RUN cmake source && \
        make && \
        make install


FROM base-builder AS ffmpeg-builder
ENV FFMPEG_VERSION=7.0.2

WORKDIR /build/ffmpeg_sources
RUN wget https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.gz && \
        tar xvzf ffmpeg-${FFMPEG_VERSION}.tar.gz

WORKDIR /build/ffmpeg_sources/ffmpeg-${FFMPEG_VERSION}
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
        ldconfig


FROM base-builder AS srt-vtt-builder
WORKDIR /build/ffmpeg_sources
RUN git clone --depth=1 https://github.com/nwoltman/srt-to-vtt-cl.git
WORKDIR /build/ffmpeg_sources/srt-to-vtt-cl
RUN make && \
        find -name 'srt-vtt' | \
            grep -i linux | \
            head -n 1 | \
            xargs -I{} cp {} /usr/local/bin/srt-vtt


FROM ${BASE_IMAGE} AS base
ARG UID=1000
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_DIR=/mc
ENV VIRTUAL_ENV=${UV_PROJECT_DIR}/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /code
RUN groupadd -g ${UID} -r user && \
        useradd -r -u ${UID} -g user user && \
        chown -R user:user /code

RUN sed -i -e's/ main/ main contrib non-free non-free-firmware/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
        libavcodec-dev \
        libvorbis-dev \
        libx264-dev \
        libx265-dev \
        libnuma-dev \
        libvpx-dev \
        libass-dev \
        libfdk-aac-dev \
        libmp3lame-dev \
        libopus-dev \
        libtheora-dev \
        unrar && \
        pip install --upgrade --no-cache-dir pip uv && \
        uv venv --seed ${VIRTUAL_ENV}

WORKDIR /code
COPY uv.lock pyproject.toml ${UV_PROJECT_DIR}

RUN uv sync --no-dev --project ${VIRTUAL_ENV}

RUN ldconfig
WORKDIR /code

COPY --from=srt-vtt-builder /usr/local/bin/srt-vtt /usr/local/bin/srt-vtt
COPY --from=x265-builder /usr/local/lib/libx265* /usr/local/lib/
COPY --from=ffmpeg-builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg


# ********************* Begin Prod Image ******************
FROM base AS prod
USER user
COPY . /code

CMD ["celery", "-A", "main", "worker", "--loglevel=info", "--concurrency=1"]



# ********************* Begin Dev Image ******************
FROM base AS dev-root

RUN apt-get install -y g++

COPY pdbrc.py /root/.pdbrc.py

RUN uv sync --project "${VIRTUAL_ENV}"

FROM dev-root AS dev
USER user
