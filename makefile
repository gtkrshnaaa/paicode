.PHONY: setup dev test run uninstall

setup:
	./install.sh

dev:
	./install.sh --dev

test:
	.venv/bin/pytest -q

run:
	.venv/bin/python -m paicode

uninstall:
	./install.sh --uninstall
