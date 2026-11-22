.PHONY: setup dev test matrix run serve bench release uninstall

setup:
	./install.sh

dev:
	./install.sh --dev

test:
	.venv/bin/pytest -q

matrix:
	.venv/bin/pytest -q tests/coding tests/test_shell_execution.py tests/test_shell_sandbox.py tests/test_agent_coding_loop.py tests/test_multi_agent.py tests/test_multi_agent_concurrency.py tests/test_multi_agent_contract.py tests/test_multi_agent_defaults.py

serve:
	.venv/bin/python -m paicode serve

bench:
	.venv/bin/python -m paicode bench benchmarks/smoke.json --mode both

release:
	PYTHON=.venv/bin/python bash scripts/release.sh

run:
	.venv/bin/python -m paicode

uninstall:
	./install.sh --uninstall
