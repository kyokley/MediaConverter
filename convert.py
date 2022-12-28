import os
import shutil
import shlex
import sys
from pathlib import Path
from re import search
from settings import (
    MEDIAVIEWER_SUFFIX,
    ENCODER,
)
from utils import (
    stripUnicode,
    EncoderException,
    is_valid_media_file,
)
from subprocess import Popen, PIPE

import logging

log = logging.getLogger(__name__)


LARGE_FILE_SIZE = int(1024 * 1024 * 1024 * 1.25)  # 2 GB


class AlreadyEncoded(Exception):
    """Raised when attempting to encoded a file previously encoded."""


def checkVideoEncoding(source):
    ffmpeg = Popen((ENCODER, "-hide_banner", "-i", source), stderr=PIPE)  # nosec
    output = ffmpeg.communicate()[1].decode("utf-8")

    # Can't check returncode here since we always get back 1
    if "At least one output file must be specified" != output.split("\n")[-2]:
        log.error(output)
        raise EncoderException(output)

    vmatch = search(r"Video.*h264", output)
    amatch = search(r"Audio.*aac", output)
    smatch = search(r"(\d+).(\d+)\(eng.*Subtitle", output)
    surround = search(r"Audio.*5\.1", output)
    return (vmatch and 1 or 0, amatch and 1 or 0, smatch, surround)


def fixMetaData(source, dryRun=False):
    if not dryRun:
        process = Popen(
            ("qtfaststart", source), stdin=PIPE, stdout=PIPE, stderr=PIPE
        )  # nosec
        process.communicate()


def _extractSubtitles(source, dest, stream_identifier):
    srt_filename = f"{os.path.splitext(dest)[0]}.srt"

    _extractSubtitleFromVideo(
        source,
        stream_identifier,
        srt_filename,
    )

    _convertSrtToVtt(srt_filename)


def _extractSubtitleFromVideo(
    source,
    stream_identifier,
    srt_filename,
):
    command = [
        ENCODER,
        "-hide_banner",
        "-y",
        "-i",
        source,
    ]
    subtitle_command = command + ["-map", stream_identifier, srt_filename]
    log.info("Extracting using following command:")
    log.info(" ".join(subtitle_command))
    process = Popen(subtitle_command, stdin=PIPE, stdout=PIPE, stderr=PIPE)  # nosec
    out, err = process.communicate()
    if process.returncode != 0:
        log.error(err)
        try:
            os.remove(srt_filename)
        except OSError as e:
            log.warning(e)
        raise EncoderException(err)


def _convertSrtToVtt(srt_filename):
    vtt_filename = f"{os.path.splitext(srt_filename)[0]}.vtt"
    srt_vtt_command = ["srt-vtt", srt_filename]
    log.info("Extracting using following command:")
    log.info(" ".join(srt_vtt_command))
    process = Popen(srt_vtt_command, stdin=PIPE, stdout=PIPE, stderr=PIPE)  # nosec
    out, err = process.communicate()
    if process.returncode != 0:
        log.error(err)
        try:
            os.remove(vtt_filename)
        except OSError as e:
            log.warning(e)
        raise EncoderException(err)
    return vtt_filename


def encode(source, dest, dryRun=False):
    vres, ares, sres, surround = checkVideoEncoding(source)

    _handleSubtitles(source, dest, sres)
    _reencodeVideo(source, dest, vres, ares, surround, dryRun=dryRun)


def _handleSubtitles(source, dest, sres):
    dirname = Path(source).parent
    english_subtitle_paths = dirname.glob("*Eng*.srt")

    file_srt_path = Path(source).with_suffix(".srt")

    for idx, srt_path in enumerate(english_subtitle_paths):
        log.info(
            f"{srt_path.name} found in directory. Attempting to convert."
        )
        dest_path = Path(f"{dest}-{idx}.vtt")
        vtt_filename = _convertSrtToVtt(srt_path)
        _moveSubtitleFile(vtt_filename, dest_path)

    if file_srt_path.exists():
        log.info(f"{file_srt_path} found in directory. Attempting to convert.")
        dest_path = Path(dest).with_suffix(".vtt")
        vtt_filename = _convertSrtToVtt(file_srt_path)
        _moveSubtitleFile(vtt_filename, dest_path)
    elif sres:
        log.info("Found subtitles stream. Attempting to extract")
        sres = sres.groups()
        stream_identifier = f"{sres[0]}:{sres[1]}"
        _extractSubtitles(
            source,
            dest,
            stream_identifier,
        )


