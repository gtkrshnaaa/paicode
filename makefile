.PHONY: run export-all install

install:
	python3 -m venv venv
	. venv/bin/activate; pip install -r requirements.txt

run:
	# Note: This target is a placeholder. 
	# The main entry point is the 'pai' command after installation.
	@echo "To run the application, install it with 'pip install -e .' and then use the 'pai' command."
	@echo "Example: 'pai auto'"

export-all:
	@mkdir -p z_project_list
	@echo "Exporting project files to z_project_list/listing.txt..."
	@rm -f z_project_list/listing.txt
	@for f in $$(find . -type f \
		-not -path '*/\.*' \
		-not -path './venv/*' \
		-not -path '*/__pycache__/*' \
		-not -path '*.egg-info/*' \
		-not -path './z_project_list/*' \
		-not -name "poetry.lock" \
		-not -name ".gitkeep" \
		| sort); do \
			echo "=== $$f ===" >> z_project_list/listing.txt; \
			cat $$f >> z_project_list/listing.txt; \
			echo "\n" >> z_project_list/listing.txt; \
	done
	@echo "Export complete."