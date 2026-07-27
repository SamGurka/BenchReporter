# Sleeper Fantasy Football Discord Bot

A serverless Discord bot for a Sleeper fantasy football league.

The project is in early implementation. The working technical spec lives in [`sleeper-discord-bot-spec.md`](./sleeper-discord-bot-spec.md).

## Motivation

I wanted a fantasy bot that does more than dump scores into Discord. The useful stuff is scattered across Sleeper, Discord, and fantasy news: who won, who got robbed, which trade mattered, who is sitting on the waiver wire, and what newer managers might have missed.

This bot should make weekly context easier to follow: standout free agents, league recaps, and eventually injury-related opportunity reports. It should also give checked-out managers a reason to look back in instead of disappearing after a rough week.

The weekly recap style is inspired by old Madden Franchise newspaper screens: quick updates, recurring storylines, and just enough personality to make the league feel more alive.

## Planned Features

| Feature | Description | Discord channel |
|---|---|---|
| News Feed | Posts items from a configurable RSS/Atom feed | `#espn-news-feed` |
| Trade Watch | Announces completed Sleeper trades | `#trade-block` |
| Weekly Roundup | Posts matchup results, weekly high/low teams, standout starters, and letdowns | `#last-week-tldr` |
| Standout Free Agents | Highlights notable available QB/RB/WR/TE options after each week | `#standout-free-agents` |

## Architecture

- **Runtime:** Python on AWS Lambda
- **Scheduling:** Amazon EventBridge Scheduler
- **Storage:** DynamoDB
- **Deployment:** AWS SAM
- **Config/secrets:** AWS SSM Parameter Store or Secrets Manager
- **Discord:** REST API message sends; no gateway connection
- **Data sources:** Sleeper API and RSS/Atom feeds

## Storage

DynamoDB stores bot state and historical snapshots:

- RSS item dedupe
- trade announcement dedupe
- weekly post idempotency
- Sleeper player-directory cache
- team-week snapshots
- trade snapshots
- draft pick records
- optional roster-move snapshots

Sleeper remains the source of truth for current league data.

## Scoring

The bot will inspect Sleeper league scoring settings instead of hardcoding one scoring format.

Supported v1 mappings:

- standard: `pts_std`
- half-PPR: `pts_half_ppr`
- PPR: `pts_ppr`

Custom scoring support is deferred unless it is needed before launch.

## Testing

Test setup:

- FastAPI mock Sleeper API
- sanitized Sleeper sample data under `tests/data/`
- private raw captures ignored under `tests/private/`
- tests for scoring, weekly roundup logic, trade parsing, message formatting, snapshot shaping, handler orchestration, and Discord REST sending

Run tests:

```bash
python -m pytest
```

Install dependencies and the project in editable mode first if module imports fail:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

Preview sample Discord-style messages:

```bash
python -m tests.support.preview_messages weekly --week 16
python -m tests.support.preview_messages trades --week 1 --limit 1
```

Run the local app path with console output:

```bash
python -m sleeper_discord_bot.local_app --league-id <league_id> --season 2025 weekly --week 16
python -m sleeper_discord_bot.local_app --league-id <league_id> --season 2025 trades --week 1
```

## Deployment

AWS SAM will own the deployable infrastructure.

```text
infra/
  template.yaml
  samconfig.toml
```

Expected deployment flow:

```bash
sam build
sam deploy --guided
```

## Legal

- [Privacy Policy](./PRIVACY.md)
- [Terms of Use](./TERMS.md)

## Roadmap

### V1

- News feed
- Trade announcements
- Weekly roundup
- Standout free-agent report
- DynamoDB dedupe/idempotency/cache records
- Historical data capture
- AWS SAM deployment

### V1.2

- End-of-season manager recaps
- Trade impact awards
- Waiver and bench awards
- Start/sit and schedule awards
- Early QB/TE draft reach award
- Injury Opportunity free-agent label

### Backburner

- NPC league team concept for a short-handed league. Sleeper's official public API is read-only, so autonomous team control is not part of the current plan.
