# CLOUD

## Montage vidéo (reels)

Pour tout montage de reel / vidéo talking-head : utiliser le skill `/reel-edit` (`.claude/skills/reel-edit/SKILL.md`).
Méthode "5-Pass Reel Edit Kit" : 01 Transcribe -> 02 Cut-out -> 03 Captions -> 04 Motion -> 05 Sound. Une passe à la fois, attendre "next".

- Outils, scripts, templates : `reel-kit/` (lire `reel-kit/README.md`).
- Style de référence : `reel-kit/Reel-Style-Rules.md` + `reel-kit/style.json` (source de vérité, à modifier ici pour changer de look).
- Projets de montage : `projects/<nom>/` (non versionnés).
- Export final : 1080x1920, 30 fps, H.264, -14 LUFS, pics < -1 dB. Safe area : haut 220 px, bas 380 px, droite 140 px.
- Le dossier `reel-kit/` vient du PDF "5-Pass Reel Edit Kit" (@zeeuiux), adapté à Claude Code en local dans le repo.

## Voix de l'utilisateur (textes, légendes, scripts)

- Phrases courtes, une idée par ligne, oral, cash, tutoiement, zéro emoji. Scène vécue d'abord, leçon en une ligne sèche.
- Le texte de l'utilisateur est TOUJOURS la base : corrections au scalpel, jamais de réécriture par-dessus.
- N'invente JAMAIS un fait de sa vie : poser la question ou marquer [À VALIDER].
- Les sous-titres montrent ses mots tels que dits.
