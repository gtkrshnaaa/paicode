import os
import shutil
from pathlib import Path

import pytest

from paicode.tools.shell import ShellTools

from .helpers import make_registry, run_command, write_file


@pytest.mark.skipif(shutil.which("go") is None, reason="go is not installed")
def test_go_module_task(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(registry, "go.mod", "module example.com/matrix\n\ngo 1.22\n")
    write_file(
        registry,
        "math.go",
        "package matrix\n\n"
        "func Add(left, right int) int {\n"
        "    return left + right\n"
        "}\n",
    )
    write_file(
        registry,
        "math_test.go",
        "package matrix\n\nimport \"testing\"\n\n"
        "func TestAdd(t *testing.T) {\n"
        "    if Add(2, 3) != 5 {\n"
        "        t.Fatal(\"unexpected sum\")\n"
        "    }\n"
        "}\n",
    )
    run_command(registry, "go test ./...")


@pytest.mark.skipif(shutil.which("cargo") is None, reason="cargo is not installed")
def test_rust_crate_task(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "Cargo.toml",
        "[package]\nname = \"matrix\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
    )
    write_file(
        registry,
        "src/lib.rs",
        "pub fn add(left: i32, right: i32) -> i32 {\n"
        "    left + right\n"
        "}\n\n"
        "#[cfg(test)]\n"
        "mod tests {\n"
        "    use super::*;\n"
        "    #[test]\n"
        "    fn adds() {\n"
        "        assert_eq!(add(2, 3), 5);\n"
        "    }\n"
        "}\n",
    )
    run_command(registry, "cargo test --quiet")


@pytest.mark.skipif(shutil.which("tsc") is None, reason="tsc is not installed")
def test_typescript_compile_task(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "tsconfig.json",
        '{"compilerOptions":{"strict":true,"target":"ES2022","module":"ESNext",'
        '"moduleResolution":"Bundler","noEmit":true},"include":["src"]}',
    )
    write_file(
        registry,
        "src/math.ts",
        "export function add(left: number, right: number): number {\n"
        "  return left + right;\n"
        "}\n",
    )
    write_file(
        registry,
        "src/index.ts",
        "import { add } from './math.js';\n"
        "const total: number = add(2, 3);\n"
        "console.log(total);\n",
    )
    run_command(registry, "tsc --noEmit")


@pytest.mark.skipif(os.getenv("PAICODE_TEST_DOCKER") != "1", reason="docker matrix is opt-in")
@pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed")
def test_docker_image_task(project: Path, stats, monkeypatch):
    monkeypatch.setenv("PAICODE_SHELL_SANDBOX", "direct")
    registry = make_registry(project, stats)
    write_file(registry, "app.py", "print('docker-ok')\n")
    write_file(
        registry,
        "Dockerfile",
        "FROM python:3.12-slim\nCOPY app.py /app.py\nCMD [\"python\", \"/app.py\"]\n",
    )
    tools = ShellTools(project, stats)
    assert tools.run("docker build -q -t paicode-matrix .", timeout=300).ok
    output = tools.run("docker run --rm paicode-matrix", timeout=120)
    assert output.ok, output.output
    assert "docker-ok" in output.output
