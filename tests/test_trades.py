from sleeper_discord_bot.domain.trades import completed_trades, trade_faab_moves, trade_pick_moves, trade_player_moves, trade_roster_ids


def test_filters_completed_trades(week01_transactions):
    trades = completed_trades(week01_transactions)

    assert len(trades) == 17
    assert all(trade["type"] == "trade" for trade in trades)
    assert all(trade["status"] == "complete" for trade in trades)


def test_parses_trade_rosters_and_player_moves(week01_transactions):
    trade = completed_trades(week01_transactions)[0]

    assert trade_roster_ids(trade) == [2, 5]
    assert trade_player_moves(trade) == {
        2: {"adds": ["12489"], "drops": ["5859"]},
        5: {"adds": ["5859"], "drops": ["12489"]},
    }


def test_parses_trade_draft_picks(week01_transactions):
    trade = completed_trades(week01_transactions)[0]

    assert trade_pick_moves(trade) == {
        2: ["2027 round 2"],
        5: ["2027 round 3"],
    }


def test_parses_trade_faab():
    assert trade_faab_moves({"waiver_budget": [{"receiver_id": 2, "amount": 15}]}) == {2: ["$15 FAAB"]}
