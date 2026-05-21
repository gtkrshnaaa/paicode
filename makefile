.PHONY: run export-all install venv-activate setup install-cli uninstall-cli list core-list

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

# Listing Target
list:
	@mkdir -p z_listing
	@echo "================================================================================" > z_listing/listing.txt
	@echo "PAICODE PROJECT CODEBASE LISTING" >> z_listing/listing.txt
	@echo "Generated on: $$(date)" >> z_listing/listing.txt
	@echo "================================================================================" >> z_listing/listing.txt
	@echo "" >> z_listing/listing.txt
	@echo "This document contains a comprehensive listing of all tracked source code files" >> z_listing/listing.txt
	@echo "within the Paicode project, including docs, main application packages, and configs." >> z_listing/listing.txt
	@echo "Paicode is a command-line based agentic AI tool for software development and automation." >> z_listing/listing.txt
	@echo "" >> z_listing/listing.txt
	@echo "Directory Structure Overview:" >> z_listing/listing.txt
	@echo "1. paicode: Source code for Paicode's agent, CLI, LLM connection, UI, and workspace." >> z_listing/listing.txt
	@echo "2. docs: Project documentation including architecture, features, and usage." >> z_listing/listing.txt
	@echo "3. Root files: Build, dependency, licensing, and setup configurations." >> z_listing/listing.txt
	@echo "" >> z_listing/listing.txt
	@echo "================================================================================" >> z_listing/listing.txt
	@echo "" >> z_listing/listing.txt
	@for f in $$(git ls-files | sort); do \
		echo "FILE: $$f" >> z_listing/listing.txt; \
		echo "--------------------------------------------------------------------------------" >> z_listing/listing.txt; \
		cat "$$f" >> z_listing/listing.txt; \
		echo -e "\n\n" >> z_listing/listing.txt; \
	done
	@echo "Codebase listing generated at z_listing/listing.txt"

# Core Listing Target
core-list:
	@mkdir -p z_listing
	@echo "================================================================================" > z_listing/core_listing.txt
	@echo "PAICODE CORE CODEBASE LISTING" >> z_listing/core_listing.txt
	@echo "Generated on: $$(date)" >> z_listing/core_listing.txt
	@echo "================================================================================" >> z_listing/core_listing.txt
	@echo "" >> z_listing/core_listing.txt
	@echo "This document contains a listing of all source code files within the paicode/ directory." >> z_listing/core_listing.txt
	@echo "Paicode is a command-line based agentic AI tool for software development and automation." >> z_listing/core_listing.txt
	@echo "" >> z_listing/core_listing.txt
	@echo "================================================================================" >> z_listing/core_listing.txt
	@echo "" >> z_listing/core_listing.txt
	@for f in $$(git ls-files paicode | sort); do \
		echo "FILE: $$f" >> z_listing/core_listing.txt; \
		echo "--------------------------------------------------------------------------------" >> z_listing/core_listing.txt; \
		cat "$$f" >> z_listing/core_listing.txt; \
		echo -e "\n\n" >> z_listing/core_listing.txt; \
	done
	@echo "Core codebase listing generated at z_listing/core_listing.txt"
