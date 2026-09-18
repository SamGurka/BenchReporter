from sleeper_discord_bot.clients.storage import InMemoryStorage
from sleeper_discord_bot.domain.free_agents import rank_free_agents
from sleeper_discord_bot.handlers.free_agents import run_free_agents
from sleeper_discord_bot.handlers import free_agents
from sleeper_discord_bot.handlers.results import HandlerResult
from sleeper_discord_bot.messages.bot_message import BotMessage
from sleeper_discord_bot.messages.free_agents import format_free_agents_message
import pytest


BASE_SCORING = {"pass_yd": .04, "pass_td": 4, "pass_int": -2, "rush_yd": .1, "rush_td": 6, "rec_yd": .1, "rec_td": 6, "fum_lost": -2, "rec": .5}


def stat(player_id, position, points, name, years_exp=3):
    first_name, last_name = name.split(" ", 1)
    return {"player_id": player_id, "player": {"first_name": first_name, "last_name": last_name, "position": position, "team": "TST", "years_exp": years_exp}, "stats": {"pts_half_ppr": points}}


def test_ranks_available_players_and_labels_prior_production():
    weekly = [stat("rostered", "RB", 30, "Roster Back"), stat("breakout", "WR", 22, "Young Star", 1), stat("proven", "RB", 18, "Veteran Back", 6), stat("baseline", "RB", 6, "Baseline Back")]
    players = {entry["player_id"]: {"name": f"{entry['player']['first_name']} {entry['player']['last_name']}", **entry["player"]} for entry in weekly}
    rankings = rank_free_agents(weekly_stats=weekly, rosters=[{"players": ["rostered"]}], players_by_id=players, stats_field="pts_half_ppr", prior_weekly_stats=[[stat("breakout", "WR", 8, "Young Star", 1), stat("proven", "RB", 10, "Veteran Back", 6)], [stat("proven", "RB", 10, "Veteran Back", 6)]])

    assert [row["player_id"] for row in rankings] == ["proven", "breakout", "baseline"]
    assert rankings[0]["label"] == "Proven Free Agent"
    assert rankings[1]["label"] is None
    assert rankings[0]["position_average"] == 12


def test_formats_free_agent_context():
    content = format_free_agents_message(4, [{"name": "Veteran Star", "position": "WR", "team": "TST", "points": 22, "margin": 12, "prior_average": 8, "prior_games": 2, "label": "Proven Free Agent"}])
    assert "12 over WR FA avg" in content
    assert "**Proven Free Agent**" in content


def test_formats_preseason_projections():
    content = format_free_agents_message(
        3,
        [{"name": "Young Star", "position": "WR", "team": "TST", "points": 12, "margin": 4, "prior_average": None, "prior_games": 0, "label": None, "projected": True}],
        projected=True,
    )
    assert "**Week 3 Projected Standout Free Agents**" in content
    assert "12 projected pts" in content


def test_formats_positional_and_injury_sections():
    content = format_free_agents_message(
        3,
        [
            {"name": "Quarterback", "position": "QB", "team": "TST", "points": 12, "margin": 4, "prior_average": None, "prior_games": 0, "label": None, "report_section": "standout"},
            {"name": "Backup", "position": "RB", "team": "TST", "points": 8, "margin": 2, "prior_average": None, "prior_games": 0, "label": "Injury Opportunity", "injury_context": [{"name": "Starter", "status": "IR"}], "report_section": "injury"},
        ],
    )
    assert "**Standout Free Agents**" in content
    assert "**Injury Opportunities**" in content


