#!/usr/bin/env python3
"""Contrôle technique de l'export : 1080x1920, 30 fps, H.264, yuv420p, -14 LUFS, pics < -1 dB.

Usage: final_check.py <final.mp4>
"""
import json, re, subprocess, sys, os

def main(f):
    v = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", f]))
    vs = next(s for s in v["streams"] if s["codec_type"] == "video"); au = next((s for s in v["streams"] if s["codec_type"] == "audio"), None)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", f, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    summ = r[r.rfind("Summary:"):]
    I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summ).group(1)); TP = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ).group(1))
    checks = [("1080x1920", (vs["width"], vs["height"]) == (1080, 1920), f'{vs["width"]}x{vs["height"]}'),
              ("30 fps", abs(eval(vs["avg_frame_rate"]) - 30) < 0.01, vs["avg_frame_rate"]),
              ("H.264", vs["codec_name"] == "h264", vs["codec_name"]), ("yuv420p", vs["pix_fmt"] == "yuv420p", vs["pix_fmt"]),
              ("audio AAC", bool(au) and au["codec_name"] == "aac", au["codec_name"] if au else "aucun"),
              ("-14 LUFS (±1)", abs(I + 14) <= 1.0, f"{I} LUFS"), ("pics < -1 dB", TP < -1.0, f"{TP} dBTP"),
              ("taille < 100 Mo", os.path.getsize(f) < 100e6, f"{os.path.getsize(f) / 1e6:.1f} Mo")]
    ok = True
    for n, p, d in checks: print(("OK   " if p else "FAIL ") + f"{n:18s} {d}"); ok &= p
    print("Durée : %.2fs" % float(v["format"]["duration"])); return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
