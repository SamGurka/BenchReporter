from sleeper_discord_bot.domain.scoring import detect_scoring_profile


def test_detects_committed_sample_as_custom_scoring(sample_league):
    profile = detect_scoring_profile(sample_league["scoring_settings"])

    assert profile.name == "custom"
    assert profile.stats_field is None
    assert profile.supported_for_generic_stats is False
    assert profile.reason


def test_detects_standard_ppr_profiles():
    base = {
        "pass_yd": 0.04,
        "pass_td": 4,
        "pass_int": -2,
        "rush_yd": 0.1,
        "rush_td": 6,
        "rec_yd": 0.1,
        "rec_td": 6,
        "fum_lost": -2,
    }

    assert detect_scoring_profile({**base, "rec": 0}).stats_field == "pts_std"
    assert detect_scoring_profile({**base, "rec": 0.5}).stats_field == "pts_half_ppr"
    assert detect_scoring_profile({**base, "rec": 1}).stats_field == "pts_ppr"


def test_ignores_kicker_defense_and_idp_scoring_for_free_agent_profiles():
    scoring = {
        "pass_yd": 0.04,
        "pass_td": 4,
        "pass_int": -2,
        "pass_2pt": 2,
        "rush_yd": 0.1,
        "rush_td": 6,
        "rush_2pt": 2,
        "rec_yd": 0.1,
        "rec_td": 6,
        "rec_2pt": 2,
        "rec": 0.5,
        "fum_lost": -2,
        "fgm_40_49": 4,
        "xpm": 1,
        "sack": 1,
        "pts_allow_0": 5,
        "yds_allow_0_100": 5,
        "idp_pass_def_3p": 3,
        "tkl_solo": 1,
    }

    profile = detect_scoring_profile(scoring)

    assert profile.name == "half_ppr"
    assert profile.stats_field == "pts_half_ppr"


def test_keeps_nonstandard_offensive_scoring_custom():
    scoring = {
        "pass_yd": 0.04,
        "pass_td": 6,
        "pass_int": -2,
        "rush_yd": 0.1,
        "rush_td": 6,
        "rec_yd": 0.1,
        "rec_td": 6,
        "fum_lost": -2,
        "rec": 0.5,
    }

    assert detect_scoring_profile(scoring).name == "custom"
