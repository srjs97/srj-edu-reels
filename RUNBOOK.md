# SRJ EDU daily reel runbook

Two reels a day (Suraj, 2026-11-25): slots **13:00** and **18:30** IST. Two scheduled tasks run this runbook,
one at about 11:45 AM IST for the 13:00 slot and one at about 5:10 PM IST for the 18:30 slot. Each run is told
its SLOT. It makes one reel from the next row of the topics sheet and schedules it on Instagram, Facebook and
YouTube for **SLOT IST the same day**.

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
`subA`/`subB`. Scene order is fixed by `renderer/video.py`: hook, A vs B, B card, A card, recap, quiz,
bonus, fun fact, outro.

## Steps

1. **Setup**: `apt-get install -y fonts-smc-manjari fonts-noto-core` (Manjari Bold font; PIL needs raqm, which is present).
   Clone this repo.
2. **Slot already done?** If any row's column F already starts with `Scheduled <today's date> <SLOT>`, stop: this
   slot is already scheduled. Report that and do nothing else.
3. **Pick the topic**: read `A4:F1196`. The topic is the first row whose column F is empty. Skip a row only if
   `specs/NNN.json` already exists *and* Buffer already has its posts (then just fill column F).
4. **Write the spec** `specs/NNN.json` (NNN = Topic # zero-padded to 3). Copy the shape of `specs/002.json`
   exactly. Rules:
   - `topicNo` = Topic #, `tag` = `THIS vs THAT #<Topic #>`.
   - All text natural, simple Malayalam that a school student understands. Keep each line short
     (bullets about 30 Malayalam characters max; the renderer shrinks text that is too wide, but short reads better).
   - 5 bullets per card: 3 white facts, 1 grey bracket aside (size 40), 1 yellow key number/size line.
   - Every fact must be correct. Use the sheet's hook (column E) as the core difference. If unsure of a
     number, leave it out rather than guess.
   - `quiz.correct` is `"A"` or `"B"`; `quiz.answer` is that thing's English name in caps with `!`.
   - `outro3` names the next row's topic: `അടുത്തത്: <Thing A> vs <Thing B>`.
   - `emojiA` / `emojiB`: one emoji each that pictures the thing (used as the big illustration).
   - `"light": true` always (Suraj chose a light yellow background, 2026-11-25). Text colours are
     converted automatically; keep using the normal white/yellow/grey values from the example.
   - `colA` / `colB`: two contrasting bright colours (they are darkened automatically for the light background).
   - `theme`: `"space"` for category `Astronomy & Space`. For every other category use
     `{"emojis": [5 emojis for the category]}` (the light yellow background is applied automatically).
5. **Render**: `renderer/make_reel.sh specs/NNN.json reels/NNN.mp4` (about 2.5 min). Then check it:
   extract frames at 3.5, 7.5, 12, 22, 31, 39, 49, 55, 59 s with ffmpeg and look at them. Fix any text that
   overflows, overlaps or shows boxes instead of letters, and render again.
6. **Publish the file**: commit `specs/NNN.json` and `reels/NNN.mp4`, push to `main`. Confirm
   `curl -sI <raw URL>` returns 200 with `content-length` > 1,000,000.
7. **Schedule on Buffer**, `mode: customScheduled`, `schedulingType: automatic`,
   `dueAt: <today>T<SLOT>:00+05:30`, asset `{ video: { url: <raw URL> } }`:
   - Instagram: `metadata.instagram = { type: "reel", shouldShareToFeed: true }`
   - Facebook: `metadata.facebook = { type: "reel" }`
   - YouTube: `metadata.youtube = { type: "short", title: "<Thing A> vs <Thing B> | <Malayalam hook> #shorts", categoryId: "27", madeForKids: false }` (title under 100 characters)
   - Caption (`text`), same for all three:
     ```
     <Thing A> vs <Thing B> 🤔
     <2 lines in Malayalam: the key difference>

     ക്വിസ്: <quiz question in one line> 👇 ഉത്തരം കമന്റ് ചെയ്യൂ!

     Follow @srj_edu_app for daily This vs That 🔥
     #srjedu #malayalam #thisvsthat #<thingA no spaces> #<thingB no spaces> #<category tag> #science #education #learnmalayalam #reels
     ```
8. **Record**: write `Scheduled YYYY-MM-DD <SLOT>` into column F of the row (e.g. `Scheduled 2026-11-26 13:00`).
9. **Report**: if any step fails, stop, leave column F empty, and say exactly which step failed and why.

**Buffer limits** (free plan): at most **10 scheduled posts in the whole org at a time**, and at most 2 YouTube posts per day (exactly the 2 reels).
Other SRJ EDU work (PSC quiz posts) shares the same Buffer, so before step 7 count the org's `scheduled` posts
(list_posts, status scheduled). The reel needs 3 free slots. If fewer are free, schedule in this order until full:
**YouTube first** (Suraj: YouTube carries only these reels), then Instagram, then Facebook. Never delete or move other posts to make room. Write what was scheduled in column F,
e.g. `Scheduled YYYY-MM-DD 18:30 (YT+IG; FB skipped: Buffer 10-post limit)`, and say so clearly in the report so
Suraj can add the rest by hand.

Never post with `shareNow`. Never schedule more than one day ahead (the free plan holds only 10 posts).
