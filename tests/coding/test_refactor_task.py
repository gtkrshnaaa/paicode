from pathlib import Path

from .helpers import make_registry, run_command, write_file


def test_multi_file_rename_refactor(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(registry, "shop/__init__.py", "")
    write_file(
        registry,
        "shop/pricing.py",
        "TAX_RATE = 0.1\n\n"
        "def calculate_total(subtotal):\n"
        "    return round(subtotal * (1 + TAX_RATE), 2)\n",
    )
    write_file(
        registry,
        "shop/checkout.py",
        "from .pricing import calculate_total\n\n"
        "def checkout(subtotal):\n"
        "    return {\"total\": calculate_total(subtotal)}\n",
    )
    write_file(
        registry,
        "test_shop.py",
        "import unittest\n"
        "from shop.checkout import checkout\n"
        "from shop.pricing import calculate_total\n\n"
        "class ShopTests(unittest.TestCase):\n"
        "    def test_total(self):\n"
        "        self.assertEqual(calculate_total(100), 110)\n\n"
        "    def test_checkout(self):\n"
        "        self.assertEqual(checkout(50), {'total': 55.0})\n",
    )
    run_command(registry, "python3 -m unittest -q")

    for path, old, new in [
        (
            "shop/pricing.py",
            "def calculate_total(subtotal):",
            "def compute_total(subtotal):",
        ),
        (
            "shop/checkout.py",
            "from .pricing import calculate_total",
            "from .pricing import compute_total",
        ),
        (
            "shop/checkout.py",
            "calculate_total(subtotal)",
            "compute_total(subtotal)",
        ),
        (
            "test_shop.py",
            "from shop.pricing import calculate_total",
            "from shop.pricing import compute_total",
        ),
        (
            "test_shop.py",
            "calculate_total(100)",
            "compute_total(100)",
        ),
    ]:
        result = registry.execute(
            "edit",
            {"path": path, "old_string": old, "new_string": new},
        )
        assert result.ok, result.output

    output = run_command(registry, "python3 -m unittest -q")
    assert "failed" not in output.lower()
    assert "calculate_total" not in (project / "shop/pricing.py").read_text(encoding="utf-8")
