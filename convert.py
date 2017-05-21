import traceback
from subprocess import Popen, PIPE
import os, shutil
import shlex
from re import search
from settings import (MEDIAVIEWER_SUFFIX,
                      ENCODER,
                      MEDIA_FILE_EXTENSIONS,
                      SEND_EMAIL,
                      )
from utils import stripUnicode, EncoderException
from celery_handler import app

from log import LogFile
log = LogFile().getLogger()

def checkVideoEncoding(source, dryRun=False):
    if dryRun:
        log.info('Skipping checkVideoEncoding for dryRun')
        return 1, 1, 1

    ffmpeg = Popen((ENCODER, '-hide_banner', "-i", source), stderr=PIPE)
    output = ffmpeg.communicate()[1]

    # Can't check returncode here since we always get back 1
    if 'At least one output file must be specified' != output.split('\n')[-2]:
        log.error(output)
        raise EncoderException(output)

    vmatch = search("Video.*h264", output)
    amatch = search("Audio.*aac", output)
    smatch = search("(\d+).(\d+)\(eng.*Subtitle", output)
    return (vmatch and 1 or 0, amatch and 1 or 0, smatch)

def fixMetaData(source, dryRun=False):
    if not dryRun:
        process = Popen(("qtfaststart", source), stdin=PIPE, stdout=PIPE, stderr=PIPE)
        process.communicate()

def _extractSubtitles(source, dest, stream_identifier):
    srt_filename = '{}.srt'.format(os.path.splitext(dest)[0])

    _extractSubtitleFromVideo(source,
                              dest,
                              stream_identifier,
                              srt_filename,
                              )

    _convertSrtToVtt(srt_filename)

def _extractSubtitleFromVideo(source,
                              dest,
                              stream_identifier,
                              srt_filename,
                              ):
    subtitle_command = (ENCODER,
                        "-hide_banner",
                        "-y",
                        "-i",
                        source,
                        '-map',
                        stream_identifier,
                        srt_filename)
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

def _convertSrtToVtt(srt_filename):
    vtt_filename = '{}.vtt'.format(os.path.splitext(srt_filename)[0])
    srt_vtt_command = ('srt-vtt',
                       srt_filename)
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
    return vtt_filename

def encode(source, dest, dryRun=False):
    vres, ares, sres = checkVideoEncoding(source, dryRun=dryRun)

    _handleSubtitles(source, dest, sres, dryRun=dryRun)
    _reencodeVideo(source, dest, vres, ares, dryRun=dryRun)

def _handleSubtitles(source, dest, sres, dryRun=False):
    if dryRun:
        log.info('Skipping _handleSubtitles for dryRun')
        return

    dirname = os.path.dirname(source)
    english_srt_path = os.path.join(dirname, 'English.srt')
    file_srt_path = os.path.splitext(source)[0] + '.srt'
    if os.path.exists(english_srt_path):
        log.info('English.srt found in directory. Attempting to convert.')
        dest_path = '{}.vtt'.format(os.path.splitext(dest)[0])
        vtt_filename = _convertSrtToVtt(english_srt_path)
        _moveSubtitleFile(vtt_filename,
                          dest_path)
    elif os.path.exists(file_srt_path):
        log.info('{} found in directory. Attempting to convert.'.format(file_srt_path))
        dest_path = '{}.vtt'.format(os.path.splitext(dest)[0])
        vtt_filename = _convertSrtToVtt(file_srt_path)
        _moveSubtitleFile(vtt_filename,
                          dest_path)
    elif sres:
        log.info('Found subtitles stream. Attempting to extract')
        sres = sres.groups()
        stream_identifier = '{}:{}'.format(sres[0], sres[1])
        _extractSubtitles(source,
                          dest,
                          stream_identifier,
                          )

def _reencodeVideo(source, dest, vres, ares, dryRun=False):
    command = [ENCODER,
               "-hide_banner",
               "-y",
               "-i",
               source,
               ]

    if vres and ares:
        command.extend(["-c",
                        "copy",
                        ])
    elif vres:
        command.extend(["-c:v",
                        "copy",
                        "-c:a",
                        "libfdk_aac",
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
                        "libfdk_aac",
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

def _moveSubtitleFile(source, dest, dryRun=False):
    srt_filename = '{}.srt'.format(os.path.splitext(source)[0])
    source_vtt_filename = '{}.vtt'.format(os.path.splitext(source)[0])
    dest_vtt_filename = '{}.vtt'.format(os.path.splitext(dest)[0])
    if os.path.exists(source_vtt_filename):
        log.info('Found associated subtitle')
        if not dryRun:
            try:
                log.info('Moving subtitle from {} to {}'.format(source_vtt_filename, dest_vtt_filename))
                shutil.move(source_vtt_filename, dest_vtt_filename)
            except Exception, e:
                log.error(e)
                raise

            try:
                log.info('Removing old srt file {}'.format(srt_filename))
                os.remove(srt_filename)
            except OSError, e:
                log.warn(e)
    else:
        log.warn('File not found: {}'.format(source_vtt_filename))

def overwriteExistingFile(source,
                          dest,
                          removeOriginal=True,
                          dryRun=False,
                          appendSuffix=True):
    if not dryRun:
        if removeOriginal and os.path.exists(dest):
            os.remove(dest)

    dest = appendSuffix and MEDIAVIEWER_SUFFIX.format(dest) or dest

    log.info("Renaming file {} to {}".format(source, dest))
    if not dryRun:
        try:
            shutil.move(source, dest)
        except Exception, e:
            log.error(e)
            raise
    else:
        log.info('Skipping move execution for dry-run')

    _moveSubtitleFile(source, dest, dryRun=dryRun)
    log.info("Finished renaming file")
    return dest

@app.task
def makeFileStreamable(filename, pathid, dryRun=False, appendSuffix=True, removeOriginal=True):
    try:
        orig = os.path.realpath(filename)
        new = 'tmp-{}'.format(os.path.basename(filename))

        log.info("Begin re-encoding of {}...".format(orig))
        encode(orig, new, dryRun=dryRun)
        log.info("Finished encoding")

        log.info("Fixing metadata")
        fixMetaData(new, dryRun=dryRun)
        log.info("Finished fixing metadata")

        dest = overwriteExistingFile(new, orig, dryRun=dryRun, appendSuffix=appendSuffix, removeOriginal=removeOriginal)

        log.info("Done")
        return dest, pathid
    except Exception, e:
        errorMsg = "Something bad happened attempting to make {} streamable".format(filename)
        log.error(errorMsg)
        log.error(e)

        if SEND_EMAIL:
            message = '''
            {}
            Got the following:
            {}
            '''.format(errorMsg, traceback.format_exc())
        else:
            message = errorMsg
        raise Exception(message)

def _getFilesInDirectory(fullPath):
    command = "find '{}' -maxdepth 10 -not -type d".format(fullPath)
    p = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
    res = p.communicate()[0]
    tokens = res.split('\n')
    return set([x for x in tokens if x])

def reencodeFilesInDirectory(fullPath, pathid, dryRun=False):
    tokens = _getFilesInDirectory(fullPath)
    tasks = []

    for token in tokens:
        ext = os.path.splitext(token)[-1].lower()
        if ext in MEDIA_FILE_EXTENSIONS:
            cleanPath = stripUnicode(token)
            tasks.append(makeFileStreamable.delay(cleanPath,
                                                  pathid,
                                                  appendSuffix=True,
                                                  removeOriginal=True,
                                                  dryRun=dryRun))
    return tasks
