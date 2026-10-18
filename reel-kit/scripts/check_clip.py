#!/usr/bin/env python3
"""Vérifie le clip brut : 1080p, < 30 Mo, durée, audio, et du jeu en haut de cadre."""
import json, os, subprocess, sys

def main(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-print_format", "json",
                                   "-show_streams", "-show_format", path])
    info = json.loads(out)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    w, h = int(v["width"]), int(v["height"])
    rot = int(v.get("side_data_list", [{}])[0].get("rotation", 0)) if v.get("side_data_list") else 0
    if abs(rot) in (90, 270): w, h = h, w
    fps = eval(v["avg_frame_rate"]); dur = float(info["format"]["duration"])
    mb = os.path.getsize(path) / 1e6
    print(f"{os.path.basename(path)}: {w}x{h} @ {fps:.2f} fps, {dur:.1f}s, {mb:.1f} Mo, audio={'oui' if a else 'NON'}")
    warn = []
    if mb > 30: warn.append("plus de 30 Mo : ré-exporte plus léger (1080p, ~8 Mbps)")
    if (w, h) != (1080, 1920): warn.append("pas en 1080x1920 : il sera recadré/redimensionné en plein cadre 9:16")
    if not a: warn.append("aucune piste audio : impossible de transcrire")
    if dur > 90: warn.append("plus de 90 s : la transcription et le matting seront longs")
    for m in warn: print("  ATTENTION:", m)
    print("  Rappel : coupe l'air mort au début et à la fin, garde du jeu au-dessus de ta tête pour le texte.")

if __name__ == "__main__":
    main(sys.argv[1])
