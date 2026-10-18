# Reel Style Rules

Source de vérité du look. Claude les suit à chaque passe.
Pour changer de marque : édite ce fichier, rien d'autre. Les scripts lisent `style.json`.

## Canvas
- 1080x1920, 30 fps.
- Safe area : rien d'important dans les 220px du haut, les 380px du bas et les 140px de droite.

## Type
- Mots-clés : serif italique (Instrument Serif Italic), gros, un par phrase.
- Mots de support : sans propre (Inter), semibold, petit.
- Labels et UI : mono (DM Mono), majuscules, tracking large.
- 3 mots max à l'écran. Jamais sur mon visage.
- Polices dans `reel-kit/assets/fonts/`. Max 2 polices visibles à l'écran en même temps.

## Color
- Fond : quasi-noir #09090A avec une lueur chaude douce.
- Dégradé d'accent : #FFDDCC -> #F6BDD8 -> #C9B9FF.
- Texte : #F5F5F4. Texte atténué : #A3A3AB.

## Motion
- Entrée rapide (0.2 à 0.35 s), maintien, sortie propre. Ease-out sur les entrées.
- Une idée par scène. Chaque scène part sur son mot déclencheur.
- Texte derrière moi (cut-out) pour les hooks et les gros mots.
- Push-ins discrets (6 % max) sur les emphases. Aucun zoom qui tremble.

## Sound
- Hit sur le hook, tap sur les clics, whoosh sur les changements de scène, chime pour fermer.
- Voix toujours au-dessus. Master à -14 LUFS, pics sous -1 dB.
- Mes propres SFX (WAV) dans `reel-kit/assets/sfx/` : ils remplacent les sons générés.

## Don't
- Pas de contour blanc type sticker autour de moi.
- Pas d'emoji dans les sous-titres, pas d'arc-en-ciel, 2 polices max à l'écran.

## Langue (ajout perso)
- Les sous-titres suivent la langue du clip. Si le clip est en français : accents et ponctuation FR corrects, tutoiement conservé tel que dit.
- On ne reformule jamais mes mots à l'écran. Ce que je dis, c'est ce qui s'affiche. Une correction passe par le tableau de transcription, pas par une réécriture.
