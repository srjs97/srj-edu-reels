# SRJ EDU daily reel runbook

One reel a day (Suraj, 2026-11-25): slot **19:00** IST. A scheduled task runs this runbook at about 5:40 PM IST
with SLOT = 19:00. It makes one reel from the next row of the topics sheet and schedules it on Instagram, Facebook
and YouTube for **SLOT IST the same day**. (The old 13:00 slot is switched off.)

## Fixed facts

- Topics sheet: `1MOrXV3cl4hrAb-RIIJiHmNtph0NXNv_UfDXciaYKQDU`, tab `Reels Content Vault`.
  Header is row 3: A Topic #, B Category, C Thing A, D Thing B, E Hook / Key Difference, **F Reel Status** (written by this job).
- Buffer org `6b05ccaa5c3cdf93679ea380` (timezone Asia/Kolkata, free plan: max 10 scheduled posts).
  - Instagram `srj_edu_app`: `6b05ce018541f09ecb8d735d`
  - Facebook page: `6b05ce598541f09ecb8d768f`
  - YouTube: `6b05ceac8541f09ecb8d7983`
- Instagram handle shown in reels: `@srj_edu_app`.
- Video URL Buffer fetches: `https://raw.githubusercontent.com/srjs97/srj-edu-reels/main/reels/NNN.mp4`

## Reel format (agreed with Suraj, 2026-11-24)

60 s, 1080x1920, **on-screen text in Malayalam**, NO voiceover, synthesized sound effects + background music,
illustrated background. English names stay as the big titles (`thingA`/`thingB`) with the Malayalam word as
`subA`/`subB`. Since 2026-11-25 the scenes are listed in the spec (explainer style, see step 4).

## Voiceover reels (Suraj, 2026-11-26: he sends script + voiceover WAV; no automatic reels)

- Save his WAV as `voice/NNN.wav` (wav files are git-ignored; keep his upload) and add `"voice": "voice/NNN.wav"` to the spec. The audio then uses his voice
  as the main track with light music (no drums) and soft SFX under it; length follows the audio (can pass 60 s).
- One scene per narration sentence. Find sentence ends with
  `ffmpeg -i voice.wav -af silencedetect=noise=-35dB:d=0.25 -f null -` and match them to the script
  (example: `specs/025x.json`, 17 scenes for 91.5 s). Captions = his Malayalam sentences, split with `capAt`.
- Extra diagram types for physics: `cliff` (mode rest/fall/transform/heights, `meters`), `roll`, `formula`
  (`tokens`, `rows`, `at`), `pendulum`. Per-scene `sfx: [[name, at, gain]]` adds sound effects.
- Schedule for 19:00 IST the same day. Video file `reels/NNN_x.mp4`.

## Steps

1. **Setup**: `apt-get install -y fonts-smc-manjari fonts-noto-core` (Manjari Bold font; PIL needs raqm, which is present).
   Clone this repo.
2. **Slot already done?** If any row's column F already starts with `Scheduled <today's date> <SLOT>`, stop: this
   slot is already scheduled. Report that and do nothing else.
3. **Pick the topic**: read `A4:F1196`. The topic is the first row whose column F is empty. Skip a row only if
   `specs/NNN.json` already exists *and* Buffer already has its posts (then just fill column F).
4. **Write the spec** `specs/NNN.json` (NNN = Topic # zero-padded to 3) in the **explainer style**
   (Suraj, 2026-11-25: "make it like this reference video, without voice"). Copy the shape of
   `specs/001x.json` exactly and read `renderer/explainer.py` for what each visual draws. The look: one idea
   per scene, a big code-drawn diagram in the middle, an English heading on top, a Malayalam subtitle box at the
   bottom, dark purple and light peach scenes alternating, green progress bar, "SRJ EDU APP" badge.
   Rules:
   - Top level: `"style": "explainer"`, `topicNo`, `thingA`, `thingB`, `colA`, `colB` (two contrasting colours), `scenes`.
   - About 10-11 scenes, total `dur` = **60 s** exactly. Scene keys: `dur`, `bg` (`dark`/`light`, alternate them),
     `head` (short ENGLISH CAPS heading), optional `headStyle: "pill"`, `headCol`, `visual`, `captions`,
     optional `capAt` (start second of each caption inside the scene).
   - `captions`: 1-2 short Malayalam subtitle lines per scene (max ~45 characters each). Wrap the key words in
     `**...**` to show them yellow. No emoji inside captions (the font has none).
   - Scene 1 is the thumbnail: `hero` with `vs: true`, both things with `icon` + `name`, heading `<A> VS <B>`,
     and a curiosity caption. It is drawn fully at frame 0.
   - Visual types (pick what fits the topic, use several kinds):
     `hero` (1-3 icons with `label` pills / `name`), `scale` (size comparison, `size` 0-1),
     `bars` (two white cards with value bars 0-1, like "TEMP / ENERGY"), `particles` (beakers or boxes with moving
     particles: `speed`, `liquid`, `dot`, `label`, `steam`, `shape: "box"`, `chip`), `flow` (2-3 icons joined by
     arrows: process or cause and effect), `number` (big counting number + `label`), `remember` (KEY IDEA banner),
     `table` (recap rows: [row label, A, B]), `quiz` (question lines, 2 options, `correct` 0/1; use
     `capAt: [0, dur-2.4]` so the second caption gives the answer at the reveal), `outro` (always last, 5 s,
     captions: `അടുത്തത്: **<next row's A> vs <B>**` and `**SRJ EDU APP** ഫോളോ ചെയ്യൂ!`).
   - Icons: any single emoji that pictures the thing, or `rock:asteroid`, `rock:meteoroids`, `rock:small`.
   - Suggested order: hook (hero vs), the key difference, A explained, B explained, 1-2 diagram scenes that show
     *why* (bars / particles / flow / scale), a remember or number scene, recap table, quiz, outro.
   - Every fact must be correct. Use the sheet's hook (column E) as the core difference. If unsure of a
     number, leave it out rather than guess.
   - The old fixed-template renderer (`video.py`, specs without `"style"`) still works as a fallback.
