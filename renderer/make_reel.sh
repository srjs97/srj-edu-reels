#!/bin/bash
# usage: make_reel.sh spec.json out.mp4   (output < 9.5 MB, 1080x1920, 60s)
set -e
OUT=$(realpath "$2"); D=$(cd "$(dirname "$0")" && pwd); T=$(mktemp -d)
if grep -q '"style": *"explainer"' "$1"; then R=explainer.py; else R=video.py; fi
python3 "$D/$R" "$1" "$T/silent.mp4" "$T/cues.json"
python3 "$D/audio.py" "$T/cues.json" "$T/mix.wav"
cd "$T"
ffmpeg -y -loglevel error -i silent.mp4 -c:v libx264 -b:v 1150k -pass 1 -preset slow -an -f mp4 /dev/null
ffmpeg -y -loglevel error -i silent.mp4 -i mix.wav -c:v libx264 -b:v 1150k -pass 2 -preset slow -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart -shortest "$OUT"
