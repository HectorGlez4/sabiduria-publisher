# Two-week live format experiment: Facebook first

Prepared 2026-09-13; starts on the first launch day chosen in the new session. This is the latest scope and overrides conflicting offline-only, dedicated-test-account or deferred-crossposting defaults in earlier notes. Preparation only has occurred; no campaign posts or recurring jobs have been created.

## User mandate

Latest coverage requirement: **every publishable test family must cover Facebook, Instagram and Threads, in every applicable format available on each account, with API and connected-Android routes tested wherever each route supports that format.** These three networks are mandatory, not optional adaptations. Other previously named networks remain secondary expansion targets and must not displace Meta coverage. Normal scheduled posts continue unchanged and constitute the observational baseline; every lab release is additional.

“Every format” means actual account-supported organic publishing formats and their relevant treatments. Inventory native and API capabilities separately; do not invent Threads Stories or equate Facebook multi-photo posts with Instagram carousels. Record genuine unsupported combinations with evidence. A failed or factually unsuitable candidate stays in the experiment record but is not published merely to fill a cell.

Explore substantially more formats and image-generation variations, start with the easiest, build up over approximately two weeks, and actually publish to the project's social-media targets to benchmark views. Use Facebook as the primary creative and analytical focus. Round 1 remains zero incremental monetary spend; paid tools belong to a separately budgeted Round 2.

Publishing on the existing Sabiduría accounts is requested. Resolve identities from project records and connected accounts; do not ask repeatedly for permission already provided. Ask only where the intended account is ambiguous or missing, a permission/account action requires the user, or a proposed action exceeds scope. Do not substitute a personal profile for a brand account. Real public account performance, rather than a private sandbox, is the objective.

The existing automated publishing queue and schedule remain unchanged. Lab posts use separate IDs, files and delivery records. Read the production calendar to avoid collisions and log nearby production posts as possible confounders. Sharing a live audience means experimental exposure is not isolated even though the software and queue are separate.

## Operating rhythm and volume

The fourteen-day table is a sequence of creative themes and increasing difficulty, not a cap of fourteen posts. Each day's publishable family expands across all three mandatory networks and all applicable formats/routes. This supersedes the earlier one-post-per-account and optional-Story limits. Stories are required where supported and applicable. Add confirmation families after initial coverage and repeatability checks.

Each eligible family gets multiple platform/format adaptations sharing one `family_id`. At launch, calculate the actual number of required posts from the verified capability matrix and show the resulting release plan. Spread variants across appropriate windows rather than flooding all copies at once. Record timezone, planned/actual release times, spacing and platform limits. If full coverage exceeds two-week capacity, explicitly identify the remaining cells and extend or resequence with the user; never silently shrink coverage or declare the campaign complete.

Set Day 1 and release windows at launch based on the live calendar and account availability. Do not silently move production posts, auto-create schedules or backfill missed days with a burst of posts. Continue creation and publishing on available targets while recording blockers elsewhere.

## Format inventory and adaptation

Maintain `coverage.json` using `coverage-template.json`. Each required cell identifies family, network, native format, treatment, publishing route and variant. Status progresses through planned, ready, published and measured; blocked/unsupported require evidence and a reason. Track publishable masters separately from native variants. A network is not “covered” because one post succeeded; every required cell needs a real post URL/ID or a documented unresolved status. No empty or unsupported cell counts as a successful publication.

For each family, prepare the applicable text, single-image, multi-image, short-video, Story and interactive forms actually exposed by that network/account. Music and location are treatment dimensions, not automatically new native formats. Preserve the verified core while adapting the experience. If a family cannot honestly support a treatment, record why and use another matched family for that treatment; do not fabricate content to force compatibility.

At launch, inspect each account's actual composer and available metrics. Mark every format as native-supported, supported-through-adaptation, blocked, or not-applicable. Test every available relevant organic format progressively; do not buy ads or create Groups/events just to access a different format.

