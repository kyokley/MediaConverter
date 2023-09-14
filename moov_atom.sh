#!/bin/bash

# The purpose of this script is to find and fix files that are missing their
# MOOV metadata.

OIFS="$IFS"
IFS=$'\n'
for full_path in $(find . -name '*.mp4')
do
    file=$(basename "${full_path}")
    file=$(printf '%q' "$file")
    dir=$(dirname "${full_path}")

    if qtfaststart -l "${full_path}" >/dev/null 2>&1
    then
        # We found an atom so nothing to do
        continue
    else
        echo "${dir}:"
        echo "${file}(${full_path}): Missing atom"
        docker run --rm -t -v "$dir:/files" kyokley/mediaconverter /bin/bash -c "
        cd /files &&
            cp -v "${file}" "${file}_bak" &&
            ffmpeg -hide_banner -y -i "${file}_bak" -c copy -movflags faststart "${file}" &&
            rm -v "${file}_bak"
        "
        echo
    fi
done
IFS="$OIFS"
