#!/bin/bash

sudo aptitude install -y yasm \
                         cmake \
                         cmake-curses-gui \
                         libvorbis-dev \
                         libx264-dev \
                         libx265-dev \
                         libvpx-dev \
                         libass-dev \
                         libfdk-aac-dev \
                         libmp3lame-dev \
                         libopus-dev \
                         libtheora-dev

cd /tmp
hg clone https://bitbucket.org/multicoreware/x265
cd x265/build/linux
./make-Makefiles.bash
make
sudo make install

mkdir /tmp/ffmpeg_sources
cd /tmp/ffmpeg_sources
wget http://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2
tar xjvf ffmpeg-snapshot.tar.bz2
cd ffmpeg

PKG_CONFIG_PATH="/usr/bin/pkg-config" ./configure \
  --prefix="/tmp/ffmpeg_build" \
  --pkg-config-flags="--static" \
  --extra-cflags="-I/tmp/ffmpeg_build/include" \
  --extra-ldflags="-L/tmp/ffmpeg_build/lib" \
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
  --enable-nonfree
make
sudo make install

rm -rf /tmp/x265 /tmp/ffmpeg_sources /tmp/ffmpeg_build