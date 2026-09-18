# BenchReporter Task List

Local working notes. This file and the rest of `sleeper_utils/` are local development utilities.

Status key: `[x]` complete, `[-]` partially complete, `[ ]` not started.

## Current State

- [x] Python package uses a `src/` layout with a real local CLI.
- [x] Sanitized 2025 Sleeper sample data is committed under `tests/data/`; raw captures stay private under `tests/private/`.
- [x] FastAPI mock Sleeper API and in-process integration testing are in place.
- [x] Structured `BotMessage` objects separate feature logic from console/Discord delivery.
- [x] Test suite passes: ` .venv\\Scripts\\python.exe -m pytest -q ` (54 tests at last review).
- [x] Local previews are available through `tests.support.preview_messages`.

## V1 Foundations

- [x] Sleeper client covers league, roster, user, matchup, transaction, draft, player directory, NFL state, and weekly stats routes.
- [x] Discord REST client supports dry runs, the 2,000-character hard limit, and one 429 retry.
- [x] Runtime configuration supports league ID, season, Sleeper base URLs, dry run, bot token, and channel IDs.
- [x] Scoring detection recognizes standard, half-PPR, and PPR; custom scoring is identified instead of silently mapped to a generic stat field.
- [x] Storage interface, in-memory implementation, and DynamoDB implementation cover dedupe, weekly flags, player cache, and snapshots.
  - [x] Implement DynamoDB storage with conditional writes; RSS dedupe records carry a TTL and the deployed table enables TTL processing.
  - [x] Add TTL metadata to `TXN` dedupe records, or explicitly retain them permanently if trade-announcement idempotency should survive beyond a season.
  - [x] Enforce the 24-hour player-directory cache refresh policy; the cache currently persists until overwritten.
- [x] Historical records are written for team weeks and trades.
  - [x] Persist draft-pick snapshots.
  - [x] Persist optional roster-move/waiver snapshots, including FAAB where available.

## V1 Features

### F3: Weekly Roundup

- [x] Pair head-to-head matchups and render results.
- [x] Report weekly high and low scores.
- [x] Identify standout starters using position starter averages.
- [x] Identify letdowns from prior-game averages.
- [x] Write team-week snapshots before the roundup is marked posted.
- [x] Run the real workflow locally:
  ` .venv\\Scripts\\python.exe -m sleeper_discord_bot.local_app --league-id <id> --season 2025 weekly --week 16 `
- [x] Add graceful section fallback when `players_points` is missing or malformed; scoreboard/high-low should still post.
- [x] Add a message-condensing or splitting strategy for unusually large leagues so the final delivered content cannot exceed Discord's limit.
- [ ] Review target-week behavior against live preseason, Week 1, postseason, and offseason state responses.

### F4: Trade Announcements

- [x] Filter completed trades, resolve managers, players, and draft picks.
- [x] Deduplicate transaction IDs in local storage and write trade snapshots.
- [x] Run the real workflow locally:
  ` .venv\\Scripts\\python.exe -m sleeper_discord_bot.local_app --league-id <id> --season 2025 trades --week 1 `
- [x] Include FAAB in trade messages and snapshots when a transaction contains it.
- [x] Enforce the in-season-only polling rule in the deployed handler.
- [x] Define delivery behavior for a multi-team trade or a trade message that would exceed Discord's limit.

### F1: News Feed

- [x] Add RSS/Atom parsing with a source-agnostic feed URL.
- [x] Use Rotowire's NFL feed as the initial configured source.
- [x] Add RSS item ID/hash dedupe, TTL metadata, formatted news messages, and first-run backlog protection.
- [x] Add handler, local command, and unit tests.
- [x] Deploy the RSS Lambda, SSM parameters, DynamoDB table, and EventBridge Scheduler job to AWS; verify live Discord delivery.
- [x] Correct SAM's `src/` package import path in the deployed Lambda artifact.
- [x] Add client error-path tests and a static sample feed payload.

### F2: Standout Free Agents

