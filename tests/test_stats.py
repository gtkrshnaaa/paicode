from paicode.core.stats import UsageStats


def test_usage_and_file_counters():
    stats = UsageStats()
    stats.record_usage(10, 5, 15)
    stats.record_usage(20, 10, 30)
    stats.mark("read")
    stats.mark("created", 2)
    stats.mark("edited")
    stats.mark("command", 3)
    assert stats.prompt_tokens == 30
    assert stats.completion_tokens == 15
    assert stats.total_tokens == 45
    assert stats.requests == 2
    assert stats.files_read == 1
    assert stats.files_created == 2
    assert stats.files_edited == 1
    assert stats.commands == 3
    assert "tokens 30/15/45" in stats.summary()