| Facebook-first format | First implementation | Important distinction |
|---|---|---|
| Text-only question or short narrative | Strong opening, verified fact and a real discussion question | A control for image value |
| Single image + caption | Editorial visual with sparse text | Baseline for easy daily production |
| Generated person + text overlay | Original illustrated/fictional presenter, composed type | Record subject type and disclose reconstruction when necessary |
| Person in a historical environment | Same visual identity in contextual scenes | Avoid invented documentary evidence |
| Multiple images / carousel-style story | Numbered 3-card sequence, then 5-card version | Facebook multi-photo layouts may be grids; an organic post is not automatically an ad-style carousel |
| Multiple-choice trivia | Question plus A/B/C/D and evidence-backed reveal | Works as an image even without a native poll |
| Multiple-correct-answer trivia | Explicitly say “elige todas las correctas” | Do not force into single-choice controls |
| True/false, identify the person/object | Simple visual challenge and explanation | No reaction-based voting or reward bait |
| Native poll | Use only if this Page/surface actually offers it | Group/Story poll availability does not establish Page-feed support |
| Image + music | Native photo/Story music if present; otherwise short MP4 | A musical MP4 is a video treatment, not a native photo equivalent |
| Image + narration | Still image or restrained motion, spoken explanation | Store clean narration master for reuse |
| Image + location | Place inside the scene; place label/map; separate native place-tag test | These are three different variables |
| Before/after or two-panel comparison | Historical/current contrast with sources | Label imagined reconstructions; do not fabricate a current photo |
| Infographic, map or timeline | Exact data/layout drawn in code | Generated decoration must not alter factual geometry |
| Stories: quiz/reveal sequence | At most three frames, suitable interaction if available | Read metrics before expiration |
| Short loop / slideshow Reel | 8–15 seconds, one payoff | Retention/replays separate from unique reach |
| Narrated story / micro-documentary | 20–45 seconds, 3–4 scenes | Reuse successful image treatments |
| Source-led link post | Verified source, strong caption and suitable preview | Analyze separately from native media |
| Longer video / Live | Later only if short formats justify it and account tools permit | Inventory now; not a dependency for the first two weeks |

## Extensive image-generation tests

Use a staged gallery, not an unbounded cross-product. Begin with eight comparison batches of up to four images/composites each (up to 32 review candidates); promote only useful variations to public posts. Existing allowance may yield fewer. Log a quota block, reuse existing assets or open-access originals, and never switch silently to paid generation.

| Batch | Comparison | Controls |
|---|---|---|
| I01 | Fictional presenter versus object-led image | Same fact, palette, headline and layout |
| I02 | Illustrated person versus realistic generated person | Same character brief, framing, setting; realistic output labelled where misleading otherwise |
| I03 | Close portrait versus environmental portrait | Same person/reference, headline, palette |
| I04 | Minimal background versus period/place setting | Same foreground subject and composition |
| I05 | Image alone versus sparse versus denser overlay | Compose text on the SAME saved image; no extra generation needed |
| I06 | Headline placement and 1:1 / 4:5 / 9:16 composition | Keep wording fixed; crops are not independent generations |
| I07 | Same character across three scenes | Use selected reference image; score identity, clothing, period continuity |
| I08 | Open-access original versus generated editorial illustration | Same subject and factual purpose; both clearly attributed/classified |

Record anatomy/hands, face consistency, period accuracy, believable lighting, negative space, Spanish typography, legibility at phone size, and whether the image actually communicates the fact. Log original prompts, edits, references, model/tool, resolution, retries and selected file hashes.

Generate artwork separately from exact quotes, option letters, dates, maps and place labels. As a small optional capability check, compare in-image generated text against code-overlay text; publish only the version passing exact spelling/readability checks. A fictional presenter must not be introduced as a historical witness or real expert. Historic likenesses are artistic reconstructions, not authentic photographs.

## Trivia construction

Maintain question, response mode (`single` or `multiple`), labelled choices, correct choice IDs, explanation, citations and reveal placement in the brief. Single-choice needs exactly one defensible answer; multiple-choice alternatives must not become correct under another reasonable interpretation. Rotate correct-answer positions across tests.

