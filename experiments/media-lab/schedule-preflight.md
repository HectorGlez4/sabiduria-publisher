# Scheduled media-lab preflight

> **Reparto vigente desde 2026-09-14:** Codex (automatización `media-lab-hasta-1-octubre`) solo genera imágenes desde `encargos/`. Claude encarga, revisa, hace QA y publica por teléfono y API desde la tarea programada `sabiduria-media-lab` (10:40, 15:40 y 20:40). Diseño: `docs/superpowers/specs/2026-09-14-media-lab-chatgpt-claude-design.md`. Todo pasa por `experiments/media-lab/lab.py`.

Checked: 2026-09-13 23:21 Europe/Madrid

## Schedule

- Automation: `media-lab-hasta-1-octubre`
- Status: active
- Frequency: daily at 10:10, 15:10 and 20:10 Europe/Madrid
- First window: 2026-09-14 10:10
- Last window: 2026-10-01 20:10
- Total scheduled windows: 54 across 18 days
- Safety limit: at most one public coverage cell per execution, always after a live production-collision check

## Preflight result

| Dependency | Status | Evidence / action |
|---|---|---|
| Codex heartbeat | Ready | Active automation TOML exists and targets this thread. |
| Mac power | Ready while connected to AC | Mac was on AC power. Temporary launchd job `com.sabiduria.medialab.keepawake` runs `caffeinate -s` through the campaign window; the display may sleep and the assertion applies only while AC remains connected. |
| Internet | Ready | GitHub returned HTTP 200, GitHub API operations succeeded, Meta Graph responds and raw asset hosting is reachable. Every run still performs its normal live check. |
| GitHub credentials | Ready | `gh auth status` validated `HectorGlez4`; token includes `repo` and `workflow`. All five required Meta secret names are present. No secret values were exposed. |
| Git worktree | Synchronized | Pending media-lab commits were pushed to `origin/main`; three pre-existing untracked docs remain untouched. |
| Samsung phone | Ready now | SM-S918B, Android 16, ADB authorized, awake, unlocked, USB-powered, 93% during the check. |
| Facebook | Brand verified | Native navigation reached `Sabiduria De Bolsillo`. |
| Instagram | Corrected and verified | Preflight found personal `hec.gonzlez` active; switched back to brand `@sabiduriabolsillo` and verified the 5,272-follower brand profile. |
| Threads | Brand verified | `@sabiduriabolsillo` visible. |
| Native apps | Ready now | Facebook, Instagram, Threads and Edits are installed at the recorded versions. |

## Conditions needed during the vacation

1. Leave the Mac connected to AC power, logged in, with Codex running and stable internet access.
2. Do not quit this Codex task or pause/delete the automation.
3. Leave the Samsung connected by USB, with USB debugging authorization retained. Android-native publication additionally requires the phone to be unlockable without user intervention; if it locks securely, the automation must skip Android rather than guess or publish blindly.
4. Keep Facebook, Instagram, Threads and Edits signed in. Instagram must remain on `@sabiduriabolsillo`; every native run still verifies the visible identity immediately before Share.
5. Do not revoke the existing Meta/GitHub tokens or change account permissions during the campaign.
6. Keep reliable access to `github.com` and `api.github.com`. If connectivity drops again, GitHub Actions API publishing, production-collision inspection and pushing lab records pause; native Android and offline creation may still proceed.
7. Keep enough disk space and prevent system restarts or automatic OS/app updates during unattended windows when possible.

## Execution behavior when a dependency fails

- Phone absent, locked or wrong account: skip the Android cell, record the blocker and continue safe creation/metrics/API work.
- GitHub unavailable: do not dispatch an API publication without the normal collision check; retry in a later window and continue local asset work.
- Meta/platform error: never retry blindly after an ambiguous submission. Query for the resulting post first to avoid duplicates.
- Production upload active or too recent: hold the lab publication and use the window for preparation or measurement.
