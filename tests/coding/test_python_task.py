from pathlib import Path

from .helpers import make_registry, run_command, write_file


def test_python_cli_and_unittest(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "calculator.py",
        "def add(a, b):\n"
        "    return a + b\n\n"
        "def divide(a, b):\n"
        "    if b == 0:\n"
        "        raise ValueError('division by zero')\n"
        "    return a / b\n",
    )
    write_file(
        registry,
        "cli.py",
        "import argparse\n"
        "from calculator import add, divide\n\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('left', type=float)\n"
        "parser.add_argument('right', type=float)\n"
        "parser.add_argument('--divide', action='store_true')\n"
        "args = parser.parse_args()\n"
        "print(divide(args.left, args.right) if args.divide else add(args.left, args.right))\n",
    )
    write_file(
        registry,
        "test_calculator.py",
        "import unittest\n"
        "from calculator import add, divide\n\n"
        "class CalculatorTests(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n\n"
        "    def test_divide(self):\n"
        "        self.assertEqual(divide(9, 3), 3)\n\n"
        "    def test_divide_by_zero(self):\n"
        "        with self.assertRaises(ValueError):\n"
        "            divide(1, 0)\n",
    )
    run_command(registry, "python3 -m unittest -q")
    run_command(registry, "python3 -m compileall -q .")
    output = run_command(registry, "python3 cli.py 4 6")
    assert output.strip().endswith("10.0")