Example structure: “¿Qué distingue este sistema de escritura? A… B… C… D…” → final card explains the answer with a source. Verify wording against the actual research before writing choices. Never use an unchecked AI answer key.

Publish a complete experience: reveal in the last slide/frame or in the same post's caption. If testing a reply-based reveal, publish the answer promptly as an explicitly linked part of the same experiment and record it. Do not withhold basic facts to demand comments/shares. Track responses as meaningful participation separately from views and reactions.

## Location and audio

For location, test (a) a recognizable setting, (b) an accurate place name/map overlay, and only then (c) a real topic-relevant native location tag where the surface supports it. Do not add a check-in implying physical presence, falsify GPS, or use the phone's private location. Record native place ID and visible label when used.

For music, keep voice-only, music-only and voice+music treatments distinct. Native catalog audio may have platform/account-specific rights and may not survive export. Retain a clean master and create separate authorized mixes for each target. ElevenLabs Free remains private evaluation only if commercial reuse is not licensed. Do not remove watermarks from trial outputs to make them publishable.

## Fourteen-day progression

Day numbers are relative to launch. Rotate corpus topics across formats; use new hooks/facts rather than immediately reposting the same story. Original source pieces inspire each release and remain unchanged.

| Day | Primary family | What it teaches |
|---|---|---|
| 1 | Strong single image + short caption | Publishing/metrics baseline with the simplest asset |
| 2 | Generated person + sparse headline | Whether a face-led treatment merits further use |
| 3 | Place-led image with factual location text | Place/context treatment without native-tag confounding |
| 4 | Four-option trivia image + explanation | Interest in questions and answer quality |
| 5 | Three-card question → clue → reveal | Sequence design and actual Facebook multi-photo display |
| 6 | Five-card artifact-led story | Longer sequence and source-driven visual narrative |
| 7 | Text-only curiosity question; optional Story quiz | Low-effort control; first-week quality/process review |
| 8 | Image with music, simplest supported surface | Audio import/export and availability; log actual media type |
| 9 | Illustrated narrated Reel | Voice contribution and retention |
| 10 | Multiple-correct-answer trivia sequence | Participation with explicit answer rules |
| 11 | Place-led story with native tag if applicable | Tag feasibility; matched follow-up, not a claim of causal uplift |
| 12 | Same fictional presenter across three scenes | Character continuity and production cost |
| 13 | True/false or visual mystery loop | Short reveal versus longer narrated explanation |
| 14 | Best early treatment on a fresh topic | Replication; provisional report and next-round selection |

During days 8–14, allocate up to six additional families to matched follow-ups of the most promising dimensions (e.g. person/no-person, 3/5 cards, voice/music). Change one focal variable, rotate topics/time windows, and use the best controls available. Breadth is exploratory: days 1–14 alone cannot causally rank all formats. Do not declare a winner from different topics and times.

## All project social targets

The project's declared networks are Facebook, Instagram, Threads, X, LinkedIn, TikTok and YouTube. Facebook/Reels/Stories are surfaces, not additional networks. Actual login, destination and publishing/analytics rights must be checked. Lack of an API adapter is not automatic evidence that a native upload is impossible.

| Target | Intended adaptation | Launch verification |
|---|---|---|
| Facebook — primary | Photos, multi-photo sequences, trivia, Stories, Reels, text/link control | Existing Page identity; exact native features; Insights access |
| Instagram | Image/carousel, Story interaction and Reel versions | Account identity; export dimensions; music rights; carousel/Reel route not inferred from existing photo adapter |
| Threads | Image sequence or short text/trivia thread; video if available | Current media limits, poll availability, native analytics; avoid publishing both API and native duplicate |
| X | Concise question/image, supported poll or video variant | Existing brand login; use free native path if available; API terms/access must be rechecked |
| LinkedIn | Professional framing, image/document sequence, native poll or video | Brand Page versus personal account, admin access, document and poll support |
| TikTok | Photo post or vertical quiz/story video | Native account/upload tools; app/library rights; current API stubs need not block manual route |
| YouTube | Shorts for motion; image/poll/quiz Posts where channel eligible | Channel identity, Posts eligibility and analytics; distinguish Shorts from Posts |

