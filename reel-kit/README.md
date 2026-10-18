# Reel Kit : le montage en 5 passes

Clip brut dedans, reel fini dehors : sous-titres, cut-out, motion graphics, son. Tout en code, une passe à la fois.
Basé sur le "5-Pass Reel Edit Kit" (@zeeuiux), monté ici avec Claude Code dans ce repo.

## Utiliser

1. Dépose ton clip brut (1080p, < 30 Mo, air mort coupé au début et à la fin, du jeu au-dessus de la tête pour le texte).
2. Dis à Claude : `/reel-edit` + le chemin du clip. Le skill charge toute la méthode et tes règles de style.
3. Valide chaque passe en tapant `next`. Entre deux, donne des notes de réal (`prompts/06-director-notes.md`).
4. Avant de poster : `prompts/07-before-you-post.md` (téléphone, son on puis off, cover, -14 LUFS).

Les prompts d'origine sont dans `prompts/` si tu veux travailler hors Claude Code (claude.ai, chat) : `00-setup.md` d'abord, puis 01 à 05.

## Les 5 passes

| Passe | Ce qui se passe | Script | Sortie |
|---|---|---|---|
| 01 Transcribe | mots + timings, pauses > 0.4 s, tics, reprises, puis coupe serrée (0.1 s de souffle) | `transcribe.py`, `cut.py` | `words.json`, `words.cut.json`, `base.mp4` |
| 02 Cut-out | détourage image par image, bords doux, trous remplis, aucun contour | `matte.py`, `face.py` | `matte.mkv`, `face.json`, `renders/check_*.mp4` |
| 03 Captions | 1-3 mots, un mot-clé gros par phrase, tenu >= 0.4 s, hors visage | `captions.py`, `render_html.py` | `captions.json`, calques PNG |
| 04 Motion | une scène par idée, déclenchée sur son mot, derrière ou devant toi | `motion_plan.py`, `render_html.py` | `scenes.json`, `cues.json`, `push.json` |
| 05 Sound | hit, tap, whoosh, chime, voix au-dessus, master -14 LUFS | `composite.py`, `sound.py`, `final_check.py` | `renders/final.mp4`, cover |

Contrôles : `safe_check.py` (safe area Instagram), `final_check.py` (1080x1920, 30 fps, H.264, LUFS, pics).

## Arborescence

```
reel-kit/
  Reel-Style-Rules.md   style en clair (source de vérité humaine)
  style.json            même style, lu par les scripts
  prompts/              les prompts du PDF (setup, 5 passes, notes de réal, checklist)
  scripts/              outils (Python + ffmpeg + Chromium headless)
  templates/            captions_layer.html, motion_layer.html, reel.js
  assets/fonts/         Instrument Serif Italic, Inter, DM Mono (OFL)
  assets/sfx/           tes WAV perso : hit, tap, whoosh, chime (remplacent les sons générés)
  models/               téléchargés par setup_env.sh (non versionnés)
projects/<nom>/         un dossier par reel : raw, words, matte, layers/, renders/ (non versionné)
```

## Démarrage rapide (à la main)

```bash
bash reel-kit/scripts/setup_env.sh                       # une fois (déjà lancé au démarrage de session)
bash reel-kit/scripts/new_project.sh mon-reel clip.mp4
python3 reel-kit/scripts/transcribe.py projects/mon-reel --lang fr
```

## Changer de look

Édite `Reel-Style-Rules.md` et `style.json` (couleurs, polices, tailles, safe area). Rien d'autre.
Polices : ajoute le fichier dans `assets/fonts/` et déclare-le dans `style.json`.

## Limites et pièges

- Matting sur CPU : ~3-4 images/s. 30 s de clip = quelques minutes. Bords durs ou qui scintillent : `matte.py --ratio 0.5`.
- Transcription : Whisper (faster-whisper) si Hugging Face répond, sinon Parakeet v3 multilingue (GitHub sherpa-onnx). Les fins de mots Parakeet sont estimées (il ne donne que les débuts) : relis le tableau.
- Les passes sont indépendantes : changer les sous-titres ne refait pas le détourage. Pour ne re-rendre qu'une plage : `render_html.py ... --from 4 --to 7`, puis `composite.py`.
- Les sous-titres évitent les scènes motion à l'écran (relance `captions.py` après `motion_plan.py`). Si aucune zone n'est libre, le sous-titre est masqué et signalé (`NOTE:`).
- `face.py` estime la tête depuis le matte : prudent, inclut le cou. Peu de jeu au-dessus (< 340 px) : le texte passe sous le menton.
