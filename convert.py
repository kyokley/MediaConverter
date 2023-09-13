import shutil
import shlex
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


class AlreadyEncoded(Exception):
    """Raised when attempting to encoded a file previously encoded."""


class SkipProcessing(Exception):
    """Raised to stop processing a file."""


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


def _extractSubtitles(source, dest, stream_identifier):
    srt_path = dest.with_suffix(".srt")

    _extractSubtitleFromVideo(
        source,
        stream_identifier,
        srt_path,
    )

    _convertSrtToVtt(srt_path)
    try:
        srt_path.unlink()
    except FileNotFoundError:
        pass


def _extractSubtitleFromVideo(
    source,
    stream_identifier,
    srt_path,
):
    command = [
        ENCODER,
        "-hide_banner",
        "-y",
        "-i",
        str(source),
    ]
    subtitle_command = command + ["-map", stream_identifier, str(srt_path)]
    log.info("Extracting using following command:")
    log.info(" ".join(subtitle_command))
    process = Popen(subtitle_command, stdin=PIPE, stdout=PIPE, stderr=PIPE)  # nosec
    out, err = process.communicate()
    if process.returncode != 0:
        log.error(err)
        try:
            srt_path.unlink()
        except (OSError, FileNotFoundError) as e:
            log.warning(e)
        raise EncoderException(err)


def _convertSrtToVtt(srt_path):
    vtt_path = srt_path.with_suffix(".vtt")

    srt_vtt_command = ["srt-vtt", str(srt_path)]
    log.info("Extracting using following command:")
    log.info(" ".join(srt_vtt_command))
    process = Popen(srt_vtt_command, stdin=PIPE, stdout=PIPE, stderr=PIPE)  # nosec
    out, err = process.communicate()
    if process.returncode != 0:
        log.error(err)
        try:
            vtt_path.unlink()
        except (OSError, FileNotFoundError) as e:
            log.warning(e)
        raise EncoderException(err)
    return vtt_path


def encode(source, dest, dryRun=False):
    vres, ares, sres, surround = checkVideoEncoding(source)

    _handleSubtitles(source, dest, sres)
    _reencodeVideo(source, dest, vres, ares, surround, dryRun=dryRun)


def _handleSubtitles(source, dest, sres):
    dirname = Path(source).parent
    english_subtitle_paths = dirname.glob("*[eE][nN][gG]*.srt")

    file_srt_paths = dirname.glob("*.srt")

    count = 0

    for srt_path in english_subtitle_paths:
        log.info(f"{srt_path.name} found in directory. Attempting to convert.")
        dest_path = dirname / f"{dest.name}.{MEDIAVIEWER_SUFFIX}-{count}.vtt"
        vtt_path = _convertSrtToVtt(srt_path)
        _moveSubtitleFile(vtt_path, dest_path)

        count += 1

    for file_srt_path in file_srt_paths:
        log.info(f"{file_srt_path} found in directory. Looking for {source.stem}")
        if source.stem in str(file_srt_path):
            log.info(f"{file_srt_path} found in directory. Attempting to convert.")
            dest_path = dirname / f"{dest.name}.{MEDIAVIEWER_SUFFIX}-{count}.vtt"
            vtt_path = _convertSrtToVtt(file_srt_path)
            _moveSubtitleFile(vtt_path, dest_path)
            count += 1

    if sres:
        log.info("Found subtitles stream. Attempting to extract")
        sres = sres.groups()
        stream_identifier = f"{sres[0]}:{sres[1]}"
        dest_path = dirname / f"{dest.name}.{MEDIAVIEWER_SUFFIX}-{count}.vtt"
        _extractSubtitles(
            source,
            dest_path,
            stream_identifier,
        )


def _reencodeVideo(source, dest, vres, ares, surround, dryRun=False):
    command = [
        ENCODER,
        "-hide_banner",
        "-y",
        "-i",
        str(source),
    ]

    if vres and (ares and not surround):
        command.extend(
            [
                "-c",
                "copy",
            ]
        )
    elif vres:
        command.extend(
            [
                "-c:v",
                "copy",
                "-c:a",
                "libfdk_aac",
            ]
        )

        if surround:
            command.extend(["-ac", "2"])
    elif ares:
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

    command.extend(["-pix_fmt", "yuv420p", "-movflags", "faststart"])
    command.append(str(dest))
    command = tuple(command)

    log.info(command)
    if not dryRun:
        process = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)  # nosec
        process.communicate()

        if process.returncode != 0:
            if dest.exists():
                dest.unlink()
            raise EncoderException("Encoding failed")


def _moveSubtitleFile(source, dest, dryRun=False):
    srt_path = source.with_suffix(".srt")
    source_vtt_path = source.with_suffix(".vtt")
    dest_vtt_path = dest.with_suffix(".vtt")
    if source_vtt_path.exists():
        log.info("Found associated subtitle")
        if not dryRun:
            try:
                log.info(f"Moving subtitle from {source_vtt_path} to {dest_vtt_path}")
                shutil.move(source_vtt_path, dest_vtt_path)
            except Exception as e:
                log.error(e)
                raise

            try:
                log.info(f"Removing old srt file {srt_path}")
                srt_path.unlink()
            except (OSError, FileNotFoundError) as e:
                log.warning(e)
    else:
        log.warning(f"File not found: {source_vtt_path}")


def overwriteExistingFile(
    source, dest, removeOriginal=True, dryRun=False, appendSuffix=True
):
    if not dryRun:
        if removeOriginal and dest.exists():
            dest.unlink()

    dest = appendSuffix and Path(f"{dest}.{MEDIAVIEWER_SUFFIX}") or dest

    log.info(f"Renaming file {source} to {dest}")
    if not dryRun:
        try:
            shutil.move(source, dest)
        except Exception as e:
            log.error(e)
            raise
    else:
        log.info("Skipping move execution for dry-run")

    log.info("Finished renaming file")
    return dest


def makeFileStreamable(filename, dryRun=False, appendSuffix=True, removeOriginal=True):
    if MEDIAVIEWER_SUFFIX in str(filename):
        raise AlreadyEncoded("File appears to already have been encoded.")

    orig = Path(filename).resolve()

    if not is_valid_media_file(filename) or not orig.exists():
        raise SkipProcessing(f"{filename} is not a valid media file.")

    new = Path("/tmp") / orig.with_suffix('.mp4').name

    log.info(f"Begin re-encoding of {orig}...")
    encode(orig, new, dryRun=dryRun)
    log.info("Finished encoding")

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
            except (AlreadyEncoded, SkipProcessing) as e:
                log.warning(e)
    return errors
