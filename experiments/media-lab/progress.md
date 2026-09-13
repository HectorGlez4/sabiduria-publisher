# Media lab progress

Updated: 2026-09-13 23:21 Europe/Madrid

## Current checkpoint

- Campaign Day 1 started on 2026-09-13.
- Temporary Codex heartbeat `media-lab-hasta-1-octubre` is active at 10:10, 15:10 and 20:10 Europe/Madrid each day through 2026-10-01 inclusive. It may publish at most one coverage cell per execution after a live collision check.
- Schedule preflight is recorded in `schedule-preflight.md`: phone and Meta connectivity passed; Instagram was switched back from personal `hec.gonzlez` to brand `@sabiduriabolsillo`; GitHub web/API connectivity, authentication, Actions access and required secret names were revalidated at 23:21 and pending lab commits were pushed.
- Mandatory brand identities are verified natively for Facebook, Instagram and Threads.
- The Samsung SM-S918B is connected and authorized over ADB on Android 16.
- Edits is installed and opens to Projects. Still-image import, the audio picker, local export and handoff to Instagram Reel plus Facebook brand Reel/Story composers are verified; adding licensed audio and producing a publishable export remain unverified.
- Day 1 family `LAB-F12-001` is live on Facebook, Instagram and Threads through API-MASTER. All three native displays were visually verified.
- API variant A uses the Anna Atkins cyanotype object-led editorial. Canonical URLs are stored in the run records and `coverage.json`.
- Android variant B uses a distinct Maria Sibylla Merian factual piece under `PAIR-SINGLE-01`; it is rendered, transferred to the phone and ready for a later collision-checked window.
- The production run published Facebook Reel `2026-09-13-re51-reel` at 2026-09-13 21:37 Europe/Madrid and completed at 21:59. The lab held publication while it was active, then released at 22:01–22:02.

## Coverage and volume

- `coverage.json` contains 136 explicit family × network × native-format × route cells.
- Current statuses: 3 published, 7 ready and 126 planned. Draft-only capability probes do not count as publications.
- A conservative first-wave limit of three additional lab releases per day yields 42 cells in 14 days.
- 94 cells therefore spill beyond Day 14 unless capability probes mark them unsupported or the user accepts a substantially higher audience load. They remain explicit and are not counted as covered.
- The normal queue is unusually dense, and the Threads lane is hourly; exact neighboring production posts must be recorded for every lab release.

## Completed evidence

- Android launch/profile/composer evidence is stored locally under `evidence/android/` and excluded from git because screenshots include personal-account context.
- Facebook brand: Sabiduria De Bolsillo, 27,875 API-reported followers, Page published, New Pages Experience, valid non-expiring Page token, required publishing and insights scopes present.
- Instagram brand: `@sabiduriabolsillo`, 5,272 followers observed natively; account switched from personal profile to brand profile.
- Threads brand: `@sabiduriabolsillo`; native composer shows gallery, GIF, sticker, music and attachments.
- Edits package: `com.instagram.basel` 445.0.0.46.83; project screen opens successfully.
- Image generation: one included generation accepted on first attempt; zero incremental spend.
- Final master SHA-256: `32cae1642cdeb01e7b6194e7630f045f9d14c96a77527241785715884358d76b`.
- Live Day 1 URLs: Facebook `https://www.facebook.com/874327782058550/posts/1094273873397272`; Instagram `https://www.instagram.com/p/DdPX1J9jwt1/`; Threads `https://www.threads.com/@sabiduriabolsillo/post/DdPX21Rj-ie`.
- API active publishing time: Facebook 5.332 s; Instagram 13.637 s; Threads 12.749 s. All succeeded on the first submission attempt.
- Read-only Graph verification confirmed exact captions/media, Facebook `is_published=true` and `is_hidden=false`, and canonical Instagram/Threads permalinks.
- Threads native attachment menu exposes Text, Quote, Poll and Location.
- Merian Android master SHA-256: `ced93d7c407e25fba0c6337dff9b8aee01a25f535f41fbae9aaf11c586e17c41`; first generation was rejected for an implausible metallic pupa, then repaired once.
- Edits import/export probe succeeded: the 4:5 master imported and exported as a 3.03 s, 1080×1920, 30 fps HEVC MP4. It is not publishable because it is too short, letterboxed and unverified for API codec compatibility.
- Edits destination probe confirmed Instagram Reel handoff and a Facebook chooser naming `Sabiduria De Bolsillo` with both Reel and Story destinations. Neither route was published.
- Facebook brand Story editor exposes Add Yours, Location, Music, Poll, Question and Link stickers. Instagram brand Story creation exposes Templates, Music, Collage, multi-select, Location, Question, Multi-option Poll, Slider and Link. Evidence was captured and both drafts were exited without sharing.
- `storyboards.md` now defines all twelve required low-cost format hypotheses, their source and `do_not_use` gates, platform adaptations and current readiness. F01, F03, F05, F08, F10 and F12 are the initial finished-prototype slate; F12 is already live.
- `findings.md` records the Day 1 free workflow and defers any paid round until repeatability, publishable audio/motion and mature audience measurements expose a measurable gap.
- Anna API and Merian Android Story masters are rendered at 1080×1920, visually reviewed and recorded as ready for Facebook and Instagram. Both masters are also transferred to the phone; publication remains held for spaced windows.
- Day 2 I01 has a reviewed publishable fictional-presenter prototype about the Lamarr–Antheil patent. The image visibly says `PRESENTADORA FICTICIA`; its paired object-led candidate was rejected from public use because generated instrument labels failed the evidence/typography gate.

## Pending / blockers

- Probe Instagram API account identity/insights and Threads insights without exposing secrets.
- Verify Edits account association, licensed audio, publishable export and both API-EDITS / ANDROID-EDITS routes.
- Add owned/licensed audio and create a publishable 8–15 second Edits export; current silent export is only technical evidence.
- Capture baseline metrics for current production posts at comparable ages.
- The temporary automation must stop after its final 2026-10-01 window. It does not authorize paid services, production-queue edits, duplicate uploads or publication to an ambiguous/personal account.

## Next safe actions

1. On 2026-09-14, check active production runs and publish Android variant B once per mandatory network in safe, possibly staggered windows.
2. Capture the first Day 1 24-hour metrics at the exact due times in `coverage.json`; no recurring job is active.
3. Release the prepared API/Android Story pairs only in observable, spaced windows; capture a first snapshot around six hours and another before expiry.
4. Start Day 2 generated-person I01 comparison while preserving the Merian image as the Android route match for the Day 1 family.
