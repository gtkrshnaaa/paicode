from pathlib import Path

from .helpers import make_registry, run_command, write_file


def test_c_project_with_make(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "include/math_ops.h",
        "#ifndef MATH_OPS_H\n"
        "#define MATH_OPS_H\n"
        "int add(int left, int right);\n"
        "int factorial(int value);\n"
        "#endif\n",
    )
    write_file(
        registry,
        "src/math_ops.c",
        '#include "math_ops.h"\n\n'
        "int add(int left, int right) {\n"
        "    return left + right;\n"
        "}\n\n"
        "int factorial(int value) {\n"
        "    int result = 1;\n"
        "    for (int index = 2; index <= value; index++) {\n"
        "        result *= index;\n"
        "    }\n"
        "    return result;\n"
        "}\n",
    )
    write_file(
        registry,
        "tests/test_math.c",
        '#include "math_ops.h"\n'
        "#include <assert.h>\n\n"
        "int main(void) {\n"
        "    assert(add(2, 3) == 5);\n"
        "    assert(factorial(5) == 120);\n"
        "    return 0;\n"
        "}\n",
    )
    write_file(
        registry,
        "Makefile",
        "CC ?= cc\n"
        "CFLAGS ?= -std=c11 -Wall -Wextra -Werror -Iinclude\n\n"
        "test: build/test_math\n"
        "\t./build/test_math\n\n"
        "build/test_math: src/math_ops.c tests/test_math.c include/math_ops.h\n"
        "\tmkdir -p build\n"
        "\t$(CC) $(CFLAGS) src/math_ops.c tests/test_math.c -o build/test_math\n\n"
        "clean:\n"
        "\trm -rf build\n",
    )
    run_command(registry, "make test")
