from subprocess import Popen, PIPE
import os, shutil, commands
from re import search
from settings import (MEDIAVIEWER_SUFFIX,
                      LOCAL_MOVIE_PATH,
                      ENCODER,
                      MEDIA_FILE_EXTENSIONS,
                      )
from utils import stripUnicode, EncoderException

from log import LogFile
log = LogFile().getLogger()

def checkVideoEncoding(source):
    ffmpeg = Popen((ENCODER, "-i", source), stderr=PIPE)
    output = ffmpeg.communicate()[1]
    vmatch = search("Video.*h264", output)
    amatch = search("Audio.*(mp3|aac)", output)
    return (vmatch and 1 or 0, amatch and 1 or 0)

def fixMetaData(source, dryRun=False):
    if not dryRun:
        process = Popen(("qtfaststart", source), stdin=PIPE, stdout=PIPE, stderr=PIPE)
        process.communicate()

def encode(source, dest, dryRun=False):
    vres, ares = checkVideoEncoding(source)

    command = [ENCODER,
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

    if not dryRun:
        shutil.move(source, dest)
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

    log.info("Renaming file %s to %s" % (new, orig))
    dest = overwriteExistingFile(new, orig, dryRun=dryRun, appendSuffix=appendSuffix, removeOriginal=removeOriginal)
    log.info("Finished renaming file")

    log.info("Done")
    return dest

def reencodeFilesInDirectory(dir, dryRun=False):
    errors = list()
    fullPath = os.path.join(LOCAL_MOVIE_PATH, dir)
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
