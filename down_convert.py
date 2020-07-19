import argparse
import os
import shutil
from datetime import datetime
from subprocess import PIPE, Popen

ENCODER = "ffmpeg"  # or 'avconv'


class FileNotFound(Exception):
    pass


class EncoderException(Exception):
    pass


def recompress(filename, scale_down=False):
    if not os.path.exists(filename):
        raise FileNotFound("{} does not exist".format(filename))

    path = os.path.dirname(filename) or os.getcwd()
    base = os.path.basename(filename)
    bak_filename = os.path.join(path, "{}_bak".format(base))
    tmp_filename = os.path.join(path, "tmp-{}".format(base))

    command = [
        ENCODER,
        "-hide_banner",
        "-i",
        filename,
    ]

    if scale_down:
        command.extend(["-vf", "scale=-2:720:flags=lanczos"])

    command.extend(
        [
            "-movflags",
            "+faststart",
            "-crf",
            "30",
            "-acodec",
            "libfdk_aac",
            "-preset",
            "slow",
            tmp_filename,
        ]
    )

    # Run the command to recompress the file
    print("Starting to recompress {} at {}".format(filename, datetime.now()))
    process = Popen(command, stdout=PIPE, stderr=PIPE)
    out, err = process.communicate()
    if process.returncode != 0:
        print(err)
        try:
            os.remove(tmp_filename)
        except OSError as e:
            print(e)
        raise EncoderException(err)
    print("Finished recompressing {}".format(filename))

    # Move the original file to the backup location
    print("Moving {} to {}".format(filename, bak_filename))
    shutil.move(filename, bak_filename)
    print("Done moving {} to {}".format(filename, bak_filename))

    # Move the newly created file to the original file location
    print("Moving {} to {}".format(tmp_filename, filename))
    shutil.move(tmp_filename, filename)
    print("Done moving {} to {}".format(tmp_filename, filename))


def recompress_multiple(filename, scale_down=False):
    if not os.path.exists(filename):
        raise FileNotFound("{} does not exist".format(filename))

    files = []
    with open(filename, "r") as inputted_file:
        for line in inputted_file:
            files.append(line.strip())

    for file in files:
        recompress(file, scale_down=scale_down)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input", help="File to be down-compressed to a smaller size"
    )
    parser.add_argument(
        "-s",
        "--sources",
        help="Obtain files for decompression from the given file. One per line.",
    )
    parser.add_argument(
        "-d",
        "--scale_down",
        help="Scale down a natively 1080p file to 720p",
        action="store_true",
    )

    args = parser.parse_args()

    if not args.sources and not args.input:
        raise Exception("Either sources or input must be provided")
    elif args.sources and args.input:
        raise Exception("Only sources or input is allowed to be defined. Not both.")
    elif args.input:
        recompress(args.input, scale_down=args.scale_down)
    elif args.sources:
        recompress_multiple(args.sources, scale_down=args.scale_down)
    else:
        raise Exception("Invalid Input")


if __name__ == "__main__":
    main()
