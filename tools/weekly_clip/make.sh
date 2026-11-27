#!/bin/bash
# Makes this week's social clip from an issue, square (1080) and story (1080x1920), as MP4s.
#   tools/weekly_clip/make.sh _posts/2026-11-25-issue-004.md <output folder> [music folder]
# Music: the MP3s in the music folder take turns by issue number (issue 4 of 3 tracks = track 2, and so on).
# Without a music folder the clips are silent. Needs python3 + PyYAML, node + playwright, ffmpeg.
set -euo pipefail
post=$1; out=$2; music=${3:-}
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../.." && pwd)
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
cp "$here/stage.html" "$work/"; cp "$root/assets/lib/d3-7.9.0.min.js" "$work/d3.min.js"
(cd "$root" && printf 'window.DATA=' && python3 tools/weekly_clip/data.py "$post") > "$work/data.js"
issue=$(cd "$root" && python3 -c "import json,sys;print(json.loads(open('$work/data.js').read()[12:])['issue'])")
mkdir -p "$out"
track=""
if [ -n "$music" ] && ls "$music"/*.mp3 >/dev/null 2>&1; then
  mapfile -t tracks < <(ls "$music"/*.mp3 | sort); track=${tracks[$(( (issue - 1) % ${#tracks[@]} ))]}
fi
for mode in square tall; do
  name=$([ $mode = square ] && echo square-1080 || echo story-1080x1920)
  dest="$out/chai-weekly-no-$issue-$name.mp4"
  (cd "$root" && node "$here/render.js" "$work" $mode "$work/f-$mode")
  ffmpeg -v error -y -framerate 30 -i "$work/f-$mode/f%04d.png" -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart "$work/silent-$mode.mp4"
  if [ -n "$track" ]; then
    d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$work/silent-$mode.mp4"); fo=$(python3 -c "print($d-3)")
    ffmpeg -v error -y -i "$work/silent-$mode.mp4" -i "$track" -filter_complex \
      "[1:a]silenceremove=start_periods=1:start_threshold=-35dB,atrim=0:$d,asetpts=N/SR/TB,afade=t=in:d=0.3,afade=t=out:st=$fo:d=3,loudnorm=I=-16:TP=-1.5:LRA=11[a]" \
      -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest "$dest"
  else
    cp "$work/silent-$mode.mp4" "$dest"
  fi
  echo "Saved $dest${track:+ (music: $(basename "$track"))}"
done
