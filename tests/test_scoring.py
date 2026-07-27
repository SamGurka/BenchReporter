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

