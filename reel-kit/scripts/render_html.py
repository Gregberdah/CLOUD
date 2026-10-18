#!/usr/bin/env python3
"""Rend une page HTML image par image dans Chromium headless -> séquence PNG transparente.

Usage: render_html.py <page.html> <out_dir> --duration 12.5 [--fps 30] [--size 1080x1920] [--from 0 --to 12.5]
La page expose window.setTime(t) (et window.READY=true quand ses polices sont chargées) (secondes) : elle doit afficher EXACTEMENT l'état à l'instant t
(pas d'animation temps réel). Chaque graphique est donc calé à l'image près sur son mot.
--data x.json : données injectées (window.DATA). --layer back|front : lu par la page (?layer=).
--from/--to : ne re-rend que cette plage (les autres PNG restent), pour "re-render 00:04 à 00:07".
"""
import argparse, os, sys, glob
from playwright.sync_api import sync_playwright

def chromium_path():
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", os.path.expanduser("~/.cache/ms-playwright"))
    for pat in ("chromium-*/chrome-linux/chrome", "chromium/chrome-linux/chrome", "chromium"):
        hits = glob.glob(os.path.join(base, pat))
        if hits and os.path.isfile(hits[0]): return hits[0]
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page"); ap.add_argument("out"); ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--fps", type=int, default=30); ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--data", help="JSON injecté dans window.DATA"); ap.add_argument("--layer", default="")
    ap.add_argument("--from", dest="t0", type=float, default=0.0); ap.add_argument("--to", dest="t1", type=float)
    a = ap.parse_args()
    W, H = map(int, a.size.split("x")); os.makedirs(a.out, exist_ok=True)
    n = int(round(a.duration * a.fps))
    f0 = int(a.t0 * a.fps); f1 = min(n, int((a.t1 if a.t1 else a.duration) * a.fps) + 1)
    with sync_playwright() as p:
        kw = {"executable_path": chromium_path()} if chromium_path() else {}
        b = p.chromium.launch(args=["--no-sandbox", "--force-device-scale-factor=1"], **kw)
        pg = b.new_page(viewport={"width": W, "height": H})
        if a.data: pg.add_init_script("window.DATA = " + open(a.data).read() + ";")
        pg.goto("file://" + os.path.abspath(a.page) + (f"?layer={a.layer}" if a.layer else "")); pg.wait_for_function("window.setTime !== undefined && window.READY !== false", timeout=30000)
        pg.evaluate("document.fonts.ready")
        for f in range(f0, f1):
            pg.evaluate(f"window.setTime({f / a.fps:.5f})")
            pg.screenshot(path=os.path.join(a.out, f"{f:05d}.png"), omit_background=True)
        notes = pg.evaluate("window.NOTES || []"); b.close()
        for note in notes: print("NOTE:", note)
    print(f"{f1 - f0} images -> {a.out} ({n} au total)")

if __name__ == "__main__":
    main()