def test_promotes_same_position_backup_for_rostered_injury_status():
    weekly = [stat("backup", "RB", 4, "Backup Back"), stat("other", "RB", 15, "Other Back")]
    players = {
        "injured": {"name": "Starting Back", "position": "RB", "team": "TST", "injury_status": "Q"},
        "backup": {"name": "Backup Back", "position": "RB", "team": "TST"},
        "other": {"name": "Other Back", "position": "RB", "team": "OTH"},
    }

    rankings = rank_free_agents(
        weekly_stats=weekly,
        rosters=[{"players": ["injured"]}],
        players_by_id=players,
        stats_field="pts_half_ppr",
    )

    assert rankings[0]["player_id"] == "other"
    assert rankings[1]["player_id"] == "backup"
    assert rankings[1]["label"] == "Injury Opportunity"
    assert rankings[1]["injury_context"] == [{"name": "Starting Back", "status": "Q", "depth_chart_order": None}]
    assert "backing up Starting Back (Q)" in format_free_agents_message(4, rankings)


def test_preseason_directory_fallback_only_returns_injury_replacements():
    rankings = rank_free_agents(
        weekly_stats=[],
        rosters=[{"players": ["injured"]}],
        players_by_id={
            "injured": {"name": "Starting Back", "position": "RB", "team": "TST", "injury_status": "IR"},
            "backup": {"name": "Backup Back", "position": "RB", "team": "TST"},
            "unrelated": {"name": "Other Back", "position": "RB", "team": "OTH"},
        },
        stats_field="pts_half_ppr",
        injury_only_directory_fallback=True,
    )

    assert [candidate["player_id"] for candidate in rankings] == ["backup"]
    assert rankings[0]["preseason"] is True
    assert "preseason availability" in format_free_agents_message(1, rankings)


def test_healthy_first_or_second_string_blocks_deep_injury_replacement():
    rankings = rank_free_agents(
        weekly_stats=[],
        rosters=[{"players": ["injured"]}],
        players_by_id={
            "starter": {"name": "Healthy Starter", "position": "RB", "team": "TST", "depth_chart_order": 1, "depth_chart_position": "RB"},
            "injured": {"name": "Hurt Backup", "position": "RB", "team": "TST", "injury_status": "Q", "depth_chart_order": 2, "depth_chart_position": "RB"},
            "deep": {"name": "Deep Back", "position": "RB", "team": "TST", "depth_chart_order": 4, "depth_chart_position": "RB"},
        },
        stats_field="pts_half_ppr",
        injury_only_directory_fallback=True,
    )

    assert rankings == []


def test_preseason_uses_a_separate_idempotency_flag():
    sleeper = FreeAgentSleeper()
    sleeper.stats[3] = sleeper.stats[2]
    sleeper.nfl_state = lambda: {"season": "2026", "week": 3, "season_type": "pre"}
    storage = InMemoryStorage()

    result = run_free_agents(
        sleeper=sleeper,
        storage=storage,
        league_id="league",
        season=None,
        week=None,
        send_message=lambda _: None,
    )

    # The sample has regular-week stats, but an NFL preseason state must never
    # reserve the regular-season report flag for the same numeric week.
    assert result.posted_count == 1
    assert sleeper.projection_calls == [("2026", 3)]
    flags = storage.get_weekly_flags("2026", 3)
    assert flags["preseason_free_agents_posted"] is True
    assert "free_agents_posted" not in flags


class FreeAgentSleeper:
    def __init__(self, scoring=BASE_SCORING):
        self.scoring = scoring
        self.projection_calls = []
        self.stats = {1: [stat("breakout", "WR", 8, "Young Star", 1), stat("baseline", "WR", 6, "Base Line")], 2: [stat("breakout", "WR", 22, "Young Star", 1), stat("baseline", "WR", 6, "Base Line")]}

    def league(self, league_id): return {"scoring_settings": self.scoring}
    def rosters(self, league_id): return [{"players": []}]
    def players(self): return {"breakout": {"first_name": "Young", "last_name": "Star", "position": "WR", "team": "TST", "years_exp": 1}, "baseline": {"first_name": "Base", "last_name": "Line", "position": "WR", "team": "TST", "years_exp": 3}}
    def weekly_stats(self, season, week): return self.stats[week]
    def weekly_projections(self, season, week):
        self.projection_calls.append((season, week))
        return self.stats[week]
    def nfl_state(self): return {"season": "2026", "week": 2, "season_type": "regular"}


