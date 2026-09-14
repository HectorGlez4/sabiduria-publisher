# Sabiduría media lab: creation and publishing benchmark

> **Reparto vigente desde 2026-09-14:** Codex (automatización `media-lab-hasta-1-octubre`) solo genera imágenes desde `encargos/`. Claude encarga, revisa, hace QA y publica por teléfono y API desde la tarea programada `sabiduria-media-lab` (10:40, 15:40 y 20:40). Diseño: `docs/superpowers/specs/2026-09-14-media-lab-chatgpt-claude-design.md`. Todo pasa por `experiments/media-lab/lab.py`.

Prepared 2026-09-13. Status: planned, not executed. The user will start testing in a new session. Read [TWO-WEEK-CAMPAIGN.md](TWO-WEEK-CAMPAIGN.md) first: the latest scope adds extensive image variations, Facebook-first trivia/carousels/audio/location formats and actual publishing across all existing brand targets. That campaign takes precedence where this original benchmark differs; the tool comparisons and paid-round framework below still apply.

## Objective and scope

Find engaging new Spanish-language formats inspired by the existing verified corpus, and determine which creation and publishing workflows offer the best quality, elapsed time, human effort and repeatability. Explore broadly with free/local/included options first. Use a second, separately budgeted paid round to address demonstrated weaknesses.

Do not equate more tools or more generated pixels with better content. Produce a portfolio of winners: fastest acceptable, strongest visual quality, strongest voice, easiest phone workflow, best repeatable workflow, and best audience response.

## Isolation from production

- All briefs, experiments, exports, scores and post records live under `experiments/media-lab/`. Use IDs such as `LAB-R1-001`, never production date/slot IDs.
- Read existing content as inspiration. Do not write to `content/queue`, `content/published`, production assets, RSS output or `.github/workflows`; do not dispatch production publishing or enqueue scripts.
- Do not invoke `python -m src.publish --due`. Its current dry-run does not cover every video/story render and is not this lab's isolation mechanism.
- Use a separate checkout/branch for experimental code where practical. Test generation scripts must take explicit output paths inside the lab and must not publish as a side effect.
- Keep provider/model downloads, large binaries and private account information out of commits. Store original exported media locally with hashes and a backup location; do not rely on app draft storage alone.
- The user requests actual public publishing across existing Sabiduría targets. Resolve the correct brand accounts and use the campaign's bounded release plan; ask only about missing or ambiguous destinations. Keep production queues unchanged and record nearby production posts because audience exposure is shared.
- Do not activate recurring tasks. Production publishing cadence stays unchanged. A new session should complete offline work while destination selection is pending.

## Known starting state — recheck at launch

Apple Silicon Mac, 32 GiB RAM; Python, Pillow, uv, ADB, FFmpeg and ffprobe available. scrcpy 4.1 was installed; Homebrew also upgraded FFmpeg to 9.0.1. A small H.264 encoder smoke check passed, not the full renderer suite. Kokoro and its dependencies were not installed in the inspected Python environment.

The connected phone reported Samsung **SM-S918B / Android 16** and authorized ADB. Although called a Galaxy Note in conversation, use the detected identifier. scrcpy was started but screen control was not verified: the computer-use app inventory did not expose it and selecting its executable path failed. Resolve this before claiming phone automation. Edits installation/functionality and export behavior remain unverified. Follow the phone pilot for context, using the current session's supported UI tools and their instructions.

Connected services, free balances, plans and content rights are unverified until checked in each account. Installing a plugin does not create a free service allowance.

## Content seeds

| Seed | Existing JSON in `content/published/` | New angles to explore |
|---|---|---|
| Braille | `2026-08-28-manana.json` | Six dots as a puzzle; hands demonstrating a system; why useful inventions meet resistance |
| Séneca | `2026-08-17-tarde.json` | A modern situation followed by the original passage; quote versus interpretation |
| Merian | `2026-09-05-extra51.json` | Follow a caterpillar across a plate; the relationships hidden in an illustration |
| Sócrates | `2026-08-20-tarde.json` | A familiar quotation put on trial; what the source actually supports |
| Anna Atkins | `2026-09-07-extra84.json` | Reveal an image in blue; a visual story told through an original artifact |
| Hedy Lamarr | `2026-09-07-extra88.json` | A patent as a mystery object; distinguish the invention from exaggerated modern claims |

These are hypotheses, not prevalidated scripts. Inspect `sources` and `do_not_use`, follow primary sources and verify every new claim. Draft new hooks and structures instead of just repackaging the original caption. Preserve neutral Latin American Spanish, respect and accuracy; allow curiosity, narrative tension and visual surprise without false stakes or invented quotations.

