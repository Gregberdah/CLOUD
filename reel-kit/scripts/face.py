#!/usr/bin/env python3
"""Localise la tête à partir du matte -> face.json (utilisé par captions et motion pour ne jamais couvrir le visage).

Usage: face.py <projet_dir>
face.json = {"head_top":y, "face_bottom":y, "cx":x, "head_w":px, "headroom":px}
Méthode : médiane sur le clip du haut du sujet, puis largeur de ligne en ligne ; le bas du visage est la ligne
où la largeur dépasse 1,7x celle de la tête (les épaules). Estimation prudente (inclut le cou).
"""
import json, os, subprocess, sys
import numpy as np

def main(P):
    style = json.load(open(os.path.join(P, "style.json")))
    W, H = style["canvas"]["width"], style["canvas"]["height"]
    w, h = W // 4, H // 4
    mt = subprocess.Popen(["ffmpeg", "-v", "error", "-i", os.path.join(P, "matte.mkv"), "-vf", "fps=3,scale=%d:%d" % (w, h),
                           "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    tops, bots, cxs, hws = [], [], [], []
    while True:
        b = mt.stdout.read(w * h)
        if len(b) < w * h: break
        a = np.frombuffer(b, np.uint8).reshape(h, w) > 128
        rows = np.where(a.sum(1) > 3)[0]
        if len(rows) < 10: continue
        top = rows[0]; span = h - top
        head = a[top + 2: top + max(4, int(span * 0.12))]
        widths = head.sum(1); hw = float(np.median(widths[widths > 0])) if (widths > 0).any() else 1
        cols = np.where(head.any(0))[0]
        fb = h
        for y in range(top + 4, h):
            if a[y].sum() > 1.7 * hw: fb = y; break
        tops.append(top); bots.append(fb); hws.append(hw); cxs.append((cols[0] + cols[-1]) / 2 if len(cols) else w / 2)
    if not tops: sys.exit("Aucune personne détectée dans le matte.")
    out = {"head_top": int(np.median(tops) * 4), "face_bottom": int(np.median(bots) * 4),
           "cx": int(np.median(cxs) * 4), "head_w": int(np.median(hws) * 4)}
    out["headroom"] = out["head_top"]
    json.dump(out, open(os.path.join(P, "face.json"), "w"), indent=1)
    print(out)
    if out["headroom"] < 220 + 120:
        print("ATTENTION : peu de jeu au-dessus de la tête (< 340 px) : le texte ira sous le visage.")

if __name__ == "__main__":
    main(sys.argv[1])
