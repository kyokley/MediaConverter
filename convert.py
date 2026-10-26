import shutil
import shlex
import tempfile
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
    matching_subtitle_files,
)
from subprocess import Popen, PIPE, DEVNULL, TimeoutExpired

import logging
import time

log = logging.getLogger(__name__)

_PROGRESS_INTERVAL = 30
_STDERR_TAIL_BYTES = 8192


def _read_stderr_tail(stderr_file):
    stderr_file.seek(0, 2)
    size = stderr_file.tell()
    stderr_file.seek(max(0, size - _STDERR_TAIL_BYTES))
    return stderr_file.read().decode("utf-8", errors="replace").strip()


def _format_progress(values):
    fields = [
        f"{name}={values[name]}"
        for name in ("out_time", "speed", "frame")
        if values.get(name)
    ]
    return ", ".join(fields)


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
    log.info("Inspecting media source=%s destination=%s", source, dest)
    vres, ares, sres, surround = checkVideoEncoding(source)
    log.info(
        "Codec decision source=%s video=%s audio=%s downmix=%s",
        source,
        "copy" if vres else "encode",
        "copy" if ares and not surround else "encode",
        bool(surround),
    )

    log.info("Starting subtitle processing source=%s", source)
    _handleSubtitles(source, dest, sres)
    log.info("Finished subtitle processing source=%s", source)
    _reencodeVideo(source, dest, vres, ares, surround, dryRun=dryRun)


def _handleSubtitles(source, dest, sres):
    dirname = Path(source).parent
    count = 0

    def unused_destination():
        nonlocal count
        while True:
            dest_path = dirname / f"{dest.name}.{MEDIAVIEWER_SUFFIX}-{count}.vtt"
            count += 1
            if not dest_path.exists() and not dest_path.with_suffix(".srt").exists():
                return dest_path

    subtitle_paths = matching_subtitle_files(source)
    if Path(source).suffix.lower() == ".srt" and not any(
        item.is_file() and is_valid_media_file(item) for item in dirname.iterdir()
    ):
        subtitle_paths = sorted(dirname.glob("*.srt"))
    for subtitle_path in subtitle_paths:
        if subtitle_path.suffix.lower() == ".vtt":
            continue
        log.info(f"{subtitle_path.name} found in directory. Attempting to convert.")
        dest_path = unused_destination()
        with tempfile.NamedTemporaryFile(
            suffix=".srt", dir=dirname, prefix=".subtitle-", delete=False
        ) as temporary:
            temporary_srt = Path(temporary.name)
        try:
            shutil.copy2(subtitle_path, temporary_srt)
            vtt_path = _convertSrtToVtt(temporary_srt)
            _moveSubtitleFile(vtt_path, dest_path)
            if not dest_path.is_file():
                raise EncoderException(
                    f"Subtitle conversion did not create destination: {dest_path}"
                )
            try:
                subtitle_path.unlink()
            except OSError as error:
                log.warning(error)
        finally:
            temporary_srt.unlink(missing_ok=True)
            temporary_srt.with_suffix(".vtt").unlink(missing_ok=True)

    if sres:
        log.info("Found subtitles stream. Attempting to extract")
        sres = sres.groups()
        stream_identifier = f"{sres[0]}:{sres[1]}"
        dest_path = unused_destination()
        _extractSubtitles(
            source,
            dest_path,
            stream_identifier,
        )


def _reencodeVideo(source, dest, vres, ares, surround, dryRun=False):
    started = time.monotonic()
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
    command.extend(["-progress", "pipe:1", "-nostats"])
    command.append(str(dest))
    command = tuple(command)

    log.info("Starting FFmpeg source=%s destination=%s", source, dest)
    log.debug("FFmpeg command=%s", command)
    if dryRun:
        log.info(
            "Skipping FFmpeg execution for dry-run source=%s destination=%s",
            source,
            dest,
        )
        return

    progress = {}
    last_logged = started
    final_progress = ""
    returncode = None
    with tempfile.TemporaryFile(mode="w+b") as stderr_file:
        process = Popen(command, stdin=DEVNULL, stdout=PIPE, stderr=stderr_file)  # nosec
        try:
            for raw_line in process.stdout:
                if isinstance(raw_line, bytes):
                    line = raw_line.decode("utf-8", errors="replace").strip()
                else:
                    line = raw_line.strip()
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                progress[key] = value
                if key == "progress":
                    summary = _format_progress(progress)
                    if summary:
                        final_progress = summary
                        now = time.monotonic()
                        if value == "end" or now - last_logged >= _PROGRESS_INTERVAL:
                            log.info(
                                "FFmpeg progress source=%s destination=%s %s",
                                source,
                                dest,
                                summary,
                            )
                            last_logged = now
                    progress = {}
            returncode = process.wait()
        except BaseException:
            try:
                process.stdout.close()
            except BaseException:
                pass
            try:
                process.terminate()
            except BaseException:
                pass
            try:
                process.wait(timeout=5)
            except TimeoutExpired:
                try:
                    process.kill()
                except BaseException:
                    pass
                try:
                    process.wait()
                except BaseException:
                    pass
            except BaseException:
                pass
            raise
        finally:
            process.stdout.close()

        elapsed = time.monotonic() - started
        if returncode != 0:
            diagnostic = _read_stderr_tail(stderr_file)
            if dest.exists():
                dest.unlink()
            log.error(
                "FFmpeg failed source=%s destination=%s elapsed=%.1fs diagnostics=%s",
                source,
                dest,
                elapsed,
                diagnostic or "(no stderr output)",
            )
            raise EncoderException("Encoding failed")

    log.info(
        "FFmpeg completed source=%s destination=%s elapsed=%.1fs%s",
        source,
        dest,
        elapsed,
        f" progress={final_progress}" if final_progress else "",
    )


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


def overwriteExistingFile(source, directory, dryRun=False, appendSuffix=True):
    dest = directory / source.name
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
    started = time.monotonic()
    log.info(f"Begin processing {filename}")
    if MEDIAVIEWER_SUFFIX in str(filename):
        raise AlreadyEncoded(f"{filename} appears to already have been encoded.")

    orig = Path(filename).resolve()

    if not is_valid_media_file(filename) or not orig.exists():
        raise SkipProcessing(f"{filename} is not a valid media file.")

    with tempfile.TemporaryDirectory() as tmpdir:
        new = Path(tmpdir) / orig.with_suffix(".mp4").name

        log.info("Begin re-encoding source=%s destination=%s", orig, new)
        encode(orig, new, dryRun=dryRun)

        dest = overwriteExistingFile(
            new,
            orig.parent,
            dryRun=dryRun,
            appendSuffix=appendSuffix,
        )

    if not dryRun:
        if removeOriginal and orig.exists():
            orig.unlink()

    elapsed = time.monotonic() - started
    if dryRun:
        log.info(
            "Dry-run planned output source=%s destination=%s elapsed=%.1fs",
            orig,
            dest,
            elapsed,
        )
    else:
        output_size = dest.stat().st_size if dest.exists() else None
        log.info(
            "Processing completed source=%s destination=%s elapsed=%.1fs output_bytes=%s",
            orig,
            dest,
            elapsed,
            output_size if output_size is not None else "unknown",
        )
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