## Twelve format hypotheses

| ID | Format | Initial length | Viewer reason to stay |
|---|---|---|---|
| F01 | Visual puzzle → reveal | 12–20 s | Recognize an object/system before the explanation |
| F02 | Myth → evidence → correction | 20–35 s | Resolve a familiar misconception |
| F03 | Object-led micro-documentary | 30–45 s | Discover what one real artifact reveals |
| F04 | Three-beat illustrated story | 25–40 s | Follow obstacle, action and consequence |
| F05 | Quote in context | 15–25 s | Understand the missing meaning behind a familiar line |
| F06 | Two-voice question/answer | 25–40 s | Hear a skeptical question and a precise answer; label dramatization |
| F07 | Hands/tabletop demonstration | 15–30 s | See the mechanism rather than read about it |
| F08 | Timeline or map animation | 20–35 s | Understand change across time/place; draw exact data in code |
| F09 | Seamless visual loop | 8–15 s | Rewatch a transformation or reveal; natural loop, no deception |
| F10 | Swipeable mini-essay | 5–7 cards | One clear idea per card, source and question at the end |
| F11 | Story sequence with a question | 3–4 frames | Make a prediction then see the explanation; interactive stickers only if supported |
| F12 | Single-image editorial + strong caption | 1 image | Communicate one unexpected idea immediately |

Create one low-cost storyboard for every format before selecting finished renders. F01–F09 give nine motion concepts; F10–F12 give three static/sequence concepts. A strong opening should appear in the first frame; do not require sound to understand the premise. Compare calm and more immediate hooks without losing the brand's voice.

## Round 1: broad free/included screening

Screen every listed option for availability. Each accessible option gets one bounded sample; unavailable or unsuitable options get a documented reason and the work continues. The ceiling is one discovery sample plus one focused repair per option. Do not silently skip options or purchase access. Confirm features and output rights at test time rather than assuming the entire product is free.

| ID | Option | One useful test | Cost/access treatment |
|---|---|---|---|
| T01 | Existing renderer + FFmpeg | Original baseline and controllable motion version | Local foundation |
| T02 | Built-in imagegen | Two visual directions, then an edit preserving style | Included allowance; no paid API fallback |
| T03 | Open-access originals | Artifact-led card and pan over a source image | Record asset-level rights and provenance |
| T04 | Edits on Samsung | Import three scenes, add audio/captions, export original MP4 | Priority; test actual app/account features |
| T05 | Native Instagram/Facebook creation | Add supported audio/caption/cover in a draft | Priority publishing comparison; exact audience unresolved |
| T06 | Kokoro locally | Same 20-second passage in three Spanish voices | Local install; select by listening, not claimed accent |
| T07 | Human phone narration | Same passage recorded by the user | Optional user contribution; don't block other tests |
| T08 | Canva Free | One carousel/cover and a video only if free export is available | Limited allowance; record templates/assets used |
| T09 | CapCut free features | Recreate reference timeline and captions | Verify current free/export boundaries per account |
| T10 | Adobe Express Free | Recreate reference timeline or animated explainer | Verify feature/asset/export limits |
| T11 | DaVinci Resolve Free | Same timeline, voice mix and export | Separate learning/setup time from repeat-edit time |
| T12 | ElevenLabs Free | Same passage as Kokoro for private voice comparison | Evaluation only: free output lacks commercial rights |
| T13 | HeyGen Free | One brief in a presenter/video-agent treatment | Quota/export restrictions; assess brand fit |
| T14 | Runway free credits | Animate one shared reference image | Conditional, one-time credits; watermarked free output |
| T15 | Pika free allowance | Animate the same image/prompt as T14 | Confirm current balance, resolution and rights; not API entitlement |
| T16 | Music/sound treatment | Same narration with no music, quiet licensed bed, sparse effects | Use original or explicitly licensed audio; record track/destination rights |

This screens sixteen options without generating every tool × topic × format combination. A tool that only produces a preview can be scored for creative potential but fails production-export eligibility.

## Controlled comparisons

Separate format discovery from tool benchmarking:

