Burn in subtitles from bitmap subtitle source (hdmv_pgs_subtitle)
```
for file in *
do
ffmpeg -analyzeduration 500000000 -probesize 500000000 -i ${file} -filter_complex "[0:v][0:s]overlay[v]" -map "[v]" -map 0:a  ${file}.sub.mkv
done
```

Burn in subtitles from vtt subtitle source
```
for file in *.mp4
do
ffmpeg -y -i ${file}-0.vtt ${file}-0.ass
ffmpeg -y -i ${file} -vf ass=${file}-0.ass out.mp4
mv -fv out.mp4 ${file}
done
rm *.vtt *.ass
```
