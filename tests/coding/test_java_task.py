import shutil
from pathlib import Path

import pytest

from .helpers import make_registry, run_command, write_file

pytestmark = pytest.mark.skipif(
    shutil.which("javac") is None,
    reason="javac is not installed",
)


def test_java_compile_and_run(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "Matrix.java",
        "import java.util.List;\n"
        "public final class Matrix {\n"
        "    static int total(List<Integer> values) {\n"
        "        return values.stream().mapToInt(Integer::intValue).sum();\n"
        "    }\n"
        "    public static void main(String[] args) {\n"
        "        assert total(List.of(1, 2, 3, 4)) == 10;\n"
        "        System.out.println(\"java-ok\");\n"
        "    }\n"
        "}\n",
    )
    run_command(registry, "javac -d out Matrix.java")
    output = run_command(registry, "java -ea -cp out Matrix")
    assert "java-ok" in output
