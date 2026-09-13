# Visual QA gate — mandatory before every lab publication

Effective 2026-09-14. This is a hard stop, not a score to be averaged away.

Before any API or Android-native public submission, including TikTok:

1. Build the exact final platform composition: actual crop, text, place label, music label, poll/sticker and platform controls.
2. Capture the complete preview at its intended platform aspect ratio.
3. Assign an independent visual-verification agent. It must return an explicit `PASS` for that exact asset, platform, route and preview.
4. Record the preview path, agent verdict and checklist results in the run record before submission.

The agent checks that the audience sees an autonomous editorial item (never lab metacontent), all text is readable at phone size and inside the frame/safe area, spelling and accents are correct, contrast is sufficient, no text or essential image is covered, and stickers/polls sit wholly in intentional empty space. For video it also checks the final cover and audible preview when applicable.

`FAIL`, absent evidence, a draft without native elements, or a preview that omits any final overlay blocks publication. Correct and rerun the independent review; do not substitute a self-review.