5. **Render**: `renderer/make_reel.sh specs/NNN.json reels/NNN.mp4` (about 1.5 min; it picks the explainer
   renderer from `"style"`). Then check it: extract a frame from the middle of every scene with ffmpeg and look at them. Fix any text that
   overflows, overlaps or shows boxes instead of letters, and render again.
6. **Publish the file**: commit `specs/NNN.json` and `reels/NNN.mp4`, push to `main`. Confirm
   `curl -sI <raw URL>` returns 200 with `content-length` > 1,000,000.
7. **Schedule on Buffer**, `mode: customScheduled`, `schedulingType: automatic`,
   `dueAt: <today>T<SLOT>:00+05:30`, asset `{ video: { url: <raw URL> } }`:
   - Instagram: `metadata.instagram = { type: "reel", shouldShareToFeed: true }`
   - Facebook: `metadata.facebook = { type: "reel" }`
   - YouTube: `metadata.youtube = { type: "short", title: "<Thing A> vs <Thing B> | <Malayalam hook> #shorts", categoryId: "28" (Science & Technology, Suraj 2026-11-26), madeForKids: false }. Buffer has no YouTube tags field: put keywords + hashtags in the description` (title under 100 characters)
   - Caption (`text`). Engagement style (Suraj, 2026-11-25: reach matters). Instagram and Facebook:
     ```
     <hook_banner from the spec> 😳 <Thing A> ഉം <Thing B> ഉം ഒന്നാണോ?

     <1 line in Malayalam: what they share, then the key difference> 👇
     <short "A = ... | B = ..." line in Malayalam>

     🧠 ക്വിസ്: <quiz question in one line> ഉത്തരം കമന്റ് ചെയ്യൂ 👇

     📌 Save ചെയ്യൂ, പരീക്ഷയ്ക്ക് ഉപകാരപ്പെടും
     📤 ഇത് അറിയാത്ത ഒരു ഫ്രണ്ടിന് Share ചെയ്യൂ
     🔔 Follow @srj_edu_app, ദിവസവും This vs That

     #srjedu #malayalam #thisvsthat #<thingA no spaces> #<thingB no spaces> #<category tag> #science #education #learnmalayalam #keralastudents #psc #gk #reels #explore
     ```
     (Instagram may add `#reelsinstagram`.) YouTube uses the same first four blocks, then
     `🔔 Subscribe ചെയ്യൂ, ദിവസവും This vs That` and `#shorts #srjedu #malayalam #thisvsthat #<thingA> #<thingB> #<category tag> #science #education #keralastudents #psc #gk`.
8. **Record**: write `Scheduled YYYY-MM-DD <SLOT>` into column F of the row (e.g. `Scheduled 2026-11-26 19:00`).
9. **Report**: if any step fails, stop, leave column F empty, and say exactly which step failed and why.

**Buffer limits** (free plan): at most **10 scheduled posts in the whole org at a time**, and at most 2 YouTube posts per day.
Other SRJ EDU work (PSC quiz posts) shares the same Buffer, so before step 7 count the org's `scheduled` posts
(list_posts, status scheduled). The reel needs 3 free slots. If fewer are free, schedule in this order until full:
**YouTube first** (Suraj: YouTube carries only these reels), then Instagram, then Facebook. Never delete or move other posts to make room. Write what was scheduled in column F,
e.g. `Scheduled YYYY-MM-DD 18:30 (YT+IG; FB skipped: Buffer 10-post limit)`, and say so clearly in the report so
Suraj can add the rest by hand.

Never post with `shareNow`. Never schedule more than one day ahead (the free plan holds only 10 posts).
