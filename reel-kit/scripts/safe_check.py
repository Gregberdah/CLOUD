#!/usr/bin/env python3
"""Vérifie que rien d'important n'entre dans la safe area Instagram (haut 220 px, bas 380 px, droite 140 px).

Usage: safe_check.py <projet_dir>
Parcourt les PNG de layers/back et layers/front et signale les plages de temps où du texte/des graphiques (alpha > 25 %)
touchent une zone interdite. Les fonds/lueurs ne doivent PAS être dans ces calques.
"""
import glob, json, os, sys
import cv2, numpy as np

def main(P):
    st = json.load(open(os.path.join(P, "style.json"))); S, fps = st["safe"], st["canvas"]["fps"]; bad = {}
    for d in sorted(glob.glob(os.path.join(P, "layers/*/*"))):
        if not os.path.isdir(d): continue
        for f in sorted(glob.glob(os.path.join(d, "*.png"))):
            im = cv2.imread(f, cv2.IMREAD_UNCHANGED)
            if im is None or im.shape[2] < 4: continue
            a = im[..., 3] > 64; H, W = a.shape; hit = []
            if a[:S["top"]].any(): hit.append("haut")
            if a[H - S["bottom"]:].any(): hit.append("bas")
            if a[:, W - S["right"]:].any(): hit.append("droite")
            if hit: bad.setdefault((os.path.relpath(d, P), tuple(hit)), []).append(int(os.path.basename(f)[:5]))
    if not bad: print("OK : rien dans la safe area interdite."); return 0
    for (d, z), fr in bad.items():
        print(f"ATTENTION {d} : zone {'+'.join(z)} touchée de {fr[0] / fps:.2f}s à {fr[-1] / fps:.2f}s ({len(fr)} images)")
    return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
