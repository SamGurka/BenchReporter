from sleeper_discord_bot.domain.team_names import roster_display_names


def test_resolves_roster_ids_to_team_names():
    rosters = [
        {"roster_id": 1, "owner_id": "user_01"},
        {"roster_id": 2, "owner_id": "missing"},
    ]
    users = [{"user_id": "user_01", "display_name": "Manager 1", "metadata": {"team_name": "Team 1"}}]

    assert roster_display_names(rosters, users) == {
        1: "Team 1",
        2: "Roster 2",
    }

