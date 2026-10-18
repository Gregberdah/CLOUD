#!/usr/bin/env bash
# Prépare la machine de montage : dépendances Python, modèles (matting + transcription), vérif ffmpeg/Chromium.
set -euo pipefail
KIT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KIT"

command -v ffmpeg >/dev/null || { echo "ffmpeg manquant (apt-get install -y ffmpeg)"; exit 1; }
python3 -m pip install -q --disable-pip-version-check \
  numpy opencv-python-headless pillow onnxruntime playwright sherpa-onnx soundfile scipy 2>&1 | grep -v "running pip as the 'root'" || true

# Chromium : celui de Playwright est déjà là dans le cloud. Sinon on ne télécharge rien d'office.
if ! ls "${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"/chromium* >/dev/null 2>&1; then
  echo "Chromium introuvable : lance 'python3 -m playwright install chromium'"; fi

mkdir -p models
RVM=models/rvm_mobilenetv3_fp32.onnx
if [ ! -s "$RVM" ]; then
  echo ">> modèle de matting (RobustVideoMatting, 15 Mo)"
  curl -fSL --retry 3 -o "$RVM" \
    https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx
fi
PK=models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8
if [ ! -s "$PK/tokens.txt" ]; then
  echo ">> modèle de transcription Parakeet v3 multilingue (~480 Mo, timings au mot)"
  curl -fSL --retry 3 -o models/parakeet.tar.bz2 \
    https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2
  tar xjf models/parakeet.tar.bz2 -C models && rm models/parakeet.tar.bz2
fi
echo "OK. Prochaine étape : scripts/new_project.sh <nom> <clip.mp4>"
