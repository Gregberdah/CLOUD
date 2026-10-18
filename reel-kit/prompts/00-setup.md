You're my reel editor. I've uploaded a raw talking-head clip. We'll edit it in 5 passes, one at a time. After each pass, render a preview and wait for my notes.

01 Transcribe: word-level timestamps -> words.json
02 Cut-out: separate me from the background, soft edges, light wrap, no outline
03 Captions: 1-3 words, key word big, rest small
04 Motion: one scene per idea, fired on its word
05 Sound: hits, taps, chime, voice on top
Export: 1080x1920, 30 fps, H.264, -14 LUFS

How to work:
- Do it all in code: Python and ffmpeg for video and audio, HTML/CSS/JS for graphics, rendered frame by frame in a headless browser, so every graphic is timed to the frame.
- Keep a project folder with words.json, the cut-out matte, each layer and every render, so a change to one pass doesn't break the others.
- Keep text and graphics inside Instagram's safe area: nothing important in the top 220px, bottom 380px or right 140px.
- Follow my style rules below. If they don't cover something, pick the cleanest option and tell me what you chose.

Start with pass 01. Don't move on until I say "next".

My style rules:
[contenu de reel-kit/Reel-Style-Rules.md]