1. **Baseline:** preserve current card/reel output for three topics; record original render time.
2. **Reference brief:** use one approximately 30-second Braille brief with fixed facts, script, three scenes, voice master, caption text and export target. Timeline editors receive the same assets. Score assembly separately from generative ability.
3. **Voice bake-off:** same words and normalized listening volume across voices; anonymize filenames. Keep expressive delivery evaluation separate from correct pronunciation. Include silence as an accessibility control, not a voice competitor.
4. **Motion bake-off:** same reference image, intended action, framing and requested duration across generators; score their native outputs before any common final export.
5. **Creative discovery:** storyboard all twelve formats; choose six spanning at least three seeds and at least two non-video formats. Build one finished prototype per selection using promising tools.
6. **Repeatability:** best three production workflows repeat on two different seeds each (six additional outputs). Include one revised date or caption after export to measure correction/re-export effort.

Outputs: a complete sixteen-option screening register, twelve storyboards, six polished format prototypes, six repeatability samples, and delivery-test evidence. Samples may be reused across comparisons where inputs are identical. Do not count reuse as a new independent test. Export variants are not new creative samples.

Suggested effort controls: 20 minutes for an account/feature probe; 45 minutes active editing for a first sample; up to 90 minutes for a worthwhile local setup. Pause and document when exceeded, then continue other options. Report slow-but-promising options instead of discarding quality purely on first-time learning cost. Generation waits and total elapsed time are still recorded.

## Publishing tests — independent of the existing schedule

Creation quality, delivery integrity and audience engagement are separate outcomes. A private/test-account post checks delivery; it cannot establish real audience appeal.

| Route | Test | Evidence |
|---|---|---|
| P01 | Edits → named Instagram destination | Final cover/caption, audible tracks, correct aspect, actual post URL |
| P02 | Edits → named Facebook destination, if offered | Same checks plus destination identity |
| P03 | Export MP4 → native Instagram uploader | Whether export retains audio; whether native music differs from baked audio |
| P04 | Export MP4 → native Facebook uploader | Same master, delivery time and processing result |
| P05 | Export MP4 → standalone lab API harness | Start with existing supported Facebook reel adapter; isolated credentials/state, no production orchestration |
| P06 | Carousel/story through native app | Card order, legibility, interactions and platform-specific audio availability |

Inspect current adapters before promising API support; do not infer Instagram reels/carousels from photo support. Add new API routes only inside the lab after official documentation and permissions checks. TikTok/YouTube and other declared targets are in campaign scope: try verified free native routes when API support is absent, and record any account or capability blockers.

Before each live route, verify the brand destination and intended public audience. Follow TWO-WEEK-CAMPAIGN.md for cross-platform adaptations and volume. Do not publish the same adaptation twice through native and API routes. State clearly when audio cannot be exported/reused or is attached only within a platform. Do not assume the publishing API can attach a catalog track.

Save the original master and its hash, route, asset IDs, requested and actual audience, submission time, processing completion, playable confirmation time, post ID/URL and errors. A returned ID or upload acceptance is not proof of playable delivery. Verify the final platform player visually and audibly. On uncertain submission, reconcile the existing post before retrying. Do not delete posts automatically to reset tests.

## Measurement and decisions

Use `run-template.json` per run. Unknown means null with a reason, never zero.

**Time:** separate one-time setup, research/script, asset creation, editing, corrections, transfers, export, upload and remote processing. Record wall-clock start/end plus active human and active agent minutes. Overlapping waits must not be added to elapsed total. Record approval/device-unlock waits separately. Report first acceptable output and final accepted output times.

**Quality:** use 1–5 anchored ratings: 1 unusable, 3 usable with noticeable repair, 5 polished and ready. Rate visual storytelling, clarity/readability, voice, pacing, brand fit and opening hook. Voice is N/A for silent/static work. Suggested composite: 25% visual, 20% clarity, 15% voice, 15% pacing, 15% brand, 10% hook; remove inapplicable weights and renormalize. Label evaluator identity; agent scoring cannot stand in for human listening or audience response.

**Hard gates:** facts/quotation verified; asset/audio rights support the intended destination; no critical typo, misleading reconstruction, clipped narration or missing media; export fits intended platform; final playback correct; spending matches round. A high average cannot compensate for a failed gate. A low-resolution or watermarked free sample may inform Round 2 without qualifying for publication.

**Reliability:** attempts, failures, manual interventions, steps that cannot be automated, export success and time to fix. Save prompts, versions, reference assets and selected bytes. Repeating a prompt is not reproducing the asset.

**Cost:** actual monetary spend, included/free credits consumed, local compute time and recurring subscription allocation separately. Round 1 incremental money must remain zero. Do not label prepaid or included use as universally free. For paid round, include discarded outputs in cost per accepted piece.

