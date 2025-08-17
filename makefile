.PHONY: run export-all install

install:
	python3 -m venv .venv
	. .venv/bin/activate; pip install -r requirements.txt

run:
	. .venv/bin/activate; python3 main.py

export-all:
	@mkdir -p z_project_list
	@echo "Mengekspor semua file ke z_project_list/listing.txt"
	@rm -f z_project_list/listing.txt
	@for f in $$(find . -type f \
		-not -path '*/\.*' \
		-not -path '*/__pycache__/*' \
		-not -name ".gitkeep" \
		| sort); do \
			echo "=== $$f ===" >> z_project_list/listing.txt; \
			cat $$f >> z_project_list/listing.txt; \
			echo "\n" >> z_project_list/listing.txt; \
	done