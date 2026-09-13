# Media lab progress

Updated: 2026-09-13 22:10 Europe/Madrid

## Current checkpoint

- Campaign Day 1 started on 2026-09-13.
- Mandatory brand identities are verified natively for Facebook, Instagram and Threads.
- The Samsung SM-S918B is connected and authorized over ADB on Android 16.
- Edits is installed and opens to Projects; import, audio, export and account/destination fidelity are not yet verified.
- Day 1 family `LAB-F12-001` is ready: Anna Atkins cyanotype object-led editorial, 1080×1350 JPEG, exact text overlaid in code.
- API variant A is assigned to Facebook, Instagram and Threads under `PAIR-SINGLE-01`; Android variant B must use a distinct factual piece to avoid duplicate public uploads.
- The production run published Facebook Reel `2026-09-13-re51-reel` at 2026-09-13 21:37 Europe/Madrid and completed at 21:59. The lab held publication while it was active.

## Coverage and volume

- `coverage.json` contains 136 explicit family × network × native-format × route cells.
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

## Pending / blockers

- Commit the isolated workflow, public master and manifest before API submission.
- Probe Instagram API account identity/insights and Threads insights without exposing secrets.
- Open Threads attachment submenu and Facebook/Instagram Story editors to verify polls, location stickers and music.
- Verify Edits account association, import, audio, export, recovered MP4 and both API-EDITS / ANDROID-EDITS routes.
- Create `LAB-F12-001-B` with a different verified topic for the Android matched route.
- Capture baseline metrics for current production posts at comparable ages.
- No recurring automation has been created.

## Next safe actions

1. Publish API variant A through the isolated media-lab workflow after the production collision check.
2. Download the workflow result, reconcile any partial success before retrying, and visually verify all returned URLs.
3. Update the three run records and coverage cells with public IDs/URLs and metric due timestamps.
4. Transfer the eventual Android variant B master to the phone and publish through each native brand composer in spaced windows.

