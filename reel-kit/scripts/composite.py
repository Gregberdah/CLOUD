#!/usr/bin/env python3
"""Assemble les calques : [fond] -> calques DERRIÈRE moi -> moi (matte) -> calques DEVANT moi -> push-ins.

Usage: composite.py <projet_dir> --out renders/preview_pass03.mp4 [--with-audio] [--backdrop dark] [--from 0 --to 8]
Calques : tout dossier de PNG sous layers/back/<nom>/ (derrière) et layers/front/<nom>/ (devant), empilés par ordre alphabétique.
Sans matte.mkv (avant la passe 02) : tout est posé par-dessus la vidéo.
--backdrop dark : remplace le fond d'origine par #09090A + lueur chaude, avec light wrap sur les bords (sans contour).
push.json : [{"at":s,"dur":s,"amount":0.04}] -> push-in doux (<= 6 %), jamais de tremblement.
"""
import argparse, glob, json, os, subprocess, sys
import cv2, numpy as np

def run_ffmpeg_read(path, W, H, fps, pix, t0, t1):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(t0)] if t0 else []) + ["-i", path] + (["-t", str(t1 - t0)] if t1 else []) + \
          ["-vf", f"fps={fps},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", pix, "-"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE)

def backdrop(W, H, style):
    bg = np.zeros((H, W, 3), np.float32); bg[:] = np.array([9, 9, 10], np.float32) / 255
    y, x = np.mgrid[0:H, 0:W]
    g = np.exp(-(((x - W * 0.5) / (W * 0.7)) ** 2 + ((y - H * 0.38) / (H * 0.35)) ** 2))
    warm = np.array([255, 190, 160], np.float32) / 255 * 0.10
    return np.clip(bg + g[..., None] * warm, 0, 1)

def wrap(fg, bg, a, strength=0.30, radius=18):
    inner = cv2.GaussianBlur(a, (0, 0), radius); edge = np.clip(a * (1 - inner) * 2.2, 0, 1)[..., None]
    return fg * (1 - edge * strength) + cv2.GaussianBlur(bg, (0, 0), radius / 2) * edge * strength

def over(dst, png_path):
    im = cv2.imread(png_path, cv2.IMREAD_UNCHANGED)
    if im is None or im.shape[2] < 4: return dst
    a = im[..., 3:4].astype(np.float32) / 255
    if not a.any(): return dst
    rgb = im[..., 2::-1].astype(np.float32) / 255
    return rgb * a + dst * (1 - a)

def push_scale(t, push):
    s = 0.0
    for p in push:
        a, d, m = p["at"], p["dur"], p["amount"]
        if a <= t <= a + d + 0.3:
            k = min(1, (t - a) / 0.25) if t < a + d else max(0, 1 - (t - a - d) / 0.3)
            s = max(s, m * (1 - (1 - k) ** 3))
    return 1 + s

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--out", required=True)
    ap.add_argument("--with-audio", action="store_true"); ap.add_argument("--backdrop", choices=["none", "dark"], default="none")
    ap.add_argument("--from", dest="t0", type=float, default=0); ap.add_argument("--to", dest="t1", type=float, default=0)
    ap.add_argument("--crf", type=int, default=16)
    a = ap.parse_args(); P = a.project
    style = json.load(open(os.path.join(P, "style.json"))); W, H, fps = (style["canvas"][k] for k in ("width", "height", "fps"))
    base = os.path.join(P, "base.mp4") if os.path.exists(os.path.join(P, "base.mp4")) else glob.glob(os.path.join(P, "raw.*"))[0]
    matte = os.path.join(P, "matte.mkv"); has_matte = os.path.exists(matte)
    back = sorted(d for d in glob.glob(os.path.join(P, "layers/back/*")) if os.path.isdir(d))
    front = sorted(d for d in glob.glob(os.path.join(P, "layers/front/*")) if os.path.isdir(d))
    push = json.load(open(os.path.join(P, "push.json"))) if os.path.exists(os.path.join(P, "push.json")) else []
    out = a.out if os.path.isabs(a.out) else os.path.join(P, a.out); os.makedirs(os.path.dirname(out), exist_ok=True)
    rd = run_ffmpeg_read(base, W, H, fps, "rgb24", a.t0, a.t1)
    mt = run_ffmpeg_read(matte, W, H, fps, "gray", a.t0, a.t1) if has_matte else None
    tmp = out + ".silent.mp4"
    wr = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                           "-c:v", "libx264", "-crf", str(a.crf), "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp],
                          stdin=subprocess.PIPE)
    bd = backdrop(W, H, style) if a.backdrop == "dark" else None
    f0 = int(a.t0 * fps); n = 0
    while True:
        fb = rd.stdout.read(W * H * 3)
        if len(fb) < W * H * 3: break
        fn = f0 + n; t = fn / fps; name = f"{fn:05d}.png"
        vid = np.frombuffer(fb, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
        if has_matte:
            m = mt.stdout.read(W * H)
            if len(m) < W * H: break
            al = np.frombuffer(m, np.uint8).reshape(H, W).astype(np.float32) / 255
            canvas = bd.copy() if bd is not None else vid.copy()
            for d in back: canvas = over(canvas, os.path.join(d, name))
            fg = wrap(vid, canvas, al) if bd is not None else vid
            frame = fg * al[..., None] + canvas * (1 - al[..., None])
        else:
            frame = vid
            for d in back: frame = over(frame, os.path.join(d, name))
        for d in front: frame = over(frame, os.path.join(d, name))
        s = push_scale(t, push)
        if s > 1.0001:
            M = np.array([[s, 0, W * (1 - s) / 2], [0, s, H * (1 - s) * 0.42]], np.float32)  # push-in centré un peu au-dessus du milieu
            frame = cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        wr.stdin.write((np.clip(frame, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes()); n += 1
        if n % 90 == 0: print(f"  {n} images", flush=True)
    wr.stdin.close(); wr.wait(); rd.wait()
    if mt: mt.wait()
    if a.with_audio:
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", tmp] + (["-ss", str(a.t0)] if a.t0 else []) + ["-i", base] + (["-t", str(n / fps)]) + \
              ["-map", "0:v", "-map", "1:a?", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out]
        subprocess.check_call(cmd); os.remove(tmp)
    else: os.replace(tmp, out)
    print(f"{out} : {n} images, {n / fps:.2f}s")

if __name__ == "__main__":
    main()
