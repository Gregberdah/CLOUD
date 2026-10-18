#!/usr/bin/env python3
"""Passe 01 (suite) : applique les coupes, garde ~0.1 s de souffle de chaque côté, re-cale words.json.

Usage: cut.py <projet_dir> cuts.json
cuts.json = [[start,end], ...] en secondes sur le clip BRUT : les zones à supprimer (pauses, accrocs).
Sorties : base.mp4 (clip serré, 1080x1920, 30 fps, CFR), words.cut.json (re-calé), keep.json.
Si words.cut.json existe, c'est lui que lisent les passes 03 à 05.
"""
import glob, json, os, subprocess, sys

def main(P, cuts_file):
    style = json.load(open(os.path.join(P, "style.json")))
    breath, fps = style["audio"]["breath"], style["canvas"]["fps"]
    W, H = style["canvas"]["width"], style["canvas"]["height"]
    src = glob.glob(os.path.join(P, "raw.*"))[0]
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", src]).decode())
    words = json.load(open(os.path.join(P, "words.json")))
    cuts = sorted([[max(0, s + breath), min(dur, e - breath)] for s, e in json.load(open(cuts_file))
                   if e - s > 2 * breath + 0.02])
    keep, t = [], 0.0
    for s, e in cuts:
        if s > t: keep.append([t, s])
        t = max(t, e)
    if t < dur: keep.append([t, dur])
    parts, offs, acc = [], [], 0.0
    for s, e in keep:
        offs.append((s, e, acc)); acc += e - s
    fc = []
    for k, (s, e) in enumerate(keep):
        fc.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS[v{k}]")
        fc.append(f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.008,"
                  f"afade=t=out:st={max(0, e - s - 0.008):.3f}:d=0.008[a{k}]")
    n = len(keep)
    fc.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[cv][ca]")
    fc.append(f"[cv]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},format=yuv420p[v]")
    out = os.path.join(P, "base.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex", ";".join(fc),
                           "-map", "[v]", "-map", "[ca]", "-c:v", "libx264", "-crf", "14", "-preset", "fast",
                           "-r", str(fps), "-c:a", "aac", "-b:a", "256k", "-ar", "48000", out])
    new = []
    for w in words:
        for s, e, off in offs:
            if w["start"] >= s - 1e-3 and w["start"] < e:
                new.append({**w, "start": round(w["start"] - s + off, 3), "end": round(min(w["end"], e) - s + off, 3)})
                break
    for i, w in enumerate(new): w["i"] = i
    json.dump(new, open(os.path.join(P, "words.cut.json"), "w"), ensure_ascii=False, indent=1)
    json.dump([{"src_start": s, "src_end": e, "dst_start": o} for s, e, o in offs],
              open(os.path.join(P, "keep.json"), "w"), indent=1)
    print(f"base.mp4 : {acc:.2f}s (brut {dur:.2f}s), {len(words) - len(new)} mots retirés, words.cut.json re-calé")

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
