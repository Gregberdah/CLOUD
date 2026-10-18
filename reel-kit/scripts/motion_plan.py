#!/usr/bin/env python3
"""Passe 04 : retrouve l'instant de chaque mot déclencheur dans words.cut.json et sort le plan (tableau) + scenes.json.

Usage: motion_plan.py <projet_dir> scenes_draft.json
scenes_draft.json = [{"id":"s1","says":"overanalysis","layer":"back","type":"bigword","dur":2.0,"props":{...},
                      "taps":[0.6,1.2], "push":0.04}, ...]
- "says" : mot ou suite de mots (comme dans words.cut.json). L'instant "at" = début de ce mot.
- Une idée à l'écran à la fois : le script signale deux scènes qui se chevauchent.
- Sorties : scenes.json (pour motion_layer.html), cues.json (hit/tap/whoosh/chime pour la passe 05),
            push.json (push-ins <= 6 %), motion_plan.md (à valider AVANT de construire).
"""
import json, os, re, sys

def norm(w): return re.sub(r"[^\w]", "", w.lower())

def find(words, phrase):
    toks = [norm(x) for x in phrase.split()]
    for k in range(len(words) - len(toks) + 1):
        if [norm(w["w"]) for w in words[k:k + len(toks)]] == toks: return words[k]["start"], words[k + len(toks) - 1]["end"]
    return None

def band(typ, style, face):
    """Bande verticale occupée par la scène (px) : sert à ne pas y poser de sous-titre."""
    H, S = style["canvas"]["height"], style["safe"]; bot = H - S["bottom"]; ht = face["head_top"] if face else 700
    return {"notif_stack": [max(S["top"] + 20, ht - 560), max(S["top"] + 20, ht - 560) + 520], "tiles": [bot - 300, bot - 60],
            "source_card": [bot - 330, bot - 60], "label": [S["top"] + 30, S["top"] + 90]}.get(typ)

def tc(t): return f"{int(t // 60):02d}:{t % 60:05.2f}"

def main(P, draft):
    style = json.load(open(os.path.join(P, "style.json")))
    wf = os.path.join(P, "words.cut.json") if os.path.exists(os.path.join(P, "words.cut.json")) else os.path.join(P, "words.json")
    face = json.load(open(os.path.join(P, "face.json"))) if os.path.exists(os.path.join(P, "face.json")) else None
    words = json.load(open(wf)); sc = json.load(open(draft)); out, cues, push, rows, warn = [], [], [], [], []
    for s in sc:
        hit = find(words, s["says"])
        if not hit: warn.append(f'mot introuvable : "{s["says"]}"'); continue
        at = max(0.0, hit[0] + s.get("offset", 0.0)); end = at + s.get("dur", 2.0)
        out.append({"id": s["id"], "layer": s["layer"], "type": s["type"], "at": round(at, 3), "end": round(end, 3), "band": band(s["type"], style, face),
                    "props": {**s.get("props", {}), "taps": s.get("taps")}})
        cues.append({"t": round(at, 3), "kind": "whoosh", "id": s["id"]})
        for tp in s.get("taps", []): cues.append({"t": round(at + tp, 3), "kind": "tap", "id": s["id"]})
        if s.get("push"): push.append({"at": round(at, 3), "dur": 0.9, "amount": min(float(s["push"]), style["motion"]["max_push_in"])})
        rows.append((s["says"], at, f'{s["type"]} ({s["layer"]})', s.get("why", "")))
    out.sort(key=lambda x: x["at"])
    for a, b in zip(out, out[1:]):
        if b["at"] < a["end"] - 1e-6: warn.append(f'chevauchement : {a["id"]} ({tc(a["end"])}) / {b["id"]} ({tc(b["at"])}) : une idée à la fois')
    cues.append({"t": 0.0, "kind": "hit", "id": "hook"})
    total = words[-1]["end"] if words else 0
    cues.append({"t": round(max(0, total - 0.9), 3), "kind": "chime", "id": "close"})
    json.dump({"style": style, "layout": {"W": style["canvas"]["width"], "H": style["canvas"]["height"], "safe": style["safe"],
               "face": json.load(open(os.path.join(P, "face.json"))) if os.path.exists(os.path.join(P, "face.json")) else None},
               "scenes": out}, open(os.path.join(P, "scenes.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(sorted(cues, key=lambda c: c["t"]), open(os.path.join(P, "cues.json"), "w"), indent=1)
    json.dump(push, open(os.path.join(P, "push.json"), "w"), indent=1)
    with open(os.path.join(P, "motion_plan.md"), "w") as f:
        f.write("| SAYS | AT | SCENE | WHY |\n|---|---|---|---|\n")
        for says, at, scn, why in sorted(rows, key=lambda r: r[1]): f.write(f'| "{says}" | {tc(at)} | {scn} | {why} |\n')
    print(open(os.path.join(P, "motion_plan.md")).read())
    for w in warn: print("ATTENTION:", w)

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
