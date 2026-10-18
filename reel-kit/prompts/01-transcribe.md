Pass 01: Transcribe.
- Transcribe my clip word by word, with a start and end time for every word. Save it as words.json.
- List every pause longer than 0.4s and every stumble or repeated take, with timestamps. Don't cut anything yet.
- Show me the transcript as a table so I can fix any misheard words.

THEN (Tighten the cut):
Cut the pauses and stumbles you listed. Keep about 0.1s of breath on each side of every cut. Re-time words.json to the new cut and render a rough preview.

DONE WHEN: you have words.json, every word is spelled right, and the rough cut has no dead air. Then type "next".
IF STUCK: if Claude can't download a speech model, use a Whisper or Parakeet model from the sherpa-onnx releases on GitHub. Both give word-level timings.
