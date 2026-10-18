#!/usr/bin/env python3
"""Passe 05 : design sonore + master + export final.

Usage: sound.py <projet_dir> --video renders/video.mp4 --out renders/final.mp4 [--music musique.mp3] [--cover 1.2]
- SFX depuis cues.json : hit (hook), tap (clics), whoosh (changements de scène), chime (fermeture).
  Si reel-kit/assets/sfx/<hit|tap|whoosh|chime>.wav existe, il remplace le son généré.
- Voix nettoyée (coupe grave, réduction de souffle), toujours au-dessus. Musique éventuelle : ducking sous la voix.
- Master 2 passes à -14 LUFS, pics vraiment sous -1 dB. Sortie 1080x1920, 30 fps, H.264 + AAC, cover.jpg.
"""
import argparse, glob, json, os, re, subprocess, sys, wave
import numpy as np

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SR = 48000

def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR; return np.minimum(t / a, 1) * np.exp(-t / d)

def gen(kind):
    rng = np.random.default_rng(7)
    if kind == "hit":      # impact grave : sinus qui chute + transitoire de bruit
        n = int(SR * 0.9); t = np.arange(n) / SR
        f = 48 + 90 * np.exp(-t * 18); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .001, .28)
        x += rng.standard_normal(n) * env(n, .0005, .03) * 0.35; return x * 0.9
    if kind == "tap":      # clic sec
        n = int(SR * 0.12); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 1800 * t) * env(n, .0005, .018) + rng.standard_normal(n) * env(n, .0003, .006) * 0.25) * 0.8
    if kind == "whoosh":   # bruit filtré qui monte puis retombe
        n = int(SR * 0.55); x = rng.standard_normal(n); t = np.linspace(0, 1, n)
        from scipy.signal import butter, sosfilt
        out = np.zeros(n); seg = 24
        for k in range(seg):
            lo, hi = 400 + 3500 * np.sin(np.pi * k / seg) ** 1.5, 900 + 5500 * np.sin(np.pi * k / seg) ** 1.5
            sos = butter(2, [lo, min(hi, 20000)], btype="band", fs=SR, output="sos")
            a, b = int(k * n / seg), int((k + 1) * n / seg); out[a:b] = sosfilt(sos, x)[a:b]
        return out * np.sin(np.pi * t) ** 2 * 0.55
    if kind == "chime":    # accord doux, queue longue
        n = int(SR * 1.8); t = np.arange(n) / SR
        x = sum(np.sin(2 * np.pi * f * t) * a * np.exp(-t * d) for f, a, d in
                [(880, 1, 2.4), (1318.5, .6, 3.0), (1760, .35, 4.0), (2637, .15, 5.5)])
        return x * np.minimum(t / .004, 1) * 0.35
    raise ValueError(kind)

