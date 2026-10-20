from trading_agent.replay import demo


def test_identical_events_produce_identical_journal_and_results(tmp_path):
    first = demo(tmp_path / "first")
    second = demo(tmp_path / "second")
    assert first == second
    assert first["snapshot"]["cash"] == "25099.11"