Resolve existing destinations from project history and signed-in brand accounts first. Use `destinations.json` to record verification without credentials. Ask for missing handles/logins as one concise grouped request while other work proceeds. Record each family×target as published, pending-login, pending-capability, failed or adapted; no silent omissions and no false “published everywhere” claim.

Use shared verified facts/artwork but adapt captions, aspect ratios, interaction and music. Track each adaptation under the same family ID. Keep separate platform leaderboards. An adaptation that changes format or soundtrack is a related test, not an identical cross-platform A/B sample.

## Benchmarking real views

### Required publishing comparison: API versus connected Android

Both routes are mandatory experiment tracks, starting on Facebook. A phone upload is not merely a fallback when an API fails. Record unsupported combinations instead of treating phone-only features as API failures. Resolve current API permissions and native account features during launch.

| Route | Creation source | Publishing action | Purpose |
|---|---|---|---|
| API-MASTER | Saved lab image/video | Official platform API through an isolated lab harness | Programmatic delivery baseline |
| ANDROID-MASTER | The same kind of saved lab master, transferred to Samsung | Native Facebook/Instagram/etc. app on connected Android | Compare upload route without changing editing workflow |
| API-EDITS | Original MP4 exported by Edits and recovered on Mac | Official API through the lab harness | Test whether Edits output works equally well through API |
| ANDROID-EDITS | Edits project/output on Samsung | Edits share flow or native app upload; record which | End-to-end phone workflow and native features |

First verify phone screen access/control and the correct signed-in brand account. ADB authorization alone does not prove control of Edits. Use supported UI tools, observe each relevant state, and verify the final post rather than relying on blind taps or an upload confirmation. Log human interventions separately from agent-operated steps. Record reconnect/unlock interruptions, but do not deliberately interrupt a public upload to test recovery.

**Technical comparison:** use the identical saved master, caption, intended audience and destination surface to compare staging/previews/export behavior across routes. Where identical public uploads are needed for delivery fidelity, use an explicitly selected test destination and exclude them from audience conclusions. Do not post duplicates to the real feed just to fill a comparison cell. Keep the source hash and record any native crop, recompression, soundtrack, cover or caption change.

