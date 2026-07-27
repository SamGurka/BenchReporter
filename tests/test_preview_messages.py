from tests.support.preview_messages import print_trade_messages, print_weekly_roundup


def test_preview_weekly_roundup_prints_message(capsys):
    print_weekly_roundup(16)

    output = capsys.readouterr().out

    assert "**Week 16 Roundup**" in output
    assert "**Standout Starters**" in output
    assert "Player " not in output


def test_preview_trades_prints_limited_messages(capsys):
    print_trade_messages(1, limit=1)

    output = capsys.readouterr().out

    assert output.count("**Trade Alert:") == 1
    assert "receives:" in output
