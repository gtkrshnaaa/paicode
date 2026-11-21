.PHONY: setup dev test matrix run uninstall

setup:
	./install.sh

dev:
	./install.sh --dev

test:
	.venv/bin/pytest -q

matrix:
	.venv/bin/pytest -q tests/coding tests/test_shell_execution.py tests/test_shell_sandbox.py tests/test_agent_coding_loop.py

run:
	.venv/bin/python -m paicode

uninstall:
	./install.sh --uninstall