def _reencodeVideo(source, dest, vres, ares, surround, dryRun=False):
    file_size = os.path.getsize(source)

    command = [
        ENCODER,
        "-hide_banner",
        "-y",
        "-i",
        source,
    ]

    if vres and (ares and not surround):
        if file_size > LARGE_FILE_SIZE:
            command.extend(
                [
                    "-crf",
                    "30",
                    "-preset",
                    "slow",
                ]
            )
        else:
            command.extend(
                [
                    "-c",
                    "copy",
                ]
            )
    elif vres:
        if file_size > LARGE_FILE_SIZE:
            command.extend(
                [
                    "-crf",
                    "30",
                    "-preset",
                    "slow",
                ]
            )
        else:
            command.extend(
                [
                    "-c:v",
                    "copy",
                ]
            )

        command.extend(
            [
                "-c:a",
                "libfdk_aac",
            ]
        )

        if surround:
            command.extend(["-ac", "2"])
    elif ares:
        if file_size > LARGE_FILE_SIZE:
            command.extend(
                [
                    "-crf",
                    "30",
                    "-preset",
                    "slow",
                ]
            )

        command.extend(
            [
                "-c:v",
                "libx264",
            ]
        )

        if surround:
            command.extend(["-c:a", "libfdk_aac", "-ac", "2"])
        else:
            command.extend(
                [
                    "-c:a",
                    "copy",
                ]
            )
    else:
        if file_size > LARGE_FILE_SIZE:
            command.extend(
                [
                    "-crf",
                    "30",
                    "-preset",
                    "slow",
                ]
            )

        command.extend(
            [
                "-c:v",
                "libx264",
                "-c:a",
                "libfdk_aac",
            ]
        )

        if surround:
            command.extend(["-ac", "2"])

    command.append(dest)
    command = tuple(command)

    log.info(command)
    if not dryRun:
        process = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)  # nosec
        process.communicate()

        if process.returncode != 0:
            if os.path.exists(dest):
                os.remove(dest)
            raise EncoderException("Encoding failed")


def _moveSubtitleFile(source, dest, dryRun=False):
    srt_filename = f"{os.path.splitext(source)[0]}.srt"
    source_vtt_filename = f"{os.path.splitext(source)[0]}.vtt"
    dest_vtt_filename = f"{os.path.splitext(dest)[0]}.vtt"
    if os.path.exists(source_vtt_filename):
        log.info("Found associated subtitle")
        if not dryRun:
            try:
                log.info(
                    f"Moving subtitle from {source_vtt_filename} to {dest_vtt_filename}"
                )
                shutil.move(source_vtt_filename, dest_vtt_filename)
            except Exception as e:
                log.error(e)
                raise

            try:
                log.info(f"Removing old srt file {srt_filename}")
                os.remove(srt_filename)
            except OSError as e:
                log.warning(e)
    else:
        log.warning(f"File not found: {source_vtt_filename}")


def overwriteExistingFile(
    source, dest, removeOriginal=True, dryRun=False, appendSuffix=True
):
    if not dryRun:
        if removeOriginal and os.path.exists(dest):
            os.remove(dest)

    dest = appendSuffix and f"{dest}.{MEDIAVIEWER_SUFFIX}" or dest

    log.info(f"Renaming file {source} to {dest}")
    if not dryRun:
        try:
            shutil.move(source, dest)
        except Exception as e:
            log.error(e)
            raise
    else:
        log.info("Skipping move execution for dry-run")

    _moveSubtitleFile(source, dest, dryRun=dryRun)
    log.info("Finished renaming file")
    return dest


def makeFileStreamable(filename, dryRun=False, appendSuffix=True, removeOriginal=True):
    if MEDIAVIEWER_SUFFIX in filename:
        raise AlreadyEncoded("File appears to already have been encoded. FAIL")

    orig = os.path.realpath(filename)
    new = "tmpfile.mp4"

    log.info(f"Begin re-encoding of {orig}...")
    encode(orig, new, dryRun=dryRun)
    log.info("Finished encoding")

    log.info("Fixing metadata")
    fixMetaData(new, dryRun=dryRun)
    log.info("Finished fixing metadata")

    dest = overwriteExistingFile(
        new,
        orig,
        dryRun=dryRun,
        appendSuffix=appendSuffix,
        removeOriginal=removeOriginal,
    )

    log.info("Done")
    return dest


def _getFilesInDirectory(fullPath):
    command = f"find '{fullPath}' -maxdepth 10 -not -type d"
    p = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)  # nosec
    res = p.communicate()[0]
    tokens = res.split(b"\n")
    return set([x for x in tokens if x])


def reencodeFilesInDirectory(fullPath, dryRun=False):
    errors = list()
    cleanedFullPath = stripUnicode(fullPath)
    tokens = _getFilesInDirectory(cleanedFullPath)

    for token in tokens:
        if is_valid_media_file(token):
            try:
                cleanPath = stripUnicode(token)
                makeFileStreamable(
                    cleanPath, appendSuffix=True, removeOriginal=True, dryRun=dryRun
                )
            except EncoderException as e:
                log.error(e)
                errors.append(cleanPath)
    return errors


if __name__ == "__main__":
    encode(*sys.argv[1:])