- [x] Build the available-player pool from rostered players, directory data, and weekly stats.
- [x] Use runtime league scoring detection to choose `pts_std`, `pts_half_ppr`, or `pts_ppr`.
- [x] Use Sleeper weekly projections for preseason reports and completed-week stats during the regular season.
- [x] Skip only free-agent scoring when scoring is custom; retain the rest of the bot's work.
- [x] Rank QB/RB/WR/TE against each position's free-agent average.
- [x] Add `Proven Free Agent` labels with prior-production context.
- [x] Add `Injury Opportunity` labels using Sleeper player injury/status data for rostered Q, doubtful, out, IR, and PUP players; suppress third-and-later-string players when a healthy first/second string remains ahead.
- [x] Add handler, local command, hand-authored sample scenarios, and formatting tests.

## AWS Deployment

- [x] Add `infra/template.yaml` with DynamoDB, Lambda functions, EventBridge schedules, IAM, and configuration wiring.
  - [x] DynamoDB state table: on-demand billing, `pk`/`sk` keys, TTL, encryption, and point-in-time recovery.
  - [x] Tracked SAM configuration example and ignored local `samconfig.toml` workflow.
  - [x] Local `.env.example` with configuration names only.
- [x] Add Lambda functions, EventBridge schedules, IAM, and configuration wiring as features are implemented.
  - [x] RSS Lambda, runtime SSM reads, DynamoDB access, and a 15-minute EventBridge Scheduler job.
  - [x] F2 Lambda, runtime SSM reads, DynamoDB access, and a Tuesday 9 AM America/Chicago EventBridge Scheduler job.
  - [x] Deploy the initial RSS stack to `benchreporter-dev` and verify a manual invocation reaches Discord.
  - [x] Add the remaining feature Lambdas and schedules.
- [x] Add Lambda entrypoints for F1-F4 that use the same handlers as the local app.
  - [x] F1 RSS Lambda entrypoint.
  - [x] F2 Standout Free Agents Lambda entrypoint.
  - [x] F3-F4 Lambda entrypoints.
- [x] Store the Discord bot token and RSS channel ID in SSM Parameter Store.
- [x] Add `.env.example` for local configuration names only, with no secrets.
- [-] Add structured logs: job, season/week, dry-run status, request counts, sends/skips, writes, and skip/error reasons.
  - [x] Emit JSON Lambda result logs with job, configured season, dry-run status, sends/skips, and snapshot writes.
  - [ ] Add request counters plus resolved week and skip/error-reason fields.
- [x] Add CloudWatch alarms for recurring Lambda and Discord delivery failures.
- [-] Run AWS smoke tests.
  - [x] Invoke F1 manually and verify Lambda, DynamoDB, SSM configuration, and Discord delivery.
  - [ ] Verify the scheduled F1 invocation and test each future handler after deployment.

## Test Coverage To Add

- [x] Missing or malformed weekly stats response.
- [x] Missing `players_points` with a scoreboard-only weekly roundup.
- [x] Custom scoring skips F2 with a clear reason.
- [x] Proven Free Agent scenarios.
- [x] Trade containing FAAB and a message at Discord's length boundary.
- [x] DynamoDB conditional-write/idempotency behavior.
- [x] RSS duplicate, malformed item, and feed failure cases.
- [x] Lambda handler integration tests against the mock API and dry-run delivery.

## V1.2: Preserve Data Now, Build Later

- [ ] Season awards and manager tendency recaps.
- [-] Trade impact reports and awards.
  - [x] Compute post-trade points for acquired players from raw weekly matchup data.
  - [ ] Validate the report and delivery workflow before enabling deployment.
- [-] Draft value/reach awards, including early QB/TE success or failure.
  - [x] Compute draft-order value deltas from preserved draft picks and season player points.
  - [ ] Validate the report and delivery workflow before enabling deployment.
- [-] Waiver, bench, start/sit, and schedule awards.
  - [x] Compute same-position bench regrets and weekly all-play schedule-luck deltas from raw matchups.
  - [ ] Validate the report and delivery workflow before enabling deployment.
