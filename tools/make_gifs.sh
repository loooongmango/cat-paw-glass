#!/usr/bin/env bash
# Re-record docs/demo.gif and docs/kneading.gif from index.html.
# Needs: node + playwright (with Chromium), python3 + Pillow, ffmpeg.
# usage: tools/make_gifs.sh            (run from the repo root)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 1. step the paused CSS animations frame by frame and screenshot each frame
node "$ROOT/tools/capture.js" "$ROOT/index.html" "$WORK" hero,knead

# 2. keep a 9 s loop and crossfade the extra last second into the start, so the GIF has no seam
python3 - "$WORK" <<'EOF'
import os, sys
from PIL import Image
work = sys.argv[1]
def loop(name, fps, L=9, F=1):
    src, dst = f'{work}/{name}', f'{work}/{name}_loop'
    os.makedirs(dst, exist_ok=True)
    nL, nF = L * fps, F * fps
    for j in range(nL):
        im = Image.open(f'{src}/{j:04d}.png').convert('RGB')
        if j < nF:
            tail = Image.open(f'{src}/{j + nL:04d}.png').convert('RGB')
            im = Image.blend(tail, im, j / nF)
        im.save(f'{dst}/{j:04d}.png')
loop('hero', 12)
loop('knead', 15)
EOF

# 3. encode at 10 fps with one shared palette and ordered dithering (keeps files ~3 MB)
encode() { # frames_dir input_fps width output
  ffmpeg -v error -y -framerate "$2" -i "$1/%04d.png" \
    -vf "fps=10,scale=$3:-2:flags=lanczos,palettegen=max_colors=112:stats_mode=full" "$WORK/pal.png"
  ffmpeg -v error -y -framerate "$2" -i "$1/%04d.png" -i "$WORK/pal.png" \
    -lavfi "fps=10,scale=$3:-2:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
    -loop 0 "$4"
}
mkdir -p "$ROOT/docs"
encode "$WORK/hero_loop" 12 840 "$ROOT/docs/demo.gif"
encode "$WORK/knead_loop" 15 480 "$ROOT/docs/kneading.gif"
ls -la "$ROOT/docs"