**Live audience comparison:** reserve six matched pairs (twelve of the campaign's existing release slots, not twelve extra posts): two pairs of single-image posts, two pairs of multi-image/trivia where both routes support them, and two pairs of short video. Within each pair, match format, topic class, quality, caption length, audio and expected duration, while using distinct factual pieces. Alternate route assignment across comparable windows (API then Android in one block; Android then API in the next). Record the route assignment before seeing results. If multi-image API publishing is unavailable, substitute a supported format and label native-only carousels separately.

Facebook, Instagram and Threads all get the full applicable route comparison. The initial six matched pairs are a starting block, not a substitute for the family×network×format×route coverage requirement. Missing API access remains an explicit blocker, not a reason to skip eligible Android publishing. Keep network results separate and begin with easy supported cells while resolving more complex ones.

Measure source-to-ready time, phone transfer time, active publishing time, upload time, remote processing, final playable confirmation, rework, caption/cover/order fidelity, aspect ratio, audio preservation, failures and 24-hour/72-hour/seven-day views. Record native music/stickers/location as additional treatments: if these differ between routes, the test measures the whole workflow, not the upload mechanism alone. A native music attachment cannot be assumed equivalent to the same song embedded in an API-uploaded file.

Never presume Android publishing receives better distribution. Six matched pairs are an exploratory signal, affected by topic, timing and audience overlap. Report uncertainty and recommend more repeats if the apparent route advantage is small or inconsistent. Select separate winners for reliability, effort, available features and audience performance.

Use one lab publication record per actual post and route, with a `comparison_pair_id`. Reconcile uncertain API/native submissions against the platform before retrying; never send through the other route as an automatic retry. The existing production dispatcher and schedule remain untouched.

Primary outcome: observed platform views at 24 h, 72 h and 7 days, with exact metric name/definition and observation time. Views are not necessarily unique people. Record reach/impressions if offered rather than renaming them “views.” Keep unique reach and repeat plays distinct.

For video, include available early retention, average watch time, completion and shares per reached viewer. For images/sequences, include available reach, views, saves, shares and substantive comments. Do not invent slide-level views/completion if a platform does not expose them. Trivia gets answers/votes and accuracy only where aggregate data genuinely supports it; comments are not a complete voter count.

Record production and publishing active minutes, elapsed waits, generation retries, accepted asset cost, platform adaptation minutes and delivery failures. Useful operational comparison: 72-hour views per active production minute, reported beside quality and raw counts; this is not a causal metric.

Read recent production performance for context without editing it. Compare within platform, format family and equal post age; keep follower counts, posting windows, topic and nearby production posts in the record. Do not pool unlike platform view definitions into a single “best network” score. All activity is organic; no boosts, purchased engagement or paid distribution in Round 1.

### Normal scheduled content as the baseline

Build a read-only baseline register from normal posts published during the campaign, plus recent pre-campaign history where metrics exist. Tag records `normal_scheduled`; tag lab posts `experiment`. Never move, replace, edit or republish a scheduled piece to create a control. Capture the same 24-hour, 72-hour and seven-day metrics for both groups, with early Story snapshots where applicable.

Match comparisons within network, actual format, post age, approximate topic and posting window. Report raw counts, median views, spread, sample size, and percentage difference from the matched baseline when its denominator is nonzero. If no same-format baseline exists, show that explicitly and compare against a labelled broader network baseline; do not imply a matched comparison. Missing historical snapshots cannot be reconstructed from present lifetime views.

Additional posting changes audience load, so scheduled content is an observational baseline, not a randomized untreated control. Record total daily posts and proximity between normal/test posts; compare scheduled performance before and during the experiment for possible overlap effects. Do not claim that a view difference is caused solely by a format or publishing route.

Story readouts occur at approximately 6 h and 20–23 h, with archived/Insights data later only if available. Save aggregate data, not unnecessary commenter profiles. Day 7 and Day 14 reports are provisional; complete the final seven-day readout on Day 21 for posts published on Day 14. Metric collection is not automatically scheduled by writing this plan.

## Platform evidence and limits

- Meta documents [Facebook photo sharing, multiple photos and location](https://www.facebook.com/help/iphone-app/187741037945488); the help page required login during direct retrieval, so verify the real composer rather than treating a search excerpt as an API contract.
- Meta announced [video publishing consolidation into Reels](https://about.fb.com/news/2025/06/making-it-easier-create-videos-facebook/). Record the actual surface produced by the current app.
- The official [Meta sample repository](https://github.com/fbsamples/reels_publishing_apis/blob/main/insta_reels_publishing_api_sample/README.md) describes Instagram publishing capabilities, but its older eligibility notes are not a substitute for current account verification. Direct current API documentation retrieval failed in this planning session.
- LinkedIn documents [polls with two to four choices](https://www.linkedin.com/help/linkedin/answer/a522948/create-linkedin-polls?lang=en) and [document/image/video posting](https://www.linkedin.com/help/linkedin/answer/a518996/posting-and-sharing-content-overview?lang=en).
- YouTube documents [image posts, polls and quizzes](https://support.google.com/youtube/answer/7124474), subject to channel eligibility; native quizzes have one correct answer. Use a different format for multi-correct questions.

## Paid round and adoption

After the first-week process findings and mature view readouts, identify concrete gaps: better portrait consistency, Spanish voice, scene motion, automated captions or publishing effort. Retest only justified paid candidates from PLAN.md against the best free baseline, under a separately agreed spending cap. New purchases remain unapproved.

Propose production changes after results: new content/quiz/media structures, media import, rendering variants and platform-specific adapters. Do not implement them in the active queue during the experiment. Preserve workflows that deliver acceptable quality quickly even if a more elaborate format earns more total views.
