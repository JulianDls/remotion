#!/usr/bin/env bash
# Renderiza la intro.
#   bash scripts/render.sh            -> output/intro_congreso.mp4          (1920x1080, H.264, AAC 48 kHz)
#   bash scripts/render.sh preview    -> output/intro_congreso_preview_540p.mp4 (prueba rápida 960x540)
#   bash scripts/render.sh 4k         -> output/intro_congreso_4k.mp4       (3840x2160)
# Variables opcionales: REMOTION_BROWSER_EXECUTABLE (Chrome/Chromium propio), RENDER_CONCURRENCY.
set -euo pipefail
cd "$(dirname "$0")/.."
MODE="${1:-final}"
PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

# 1) Mezcla final con los volúmenes de config/intro.config.json (si hay entorno de audio).
if [ -f .cache/stems/music.wav ] && "$PY" -c "import numpy, scipy, soundfile, pyloudnorm, numba" 2>/dev/null; then
	"$PY" scripts/mix_audio.py
else
	echo "Aviso: no se regenera la mezcla (faltan stems o el entorno Python). Se usa public/audio/mix.wav tal cual."
fi

# 2) Render con Remotion.
RUNNER="npx"
command -v bunx >/dev/null 2>&1 && RUNNER="bunx"
EXTRA=()
[ -n "${REMOTION_BROWSER_EXECUTABLE:-}" ] && EXTRA+=("--browser-executable=${REMOTION_BROWSER_EXECUTABLE}")
[ -n "${RENDER_CONCURRENCY:-}" ] && EXTRA+=("--concurrency=${RENDER_CONCURRENCY}")
case "$MODE" in
	preview) OUT="output/intro_congreso_preview_540p.mp4"; ARGS=(--scale=0.5 --crf=22 --audio-bitrate=192k) ;;
	4k) OUT="output/intro_congreso_4k.mp4"; ARGS=(--scale=2 --crf=17 --audio-bitrate=320k) ;;
	*) OUT="output/intro_congreso.mp4"; ARGS=(--crf=15 --audio-bitrate=320k) ;;
esac
mkdir -p output
TMP="${OUT%.mp4}.tmp.mp4"
"$RUNNER" remotion render src/index.ts Intro "$TMP" --codec=h264 --pixel-format=yuv420p --audio-codec=aac "${ARGS[@]}" "${EXTRA[@]}"

# 3) MP4 con el índice al principio (reproducción inmediata en cualquier reproductor).
ffmpeg -y -loglevel error -i "$TMP" -c copy -movflags +faststart "$OUT"
rm -f "$TMP"
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,sample_rate,channels -of default=nw=1 "$OUT"
echo "Listo: $OUT"
