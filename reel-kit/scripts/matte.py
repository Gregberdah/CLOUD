#!/usr/bin/env python3
"""Passe 02 : cut-out. Détoure la personne image par image -> matte.mkv (gris, réutilisable), + vidéos de contrôle.

Usage: matte.py <projet_dir> [--ratio 0.4] [--word "MOT"] [--check-only]
- RobustVideoMatting (ONNX) avec états récurrents. --ratio = downsample_ratio (0.5 = "2x plus gros", plus net, plus lent).
- Bords doux : léger flou de bord, trous remplis (corps et mains), aucun contour blanc, aucun glow.
- Sorties : matte.mkv, renders/check_checker.mp4, renders/check_dark.mp4 (un gros mot derrière la tête).
"""
import argparse, json, os, subprocess, sys
import cv2, numpy as np

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def reader(path, w, h, fps):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={w}:{h}",
                             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

def writer(path, w, h, fps, pix="gray", codec=("-c:v", "ffv1")):
    return subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", pix, "-s", f"{w}x{h}",
                             "-r", str(fps), "-i", "-", *codec, path], stdin=subprocess.PIPE)

def fill_holes(a):
    """Remplit les trous à l'intérieur du corps/des mains sans toucher aux bords doux (cheveux)."""
    m = (a > 0.5).astype(np.uint8)
    h, w = m.shape
    ff = m.copy(); mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(ff, mask, (0, 0), 1) if m[0, 0] == 0 else None
    holes = (ff == 0).astype(np.uint8)          # zones 0 non reliées au fond
    holes = cv2.morphologyEx(holes, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return np.maximum(a, holes.astype(np.float32))

def refine(a, prev, k_blur):
    a = fill_holes(a)
    a = np.clip((a - 0.04) / 0.92, 0, 1)         # resserre légèrement : supprime le halo, garde les cheveux
    if k_blur: a = cv2.GaussianBlur(a, (0, 0), k_blur)
    if prev is not None: a = 0.7 * a + 0.3 * prev   # lissage temporel léger : moins de scintillement
    return a

def light_wrap(fg, bg, alpha, strength=0.35, radius=18):
    """Fait déborder un peu la couleur du nouveau fond sur le bord du sujet. Pas d'outline."""
    inner = cv2.GaussianBlur(alpha, (0, 0), radius)
    edge = np.clip(alpha * (1 - inner) * 2.2, 0, 1)[..., None]
    bgb = cv2.GaussianBlur(bg, (0, 0), radius / 2)
    return fg * (1 - edge * strength) + bgb * edge * strength

def checker(w, h, s=48):
    y, x = np.mgrid[0:h, 0:w]
    c = (((x // s) + (y // s)) % 2).astype(np.float32)
    return (0.55 + 0.25 * c)[..., None].repeat(3, 2)

def big_word_bg(w, h, word, style):
    bg = np.zeros((h, w, 3), np.float32); bg[:] = np.array([9, 9, 10]) / 255
    img = bg.copy()
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(os.path.join(KIT, "assets/fonts", style["fonts"]["key"]["file"]), int(w * 0.34))
    pil = Image.fromarray((img * 255).astype(np.uint8)); d = ImageDraw.Draw(pil)
    bb = d.textbbox((0, 0), word, font=f)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], h * 0.30 - bb[1]), word, font=f, fill=(246, 189, 216))
    return np.asarray(pil).astype(np.float32) / 255

def run_matte(P, ratio, W, H, fps, k_blur):
    import onnxruntime as ort
    sess = ort.InferenceSession(os.path.join(KIT, "models/rvm_mobilenetv3_fp32.onnx"),
                                providers=["CPUExecutionProvider"])
    base = os.path.join(P, "base.mp4")
    if not os.path.exists(base): base = [os.path.join(P, f) for f in os.listdir(P) if f.startswith("raw.")][0]
    # inférence à résolution réduite, matte remis à 1080x1920 ensuite
    iw, ih = (int(W * 0.5) // 8 * 8, int(H * 0.5) // 8 * 8)
    rd = reader(base, iw, ih, fps)
    wr = writer(os.path.join(P, "matte.mkv"), W, H, fps)
    rec = [np.zeros((1, 1, 1, 1), np.float32) for _ in range(4)]
    dr = np.array([ratio], np.float32); prev = None; n = 0
    while True:
        buf = rd.stdout.read(iw * ih * 3)
        if len(buf) < iw * ih * 3: break
        src = np.frombuffer(buf, np.uint8).reshape(ih, iw, 3).astype(np.float32) / 255
        out = sess.run(None, {"src": src.transpose(2, 0, 1)[None], "r1i": rec[0], "r2i": rec[1],
                              "r3i": rec[2], "r4i": rec[3], "downsample_ratio": dr})
        pha, rec = out[1][0, 0], list(out[2:6])
        a = cv2.resize(pha, (W, H), interpolation=cv2.INTER_CUBIC)
        a = refine(np.clip(a, 0, 1), prev, k_blur); prev = a
        wr.stdin.write((a * 255 + 0.5).astype(np.uint8).tobytes()); n += 1
        if n % 60 == 0: print(f"  {n} images", flush=True)
    wr.stdin.close(); wr.wait(); rd.wait()
    print(f"matte.mkv : {n} images")

def run_checks(P, W, H, fps, word, style):
    base = os.path.join(P, "base.mp4")
    if not os.path.exists(base): base = [os.path.join(P, f) for f in os.listdir(P) if f.startswith("raw.")][0]
    for name in ("checker", "dark"):
        rd = reader(base, W, H, fps)
        mt = subprocess.Popen(["ffmpeg", "-v", "error", "-i", os.path.join(P, "matte.mkv"), "-f", "rawvideo",
                               "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
        wr = writer(os.path.join(P, "renders", f"check_{name}.mp4"), W, H, fps, "rgb24",
                    ("-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p"))
        bg = checker(W, H) if name == "checker" else big_word_bg(W, H, word, style)
        while True:
            fb = rd.stdout.read(W * H * 3); mb = mt.stdout.read(W * H)
            if len(fb) < W * H * 3 or len(mb) < W * H: break
            fg = np.frombuffer(fb, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
            a = np.frombuffer(mb, np.uint8).reshape(H, W).astype(np.float32) / 255
            fg = light_wrap(fg, bg, a)
            o = fg * a[..., None] + bg * (1 - a[..., None])
            wr.stdin.write((np.clip(o, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
        wr.stdin.close(); wr.wait(); rd.wait(); mt.wait()
        print("renders/check_%s.mp4" % name)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("project")
    ap.add_argument("--ratio", type=float, default=0.4); ap.add_argument("--blur", type=float, default=1.2)
    ap.add_argument("--word", default="STUCK"); ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    style = json.load(open(os.path.join(a.project, "style.json")))
    W, H, fps = style["canvas"]["width"], style["canvas"]["height"], style["canvas"]["fps"]
    if not a.check_only: run_matte(a.project, a.ratio, W, H, fps, a.blur)
    run_checks(a.project, W, H, fps, a.word, style)
