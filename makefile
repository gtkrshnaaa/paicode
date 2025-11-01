.PHONY: run export-all install venv-activate setup install-cli uninstall-cli

install:
	@if [ ! -d .venv ]; then \
		echo "[install] Creating virtual environment at .venv"; \
		python3 -m venv .venv; \
	else \
		echo "[install] Reusing existing virtual environment at .venv"; \
	fi
	. .venv/bin/activate; python -m pip install --upgrade pip setuptools wheel
	. .venv/bin/activate; pip install -r requirements.txt
	. .venv/bin/activate; pip install -e .

run:
	. .venv/bin/activate; python -m paicode.cli auto

export-all:
	@mkdir -p z_project_list
	@echo "Exporting project files to z_project_list/listing.txt..."
	@rm -f z_project_list/listing.txt
	@for f in $$(find . -type f \
		-not -path '*/\.*' \
		-not -path '*/__pycache__/*' \
		-not -path '*.egg-info/*' \
		-not -path './z_project_list/*' \
		-not -name ".gitkeep" \
		| sort); do \
			echo "=== $$f ===" >> z_project_list/listing.txt; \
			cat $$f >> z_project_list/listing.txt; \
			echo "\n" >> z_project_list/listing.txt; \
	done
	@echo "Export complete."

venv-activate:
	@echo "To activate the virtual environment, run:"
	@echo "  source .venv/bin/activate"

setup: install install-cli
	@echo "Pai CLI installed. Ensure $$HOME/.local/bin is in your PATH, then run: pai"

install-cli:
	@mkdir -p $(HOME)/.local/bin
	@echo "Installing launcher to $(HOME)/.local/bin/pai"
	@echo '#!/usr/bin/env bash' > $(HOME)/.local/bin/pai
	@echo '# Suppress noisy gRPC/absl logs' >> $(HOME)/.local/bin/pai
	@echo 'export GRPC_VERBOSITY="NONE"' >> $(HOME)/.local/bin/pai
	@echo 'export GRPC_LOG_SEVERITY="ERROR"' >> $(HOME)/.local/bin/pai
	@echo 'export ABSL_LOGGING_MIN_LOG_LEVEL="3"' >> $(HOME)/.local/bin/pai
	@echo 'export GLOG_minloglevel="3"' >> $(HOME)/.local/bin/pai
	@echo 'export GOOGLE_CLOUD_DISABLE_GRPC="true"' >> $(HOME)/.local/bin/pai
	@echo 'export GRPC_ENABLE_FORK_SUPPORT="false"' >> $(HOME)/.local/bin/pai
	@echo 'SCRIPT_DIR="$$(cd "$$(dirname "$${BASH_SOURCE[0]}")" && pwd)"' >> $(HOME)/.local/bin/pai
	@echo 'APPDIR="$(shell pwd)"' >> $(HOME)/.local/bin/pai
	@echo 'VENVDIR="$$APPDIR/.venv"' >> $(HOME)/.local/bin/pai
	@echo 'PY="$$VENVDIR/bin/python"' >> $(HOME)/.local/bin/pai
	@echo '# Redirect stderr to suppress remaining warnings' >> $(HOME)/.local/bin/pai
	@echo 'if [ -x "$$VENVDIR/bin/pai" ]; then' >> $(HOME)/.local/bin/pai
	@echo '  exec "$$VENVDIR/bin/pai" "$$@" 2>/dev/null' >> $(HOME)/.local/bin/pai
	@echo 'elif [ -x "$$PY" ]; then' >> $(HOME)/.local/bin/pai
	@echo '  exec "$$PY" -m paicode.cli "$$@" 2>/dev/null' >> $(HOME)/.local/bin/pai
	@echo 'else' >> $(HOME)/.local/bin/pai
	@echo '  exec python3 -m paicode.cli "$$@" 2>/dev/null' >> $(HOME)/.local/bin/pai
	@echo 'fi' >> $(HOME)/.local/bin/pai
	@chmod +x $(HOME)/.local/bin/pai
	@# Ensure ~/.local/bin is in PATH (append to ~/.bashrc if missing)
	@if [ -f $(HOME)/.bashrc ]; then \
		grep -qxF 'export PATH="$$HOME/.local/bin:$$PATH"' $(HOME)/.bashrc || printf '\n# Added by pai install-cli\nexport PATH="$$HOME/.local/bin:$$PATH"\n' >> $(HOME)/.bashrc; \
	fi
	@echo "Ensured PATH includes $$HOME/.local/bin in $$HOME/.bashrc. Run: 'source $$HOME/.bashrc' or open a new terminal."
	@echo "Done. Ensure $(HOME)/.local/bin is in your PATH. Try running: pai --help"

uninstall-cli:
	@rm -f $(HOME)/.local/bin/pai
	@# Remove PATH line added by install-cli (safe if absent)
	@sed -i '/^# Added by pai install-cli$/d' $(HOME)/.bashrc || true
	@sed -i '/^export PATH="\$HOME\/\.local\/bin:\$PATH"$/d' $(HOME)/.bashrc || true
	@echo "Launcher removed: $(HOME)/.local/bin/pai"
