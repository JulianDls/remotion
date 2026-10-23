#!/usr/bin/env bash
# Descarga los recursos necesarios para REGENERAR voz y música (no hacen falta solo para renderizar).
#  - Supertonic 3 (TTS, modelo OpenRAIL-M / código MIT) vía sherpa-onnx
#  - Whisper small y Parakeet TDT v3 (verificación de la narración y marcas de tiempo)
#  - VS Chamber Orchestra 2 Community Edition (samples orquestales CC0)
set -euo pipefail
cd "$(dirname "$0")/.."
M=.cache/models
S=.cache/samples
mkdir -p "$M" "$S"
REL=https://github.com/k2-fsa/sherpa-onnx/releases/download
fetch() { # url destino
	[ -d "$2" ] && { echo "ya existe: $2"; return; }
	curl -fL --retry 4 -o /tmp/_asset.tar.bz2 "$1"
	tar xjf /tmp/_asset.tar.bz2 -C "$M"
	rm -f /tmp/_asset.tar.bz2
}
fetch "$REL/tts-models/sherpa-onnx-supertonic-3-tts-int8-2026-05-11.tar.bz2" "$M/sherpa-onnx-supertonic-3-tts-int8-2026-05-11"
fetch "$REL/asr-models/sherpa-onnx-whisper-small.tar.bz2" "$M/sherpa-onnx-whisper-small"
fetch "$REL/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2" "$M/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"
rm -f "$M"/sherpa-onnx-whisper-small/small-encoder.onnx "$M"/sherpa-onnx-whisper-small/small-decoder.onnx
if [ ! -d "$S/vsco/Strings" ]; then
	git clone --filter=blob:none --no-checkout --depth 1 https://github.com/sgossner/VSCO-2-CE.git "$S/vsco"
	cd "$S/vsco"
	git sparse-checkout init --no-cone
	git sparse-checkout set '/Strings/Violin Section/' '/Strings/Viola Section/' '/Strings/Cello Section/' '/Strings/Solo Contrabass/' \
		'/Strings/Harp/' '/Brass/F Horn/' '/Brass/Tenor Trombone/' '/Brass/Tuba/' '/Percussion/Timpani/' '/Percussion/BDrumNewhit*' \
		'/Percussion/bassdrum*' '/Percussion/cymbal*' '/Percussion/susCymb*' '/Percussion/gong*' '/Percussion/Snare*' '/Percussion/timp*' \
		'/Percussion/Glock*' '/Keys/Upright Piano/' '/LICENSE' '/README.md' '/Readme.txt'
	git checkout master
	rm -rf .git
fi
echo "Recursos listos en .cache/"
