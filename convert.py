from subprocess import Popen, PIPE
import os, shutil, commands
from re import search
from settings import (MEDIAVIEWER_SUFFIX,
                      ENCODER,
                      MEDIA_FILE_EXTENSIONS,
                      )
from utils import stripUnicode, EncoderException

from log import LogFile
log = LogFile().getLogger()

def checkVideoEncoding(source):
    ffmpeg = Popen((ENCODER, '-hide_banner', "-i", source), stderr=PIPE)
    output = ffmpeg.communicate()[1]

    # Can't check returncode here since we always get back 1
    if 'At least one output file must be specified' != output.split('\n')[-2]:
        log.error(output)
        raise EncoderException(output)

    vmatch = search("Video.*h264", output)
    amatch = search("Audio.*(mp3|aac)", output)
    smatch = search("(\d+).(\d+)\(eng.*Subtitle", output)
    return (vmatch and 1 or 0, amatch and 1 or 0, smatch)

def fixMetaData(source, dryRun=False):
    if not dryRun:
        process = Popen(("qtfaststart", source), stdin=PIPE, stdout=PIPE, stderr=PIPE)
        process.communicate()

def encode(source, dest, dryRun=False):
    vres, ares, sres = checkVideoEncoding(source)

    command = [ENCODER,
               "-hide_banner",
               "-y",
               "-i",
               source,
               ]

    if sres:
        log.info('Found subtitles stream. Attempting to extract')
        sres = sres.groups()
        srt_filename = '%s.srt' % os.path.splitext(dest)[0]
        vtt_filename = '%s.vtt' % os.path.splitext(dest)[0]
        subtitle_command = command + ['-map',
                                      '%s:%s' % (sres[0], sres[1]),
                                      srt_filename]
        log.debug('Extracting using following command:')
        log.debug(' '.join(subtitle_command))
        process = Popen(subtitle_command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        out, err = process.communicate()
        if process.returncode != 0:
            log.error(err)
            try:
                os.remove(srt_filename)
            except OSError, e:
                log.warn(e)
            raise EncoderException(err)

        srt_vtt_command = ['srt-vtt',
                           srt_filename]
        log.debug('Extracting using following command:')
        log.debug(' '.join(srt_vtt_command))
        process = Popen(srt_vtt_command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        out, err = process.communicate()
        if process.returncode != 0:
            log.error(err)
            try:
                os.remove(vtt_filename)
            except OSError, e:
                log.warn(e)
            raise EncoderException(err)

    if vres and ares:
        command.extend(["-c",
                        "copy",
                        ])
    elif vres:
        command.extend(["-c:v",
                        "copy",
                        "-c:a",
                        "libmp3lame",
                        ])
    elif ares:
        command.extend(["-c:v",
                        "libx264",
                        "-c:a",
                        "copy",
                        ])
    else:
        command.extend(["-c:v",
                        "libx264",
                        "-c:a",
                        "libmp3lame",
                        ])

    command.append(dest)
    command = tuple(command)

    log.info(command)
    if not dryRun:
        process = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        process.communicate()

        if process.returncode != 0:
            os.remove(dest)
            raise EncoderException('Encoding failed')

def overwriteExistingFile(source,
                          dest,
                          removeOriginal=True,
                          dryRun=False,
                          appendSuffix=True):
    if not dryRun:
        if removeOriginal:
            os.remove(dest)

    dest = appendSuffix and MEDIAVIEWER_SUFFIX % dest or dest

    log.info("Renaming file %s to %s" % (source, dest))
    if not dryRun:
        try:
            shutil.move(source, dest)
        except Exception, e:
            log.error(e)
            raise
    else:
        log.info('Skipping move execution for dry-run')

    srt_filename = '%s.srt' % os.path.splitext(source)[0]
    source_vtt_filename = '%s.vtt' % os.path.splitext(source)[0]
    dest_vtt_filename = '%s.vtt' % os.path.splitext(dest)[0]
    if os.path.exists(source_vtt_filename):
        log.info('Found associated subtitle')
        if not dryRun:
            try:
                log.info('Moving subtitle from %s to %s' % (source_vtt_filename, dest_vtt_filename))
                shutil.move(source_vtt_filename, dest_vtt_filename)
            except Exception, e:
                log.error(e)
                raise

            try:
                log.info('Removing old srt file %s' % srt_filename)
                os.remove(srt_filename)
            except OSError, e:
                log.warn(e)
    log.info("Finished renaming file")
    return dest

def makeFileStreamable(filename, dryRun=False, appendSuffix=True, removeOriginal=True):
    orig = os.path.realpath(filename)
    new = "tmpfile.mp4"

    log.info("Begin re-encoding of %s..." % orig)
    encode(orig, new, dryRun=dryRun)
    log.info("Finished encoding")

    log.info("Fixing metadata")
    fixMetaData(new, dryRun=dryRun)
    log.info("Finished fixing metadata")

    dest = overwriteExistingFile(new, orig, dryRun=dryRun, appendSuffix=appendSuffix, removeOriginal=removeOriginal)

    log.info("Done")
    return dest

def reencodeFilesInDirectory(fullPath, dryRun=False):
    errors = list()
    res = commands.getoutput("find '%s' -maxdepth 10 -not -type d" % fullPath)
    tokens = res.split('\n')

    for token in tokens:
        ext = os.path.splitext(token)[-1].lower()
        if ext in MEDIA_FILE_EXTENSIONS:
            try:
                cleanPath = stripUnicode(token)
                makeFileStreamable(cleanPath,
                                   appendSuffix=True,
                                   removeOriginal=True,
                                   dryRun=dryRun)
            except EncoderException, e:
                log.error(e)
                errors.append(cleanPath)
    return errors
