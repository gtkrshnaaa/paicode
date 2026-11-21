from pathlib import Path

from .helpers import make_registry, run_command, write_file


def test_node_package_and_test_runner(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "package.json",
        '{"name":"matrix-node","version":"1.0.0","type":"module",'
        '"scripts":{"test":"node --test","start":"node src/cli.js"}}',
    )
    write_file(
        registry,
        "src/math.js",
        "export function add(left, right) {\n"
        "  return left + right;\n"
        "}\n\n"
        "export function unique(values) {\n"
        "  return [...new Set(values)];\n"
        "}\n",
    )
    write_file(
        registry,
        "src/cli.js",
        "import { add } from './math.js';\n"
        "console.log(add(Number(process.argv[2]), Number(process.argv[3])));\n",
    )
    write_file(
        registry,
        "test/math.test.js",
        "import test from 'node:test';\n"
        "import assert from 'node:assert/strict';\n"
        "import { add, unique } from '../src/math.js';\n\n"
        "test('adds numbers', () => assert.equal(add(2, 3), 5));\n"
        "test('deduplicates values', () => assert.deepEqual(unique([1, 1, 2]), [1, 2]));\n",
    )
    run_command(registry, "npm test", timeout=180)
    output = run_command(registry, "node src/cli.js 7 8")
    assert output.strip().endswith("15")
