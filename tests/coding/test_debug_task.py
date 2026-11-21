from pathlib import Path

from .helpers import make_registry, run_command, write_file


def test_debug_failing_test_and_rerun(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "stats.py",
        "def mean(values):\n"
        "    return sum(values) / (len(values) - 1)\n",
    )
    write_file(
        registry,
        "test_stats.py",
        "import unittest\n"
        "from stats import mean\n\n"
        "class StatsTests(unittest.TestCase):\n"
        "    def test_mean(self):\n"
        "        self.assertEqual(mean([2, 4, 6]), 4)\n\n"
        "    def test_empty(self):\n"
        "        with self.assertRaises(ValueError):\n"
        "            mean([])\n",
    )
    failure = registry.execute("bash", {"command": "python3 -m unittest -q"})
    assert not failure.ok
    assert "FAILED" in failure.output
    assert "6.0 != 4" in failure.output

    result = registry.execute(
        "edit",
        {
            "path": "stats.py",
            "old_string": "def mean(values):\n    return sum(values) / (len(values) - 1)\n",
            "new_string": (
                "def mean(values):\n"
                "    if not values:\n"
                "        raise ValueError('mean requires at least one value')\n"
                "    return sum(values) / len(values)\n"
            ),
        },
    )
    assert result.ok, result.output
    output = run_command(registry, "python3 -m unittest -q")
    assert "failed" not in output.lower()