**Audience:** after destination/batch agreement, measure at 24 h, 72 h and 7 days from actual publication, without creating scheduled tasks unless requested. Record reach, plays, available early retention, average watch time, completion, shares, saves and meaningful comments. Keep platform definitions; missing metrics remain missing. Compare rates per reach or play with explicit denominators and same post age; compare static and video separately.

If public creative testing is authorized, use matched blocks across topics, formats, posting windows and platforms. Rotate assignment to reduce time/topic confounding; do not post every variant back-to-back to the same audience. A first six-post batch is exploratory, not an A/B significance claim. Test-account results and unequal audience exposure cannot prove a format wins. Recommend a larger follow-up if results are ambiguous.

Select the nondominated workflows: those offering better quality at similar effort, or much lower effort at acceptable quality. Proposed acceptance is at least 4/5 on applicable dimensions after gates, repeatable on two seeds. Preserve separate winners by format and use case instead of forcing one tool for everything.

## Round 2: paid candidates after evidence

No purchase, paid API call or paid-trial activation is authorized by this plan. First identify the quality/time gap, check current availability/prices, then obtain a concrete spending cap and selected provider(s).

| Gap from Round 1 | Paid candidates to compare | Controlled retest |
|---|---|---|
| Spanish voice lacks warmth or pronunciation | ElevenLabs paid; OpenAI TTS | Same three passages and names; regenerate under appropriate rights |
| Image consistency or editing effort | OpenAI Image API; paid design allowance only if needed | Same brief and reference set; first output versus one revision |
| Motion is worth having but free output is limited | Runway, Veo, Pika paid | Same reference/action; artifacts, accepted seconds and cost |
| Presenter format wins but export is limited | HeyGen paid | Same accepted script, face/voice continuity and export |
| Templates/captions save time but free features block export | Canva/CapCut/Adobe paid | Repeat the same edit; count actual minutes saved |
| Local generation is valuable but too slow | Metered hosted inference for the chosen model | Same inputs; setup, latency, privacy and spend controls |

Suggested budget discussion: start with a user-approved small fixed total, allocated to at most three demonstrated gaps, rather than subscribing to all tools. Produce two seed comparisons per chosen upgrade plus one edit; cap retries and stop at budget. Report quality gain, minutes saved, cost per accepted output and expected cost at an explicitly stated monthly volume. Do not invent a monthly volume from the existing schedule.

Do not build a new Sora dependency: current OpenAI documentation lists the Videos API/Sora 2 shutdown for September 24, 2026. Recheck model lifecycles at Round 2 launch.

## Sources and availability checks

Documentation reviewed in this planning session or the preceding project exploration; verify again at execution. These links support capabilities/limits, not claims that every account has access.

- [Edits](https://about.fb.com/news/2026/04/one-year-of-edits-built-for-and-with-creators/) and [scrcpy](https://github.com/Genymobile/scrcpy).
- [OpenAI images](https://developers.openai.com/api/docs/guides/image-generation), [speech](https://developers.openai.com/api/docs/guides/text-to-speech), [deprecations](https://developers.openai.com/api/docs/deprecations).
- [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M), [Spanish voices](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md), [ElevenLabs free-output rights](https://help.elevenlabs.io/hc/en-us/articles/13313564601361-Can-I-publish-the-content-I-generate-on-the-platform).
- [Met open access](https://www.metmuseum.org/hubs/open-access), [Canva allowances](https://www.canva.com/help/ai-access-variantb/).
- [CapCut caption workflow](https://www.capcut.com/help/how-to-recognise-subtitles), [Adobe Express plans](https://www.adobe.com/express/pricing), [DaVinci Resolve Free/Studio](https://www.blackmagicdesign.com/products/davinciresolve). Marketing feature lists do not settle account-level free export access.
- [HeyGen plans](https://help.heygen.com/en/articles/15125761-heygen-credit-based-pricing-plans-subscriptions-explained), [Runway Free](https://help.runwayml.com/hc/en-us/articles/50404627334547-Free-plan-details), [Pika plans](https://pika.art/pricing), [Veo](https://ai.google.dev/gemini-api/docs/veo).

## Deliverables for the new session

1. Availability register covering all sixteen options, with tested, blocked, rejected or deferred status and reasons.
2. Twelve new format storyboards grounded in existing content; source/claim notes.
3. Labelled export gallery with originals, six polished prototypes and repeatability samples.
4. Per-run JSON records and a quality/time/cost comparison, including failed attempts.
5. Independent publishing log with verified URLs and playback evidence where live tests are configured.
6. Recommended free workflows and a gap-driven paid-round proposal.
7. Integration recommendations only after testing; no automatic adoption into production.
