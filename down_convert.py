import os
import argparse
import shutil
from subprocess import Popen, PIPE

ENCODER = 'ffmpeg' # or 'avconv'

class FileNotFound(Exception):
    pass

class EncoderException(Exception):
    pass

def recompress(filename):
    if not os.path.exists(filename):
        raise FileNotFound('{} does not exist'.format(filename))

    path = os.path.dirname(filename) or os.getcwd()
    base = os.path.basename(filename)
    bak_filename = os.path.join(path, '{}_bak'.format(base))
    tmp_filename = os.path.join(path, '{}.tmp'.format(base))

    command = (ENCODER,
               '-hide_banner',
               '-i',
               filename,
               '-crf',
               '30',
               '-c:a',
               'copy',
               '-preset',
               'slow',
               tmp_filename)

    # Run the command to recompress the file
    print('Starting to recompress {}'.format(filename))
    process = Popen(command, stdout=PIPE, stderr=PIPE)
    out, err = process.communicate()
    if process.returncode != 0:
        print(err)
        try:
            os.remove(tmp_filename)
        except OSError as e:
            print(e)
        raise EncoderException(err)
    print('Finished recompressing {}'.format(filename))

    # Move the original file to the backup location
    print('Moving {} to {}'.format(filename, bak_filename))
    shutil.move(filename, bak_filename)
    print('Done moving {} to {}'.format(filename, bak_filename))

    # Move the newly created file to the original file location
    print('Moving {} to {}'.format(tmp_filename, filename))
    shutil.move(tmp_filename, filename)
    print('Done moving {} to {}'.format(tmp_filename, filename))

def recompress_multiple(filename):
    if not os.path.exists(filename):
        raise FileNotFound('{} does not exist'.format(filename))

    files = []
    with open(filename, 'r') as inputted_file:
        for line in inputted_file:
            files.append(line.strip())

    for file in files:
        recompress(file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', help='File to be down-compressed to a smaller size')
    parser.add_argument('-f', '--file', help='Obtain files for decompression from the given file. One per line.')

    args = parser.parse_args()

    if not args.file and not args.infile:
        raise Exception('Either file or infile must be provided')
    elif args.file and args.infile:
        raise Exception('Only file or infile is allowed to be defined. Not both.')
    elif args.infile:
        recompress(args.infile)
    elif args.file:
        recompress_multiple(args.file)
    else:
        raise Exception('Invalid Input')

if __name__ == '__main__':
    main()
