Burn in subtitles from bitmap subtitle source (hdmv_pgs_subtitle)
```
for file in *
> do
> ffmpeg -analyzeduration 500000000 -probesize 500000000 -i ${file} -filter_complex "[0:v][0:s]overlay[v]" -map "[v]" -map 0:a  ${file}.sub.mkv
> done
```