def load_wav(path):
    with wave.open(path) as f:
        ch, sr, raw = f.getnchannels(), f.getframerate(), f.readframes(f.getnframes()); w = f.getsampwidth()
    x = np.frombuffer(raw, {1: np.uint8, 2: np.int16, 4: np.int32}[w]).astype(np.float32)
    x = (x - 128) / 128 if w == 1 else x / float(2 ** (8 * w - 1))
    x = x.reshape(-1, ch).mean(1)
    if sr != SR:
        from scipy.signal import resample_poly
        from math import gcd; g = gcd(sr, SR); x = resample_poly(x, SR // g, sr // g)
    return x.astype(np.float32)

GAIN = {"hit": 0.8, "tap": 0.5, "whoosh": 0.45, "chime": 0.5}   # sous la voix : l'ensemble est mixé à 0.55 de la voix

def write_wav(path, x):
    x = np.clip(x, -1, 1); st = np.stack([x, x], 1)
    with wave.open(path, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((st * 32767).astype("<i2").tobytes())

def sh(cmd, capture=False):
    r = subprocess.run(cmd, capture_output=capture, text=True)
    if r.returncode: sys.exit(f"ffmpeg a échoué : {' '.join(cmd)}\n{r.stderr}")
    return r.stderr if capture else ""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--video", required=True)
    ap.add_argument("--out", default="renders/final.mp4"); ap.add_argument("--music"); ap.add_argument("--cover", type=float)
    a = ap.parse_args(); P = a.project; style = json.load(open(os.path.join(P, "style.json"))); au = style["audio"]
    j = lambda p: p if os.path.isabs(p) else os.path.join(P, p)
    video, out = j(a.video), j(a.out); base = os.path.join(P, "base.mp4")
    if not os.path.exists(base): base = glob.glob(os.path.join(P, "raw.*"))[0]
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video]).decode())
    cues = json.load(open(os.path.join(P, "cues.json"))) if os.path.exists(os.path.join(P, "cues.json")) else []
    # 1) piste SFX
    track = np.zeros(int(SR * (dur + 2)), np.float32); lib, used = {}, {}
    for c in cues:
        k = c["kind"]
        if k not in lib:
            own = os.path.join(KIT, "assets/sfx", f"{k}.wav"); proj = os.path.join(P, "sfx", f"{k}.wav")
            src = next((p for p in (proj, own) if os.path.exists(p)), None)
            lib[k] = load_wav(src) if src else gen(k); used[k] = "fichier perso" if src else "généré"
        s = lib[k] * GAIN[k]; i = int(c["t"] * SR); track[i:i + len(s)] += s[:len(track) - i]
    sfx = os.path.join(P, "renders", "sfx_track.wav"); write_wav(sfx, track)
    # 2) voix propre
    voice = os.path.join(P, "renders", "voice_clean.wav")
    sh(["ffmpeg", "-y", "-v", "error", "-i", base, "-vn", "-af",
        "highpass=f=80,afftdn=nr=10:nf=-32,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=3,"
        "equalizer=f=3500:t=q:w=1.2:g=1.5", "-ar", str(SR), "-ac", "2", voice])
    # 3) mix : voix + SFX (+ musique ducking)
    mix = os.path.join(P, "renders", "mix.wav")
    ins = ["-i", voice, "-i", sfx]; fc = "[1:a]volume=0.55[fx]"
    if a.music:
        ins += ["-stream_loop", "-1", "-i", j(a.music)]
        fc += ";[0:a]asplit=2[v][vsc];[2:a]volume=0.5,atrim=0:%.3f[mu];[mu][vsc]sidechaincompress=threshold=0.04:ratio=9:attack=15:release=300[md];[v][fx][md]amix=inputs=3:normalize=0:duration=first[m]" % dur
    else: fc += ";[0:a][fx]amix=inputs=2:normalize=0:duration=first[m]"
    sh(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fc, "-map", "[m]", "-t", f"{dur:.3f}", mix])
    # 4) master 2 passes -14 LUFS / TP < -1 dB
    I, TP = au["lufs"], au["true_peak"] - 0.5
    log = sh(["ffmpeg", "-hide_banner", "-i", mix, "-af", f"loudnorm=I={I}:TP={TP}:LRA=11:print_format=json", "-f", "null", "-"], True)
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", log, re.S).group(0))
    ln = (f"loudnorm=I={I}:TP={TP}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,alimiter=limit=0.88:level=disabled")
    mastered = os.path.join(P, "renders", "master.wav")
    sh(["ffmpeg", "-y", "-v", "error", "-i", mix, "-af", ln, "-ar", str(SR), mastered])
    # 5) export final + cover
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sh(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", mastered, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "16",
        "-preset", "slow", "-pix_fmt", "yuv420p", "-r", str(style["canvas"]["fps"]), "-s", f"{style['canvas']['width']}x{style['canvas']['height']}",
        "-c:a", "aac", "-b:a", "256k", "-ar", str(SR), "-movflags", "+faststart", "-shortest", out])
    ct = a.cover
    if ct is None and os.path.exists(os.path.join(P, "captions.json")):
        its = json.load(open(os.path.join(P, "captions.json")))["items"]
        k = next((i for i in its if any(w["key"] for w in i["words"])), None)
        ct = (k["start"] + 0.45) if k else 1.0
    cover = os.path.splitext(out)[0] + "_cover.jpg"
    sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{ct or 1.0:.2f}", "-i", out, "-frames:v", "1", "-q:v", "2", cover])
    print("SFX :", ", ".join(f"{k} ({v})" for k, v in used.items()) or "aucun"); print(out); print(cover)

if __name__ == "__main__":
    main()
