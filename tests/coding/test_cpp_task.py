from pathlib import Path

from .helpers import make_registry, run_command, write_file


def test_cpp_project_with_cmake(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "CMakeLists.txt",
        "cmake_minimum_required(VERSION 3.16)\n"
        "project(matrix_cpp CXX)\n"
        "set(CMAKE_CXX_STANDARD 20)\n"
        "set(CMAKE_CXX_STANDARD_REQUIRED ON)\n"
        "add_executable(matrix src/main.cpp)\n"
        "target_compile_options(matrix PRIVATE -Wall -Wextra -Werror)\n"
        "enable_testing()\n"
        "add_test(NAME matrix COMMAND matrix)\n",
    )
    write_file(
        registry,
        "src/main.cpp",
        "#include <cassert>\n"
        "#include <numeric>\n"
        "#include <vector>\n\n"
        "int total(const std::vector<int>& values) {\n"
        "    return std::accumulate(values.begin(), values.end(), 0);\n"
        "}\n\n"
        "int main() {\n"
        "    assert(total({1, 2, 3, 4}) == 10);\n"
        "    return 0;\n"
        "}\n",
    )
    run_command(registry, "cmake -S . -B build -DCMAKE_BUILD_TYPE=Release")
    run_command(registry, "cmake --build build --parallel 2")
    run_command(registry, "ctest --test-dir build --output-on-failure")
