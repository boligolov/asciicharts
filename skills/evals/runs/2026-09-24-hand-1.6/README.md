# Hand-drawn eval run 1.6, 2026-09-24

The raw replies of the run summarised in `../../README.md` (*Hand-drawn results, 1.6*), laid out as
`<model>/<eval>/<with_skill|without_skill>/`: `reply.md` is the reply exactly as the agent saved it,
`grading.json` is what `hand_grade.py` made of it.

- `haiku/` — the weaker model on all eleven prompts of `hand_evals.json` (the seven of run 1.5 and the
  four harder ones), with and without the skill.
- `strong/` — the model of run 1.5 on the four harder prompts, with and without the skill.

Every agent was independent and was told it could not run code; with the skill it read
`skills/asciicharts/` first, without it read nothing. One run per configuration.

Worth reading beyond the numbers: the two Haiku stacked-bar replies (a zero axis that moves one column in
one row — the mistake the new self-check item is about), the strong model's stacked reply with the skill
(it noticed that the renderer's own stacked bars draw no zero line, and drew `¦` because the prompt asked
for one), and the strong model's line chart with the skill (the renderer's own row labels, 64 … 29).
