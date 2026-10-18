#!/usr/bin/env python3
"""Passe 03 : plan de sous-titres -> captions.json + captions_plan.md (mots-clés à valider AVANT le rendu).

Usage: captions.py <projet_dir> [--keywords keywords.json]
- 1 à 3 mots par sous-titre, chacun apparaît sur son mot, tenu >= 0.4 s.
- Un mot-clé par phrase (le plus "porteur" : mot long, hors mots vides). Surcharge : keywords.json
  = {"<n° de phrase>": <index du mot dans words.json>}.
- Si scenes.json existe (après la passe 04), les sous-titres évitent les scènes à l'écran : relance captions.py puis re-rends les calques captions.
- Jamais sur le visage : zones calculées depuis face.json (jeu au-dessus de la tête sinon sous le menton).
"""
import argparse, json, os, re, sys

STOP = set("""le la les un une des de du d l et ou mais donc or ni car que qui quoi dont où ce cet cette ces c ça ca cela
je tu il elle on nous vous ils elles me te se lui leur leurs mon ton son ma ta sa mes tes ses notre votre nos vos
à a au aux en dans sur sous avec sans pour par chez est es suis sommes êtes sont été être avoir ai as avons avez ont
ne pas plus pas n s j t m y très si comme tout tous toute toutes bien aussi alors puis quand qu
the a an and or but of to in on at for with by is are was be been it its this that these those i you he she we they
me my your our their not no so as if from do does did have has had will would can could just very more most""".split())

def norm(w): return re.sub(r"[^\w]", "", w.lower())
def sentences(words):
    out, cur = [], []
    for k, w in enumerate(words):
        cur.append(w)
        gap = words[k + 1]["start"] - w["end"] if k + 1 < len(words) else 9
        if re.search(r"[.!?…]$", w["w"]) or gap > 0.7:
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def pick_key(sent):
    best, score = None, -1
    for w in sent:
        n = norm(w["w"]); s = 0 if n in STOP else len(n) + (2 if w is sent[-1] else 0)
        if s > score: best, score = w, s
    return best

def chunk(sent, max_words=3):
    out, cur = [], []
    for w in sent:
        cur.append(w)
        if len(cur) == max_words or re.search(r"[,;:.!?…]$", w["w"]): out.append(cur); cur = []
    if cur:
        if out and len(cur) == 1 and len(out[-1]) < max_words: out[-1] += cur
        else: out.append(cur)
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--keywords")
    a = ap.parse_args(); P = a.project
    style = json.load(open(os.path.join(P, "style.json"))); cap = style["captions"]
    wf = os.path.join(P, "words.cut.json") if os.path.exists(os.path.join(P, "words.cut.json")) else os.path.join(P, "words.json")
    words = json.load(open(wf))
    over = json.load(open(a.keywords)) if a.keywords else {}
    face = json.load(open(os.path.join(P, "face.json"))) if os.path.exists(os.path.join(P, "face.json")) else None
    W, H, S = style["canvas"]["width"], style["canvas"]["height"], style["safe"]
    items, plan = [], []
    for si, sent in enumerate(sentences(words)):
        key = next((w for w in sent if w["i"] == over[str(si)]), None) if str(si) in over else pick_key(sent)
        plan.append((si, sent[0]["start"], " ".join(w["w"] for w in sent), key["w"] if key else "-", key["i"] if key else -1))
        for ch in chunk(sent, cap["max_words"]):
            st = ch[0]["start"]; en = max(ch[-1]["end"] + 0.05, st + cap["min_hold"])
            items.append({"sentence": si, "start": round(st, 3), "end": round(en, 3),
                          "words": [{"t": w["w"], "at": w["start"], "key": bool(key and w["i"] == key["i"])} for w in ch]})
    for k in range(len(items) - 1):                       # pas de chevauchement entre sous-titres
        items[k]["end"] = round(min(items[k]["end"], items[k + 1]["start"]), 3)
    lay = {"W": W, "H": H, "safe": S, "face": face}
    sf = os.path.join(P, "scenes.json")
    scenes = [{k: x.get(k) for k in ("at", "end", "type", "layer", "band")} for x in json.load(open(sf))["scenes"]] if os.path.exists(sf) else []
    json.dump({"layout": lay, "items": items, "style": style, "scenes": scenes}, open(os.path.join(P, "captions.json"), "w"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(P, "captions_plan.md"), "w") as f:
        f.write("# Mots-clés choisis (un par phrase). Dis-moi lesquels changer.\n\n| phrase | à | phrase entière | mot-clé | index |\n|---|---|---|---|---|\n")
        for si, t, txt, kw, ki in plan: f.write(f"| {si} | {t:05.2f}s | {txt} | **{kw}** | {ki} |\n")
    short = [i for i in items if i["end"] - i["start"] < cap["min_hold"] - 1e-6]
    print(f"{len(items)} sous-titres, {len(plan)} phrases -> captions.json, captions_plan.md")
    if short: print(f"ATTENTION : {len(short)} sous-titres tenus < {cap['min_hold']}s (débit très rapide) : à regrouper.")
    if not face: print("Note : pas de face.json (lance face.py après la passe 02) : placement par défaut.")

if __name__ == "__main__":
    main()