def test_handler_posts_once_and_skips_custom_scoring():
    storage = InMemoryStorage()
    messages: list[BotMessage] = []
    sleeper = FreeAgentSleeper()
    result = run_free_agents(sleeper=sleeper, storage=storage, league_id="league", season="2026", week=2, prior_weeks=[1], send_message=messages.append)

    assert result.posted_count == 1
    assert messages[0].channel_key == "standout_free_agents"
    assert storage.get_weekly_flags("2026", 2)["free_agents_posted"] is True
    assert run_free_agents(sleeper=sleeper, storage=storage, league_id="league", season="2026", week=2, prior_weeks=[1], send_message=messages.append).skipped_count == 1
    assert run_free_agents(sleeper=FreeAgentSleeper({**BASE_SCORING, "pass_td": 6}), storage=InMemoryStorage(), league_id="league", season="2026", week=2, send_message=messages.append).skipped_count == 1


def test_failed_free_agent_delivery_releases_its_atomic_reservation():
    storage = InMemoryStorage()
    with pytest.raises(RuntimeError, match="Discord failed"):
        run_free_agents(
            sleeper=FreeAgentSleeper(), storage=storage, league_id="league", season="2026", week=2,
            prior_weeks=[1], send_message=lambda _: (_ for _ in ()).throw(RuntimeError("Discord failed")),
        )

    messages = []
    retry = run_free_agents(
        sleeper=FreeAgentSleeper(), storage=storage, league_id="league", season="2026", week=2,
        prior_weeks=[1], send_message=messages.append,
    )
    assert retry.posted_count == 1


def test_regular_season_stats_failure_fails_without_marking_the_report_posted():
    sleeper = FreeAgentSleeper()
    sleeper.weekly_stats = lambda *_: (_ for _ in ()).throw(RuntimeError("Sleeper unavailable"))
    storage = InMemoryStorage()

    with pytest.raises(RuntimeError, match="Sleeper unavailable"):
        run_free_agents(
            sleeper=sleeper, storage=storage, league_id="league", season="2026", week=2, send_message=lambda _: None,
        )

    assert storage.get_weekly_flags("2026", 2).get("free_agents_posted") is None


def test_scheduled_free_agents_skip_postseason_and_offseason():
    sleeper = FreeAgentSleeper()
    sleeper.nfl_state = lambda: {"season": "2026", "season_type": "off", "leg": 18}

    result = run_free_agents(
        sleeper=sleeper, storage=InMemoryStorage(), league_id="league", season=None, week=None, send_message=lambda _: None,
    )

    assert result.skipped_count == 1


def test_lambda_handler_loads_f2_ssm_configuration(monkeypatch):
    prefix = "/benchreporter/dev"
    monkeypatch.setenv("SSM_PARAMETER_PREFIX", prefix)
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "state-table")
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setattr(free_agents, "_ssm_values", lambda _: {
        f"{prefix}/sleeper-league-id": "league",
        f"{prefix}/discord-bot-token": "token",
        f"{prefix}/discord-channel-standout-free-agents": "channel",
    })
    monkeypatch.setattr(free_agents, "DynamoDBStorage", lambda _: object())
    monkeypatch.setattr(free_agents, "SleeperClient", lambda **_: object())
    monkeypatch.setattr(free_agents, "DiscordClient", lambda **_: object())

    captured = {}
    def fake_run(**kwargs):
        captured.update(kwargs)
        return HandlerResult(posted_count=1, skipped_count=2)
    monkeypatch.setattr(free_agents, "run_free_agents", fake_run)

    assert free_agents.lambda_handler({}, {}) == {"posted": 1, "skipped": 2}
    assert captured["league_id"] == "league"
    assert captured["week"] is None
