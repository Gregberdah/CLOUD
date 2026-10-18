#!/usr/bin/env bash
# Crée projects/<nom>/ avec l'arborescence standard, copie le clip brut et le vérifie.
set -euo pipefail
KIT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="${1:?usage: new_project.sh <nom> <clip.mp4>}"; CLIP="${2:?clip manquant}"
P="$KIT/../projects/$NAME"
mkdir -p "$P"/{layers/back,layers/front,renders,sfx}
[ -e "$P"/raw.* ] || cp "$CLIP" "$P/raw.${CLIP##*.}"
[ -e "$P/style.json" ] || cp "$KIT/style.json" "$P/style.json"
[ -e "$P/Reel-Style-Rules.md" ] || cp "$KIT/Reel-Style-Rules.md" "$P/Reel-Style-Rules.md"
python3 "$KIT/scripts/check_clip.py" "$P"/raw.*
echo "Projet prêt : $P"
