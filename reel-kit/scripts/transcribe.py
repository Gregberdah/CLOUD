#!/usr/bin/env python3
"""Passe 01 : transcription mot à mot -> words.json, + tableau des pauses/accrocs -> issues.md.

Usage: transcribe.py <projet_dir> [--lang fr] [--backend auto|whisper|parakeet]
Backends : faster-whisper (si Hugging Face est joignable) sinon Parakeet v3 via sherpa-onnx (GitHub).
words.json = [{"i":0,"w":"mot","start":0.12,"end":0.40}, ...]
"""
import argparse, glob, json, os, subprocess, sys, wave
import numpy as np

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FILLERS = {"euh", "heu", "hum", "hmm", "um", "uh", "bah", "ben"}

def extract_audio(video, wav):
    subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000",
                           "-c:a", "pcm_s16le", wav])

def read_wav(wav):
    with wave.open(wav) as f:
        raw = f.readframes(f.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

def run_whisper(wav, lang):
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(wav, language=lang, word_timestamps=True, vad_filter=False)
    return [{"w": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
            for s in segs for w in s.words]

def speech_segments(audio, sr=16000, max_len=12.0):
    """Segments de parole [(début, fin)] par énergie : plancher de bruit + 12 dB, trous < 0.35 s comblés, marge 0.2 s."""
    hop = int(0.02 * sr); n = len(audio) // hop
    rms = np.sqrt((audio[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12); db = 20 * np.log10(rms)
    thr = max(np.percentile(db, 10) + 12, -50); on = db > thr
    segs, st = [], None
    for i, v in enumerate(on):
        if v and st is None: st = i
        if not v and st is not None: segs.append([st, i]); st = None
    if st is not None: segs.append([st, n])
    merged = []
    for s0, s1 in segs:
        if merged and (s0 - merged[-1][1]) * 0.02 < 0.35: merged[-1][1] = s1
        else: merged.append([s0, s1])
    out = []
    for s0, s1 in merged:
        if (s1 - s0) * 0.02 < 0.15: continue
        a0, a1 = max(0, s0 * 0.02 - 0.2), min(len(audio) / sr, s1 * 0.02 + 0.2)
        while a1 - a0 > max_len:                       # coupe au point le plus calme vers le milieu
            lo, hi = int((a0 + max_len * 0.5) / 0.02), int((a0 + max_len) / 0.02)
            c = lo + int(np.argmin(db[lo:hi])); out.append((a0, c * 0.02)); a0 = c * 0.02
        out.append((a0, a1))
    return out or [(0.0, len(audio) / sr)]

def run_parakeet(wav, lang):
    import sherpa_onnx
    d = os.path.join(KIT, "models", "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8")
    if not os.path.exists(os.path.join(d, "tokens.txt")):
        sys.exit("Modèle Parakeet absent : lance reel-kit/scripts/setup_env.sh")
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=f"{d}/encoder.int8.onnx", decoder=f"{d}/decoder.int8.onnx", joiner=f"{d}/joiner.int8.onnx",
        tokens=f"{d}/tokens.txt", num_threads=4, model_type="nemo_transducer")
    audio = read_wav(wav)
    words = []
    # Parakeet perd la langue/le fil sur un clip entier : on découpe sur les silences et on décode segment par segment.
    for (s0, s1) in speech_segments(audio):
        s = rec.create_stream(); s.accept_waveform(16000, audio[int(s0 * 16000):int(s1 * 16000)]); rec.decode_stream(s)
        r = s.result
        cur, cur_t, last_t = "", None, []
        for tok, t in zip(r.tokens, r.timestamps):
            t = t + s0
            if tok.startswith("\u2581") or tok.startswith(" "):
                if cur: words.append([cur, cur_t, last_t[-1]])
                cur, cur_t, last_t = tok.lstrip("\u2581 "), t, [t]
            else:
                cur += tok; last_t.append(t)
                if cur_t is None: cur_t = t
        if cur: words.append([cur, cur_t, last_t[-1]])
    out, dur = [], len(audio) / 16000
    for k, (w, st, lt) in enumerate(words):
        nxt = words[k + 1][1] if k + 1 < len(words) else dur
        end = min(nxt, lt + 0.32)       # Parakeet ne donne que les débuts de tokens : on borne la fin
        out.append({"w": w, "start": round(st, 3), "end": round(max(end, st + 0.08), 3)})
    return out

def analyze(words, thr=0.4):
    rows = []
    if words and words[0]["start"] > thr:
        rows.append(("pause début", 0.0, words[0]["start"], "air mort avant le premier mot"))
    for a, b in zip(words, words[1:]):
        gap = b["start"] - a["end"]
        if gap > thr:
            rows.append(("pause", a["end"], b["start"], f'{gap:.2f}s entre "{a["w"]}" et "{b["w"]}"'))
    norm = lambda x: "".join(c for c in x.lower() if c.isalnum())
    for k, a in enumerate(words):
        if norm(a["w"]) in FILLERS:
            rows.append(("tic", a["start"], a["end"], f'"{a["w"]}"'))
    for n in (3, 2, 1):                   # mots/phrases répétés d'affilée = reprise
        for k in range(len(words) - 2 * n + 1):
            x = [norm(w["w"]) for w in words[k:k + n]]; y = [norm(w["w"]) for w in words[k + n:k + 2 * n]]
            if x == y and all(x):
                rows.append(("reprise", words[k]["start"], words[k + n - 1]["end"],
                             "répété : " + " ".join(w["w"] for w in words[k:k + n])))
    rows.sort(key=lambda r: r[1])
    return rows

def tc(t): return f"{int(t // 60):02d}:{t % 60:05.2f}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("--lang", default="fr")
    ap.add_argument("--backend", default="auto", choices=["auto", "whisper", "parakeet"])
    a = ap.parse_args()
    P = a.project
    src = glob.glob(os.path.join(P, "raw.*"))[0]
    wav = os.path.join(P, "renders", "audio16k.wav"); os.makedirs(os.path.dirname(wav), exist_ok=True)
    extract_audio(src, wav)
    words = None
    if a.backend in ("auto", "whisper"):
        try: words = run_whisper(wav, a.lang); print("backend: faster-whisper")
        except Exception as e:
            if a.backend == "whisper": raise
            print(f"whisper indisponible ({type(e).__name__}), bascule sur Parakeet")
    if words is None:
        words = run_parakeet(wav, a.lang); print("backend: parakeet (sherpa-onnx)")
    for i, w in enumerate(words): w["i"] = i
    json.dump(words, open(os.path.join(P, "words.json"), "w"), ensure_ascii=False, indent=1)
    rows = analyze(words)
    with open(os.path.join(P, "issues.md"), "w") as f:
        f.write("# Pauses > 0.4 s, tics et reprises (rien n'est coupé tant que tu n'as pas validé)\n\n")
        f.write("| # | type | de | à | détail |\n|---|---|---|---|---|\n")
        for n, (k, s, e, d) in enumerate(rows, 1): f.write(f"| {n} | {k} | {tc(s)} | {tc(e)} | {d} |\n")
    with open(os.path.join(P, "transcript.md"), "w") as f:
        f.write("| # | début | fin | mot |\n|---|---|---|---|\n")
        for w in words: f.write(f'| {w["i"]} | {tc(w["start"])} | {tc(w["end"])} | {w["w"]} |\n')
    print(f"{len(words)} mots -> words.json, transcript.md ; {len(rows)} points dans issues.md")

if __name__ == "__main__":
    main()
