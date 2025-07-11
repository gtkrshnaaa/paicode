LISTING_FILE := z_project_list/listing_all_components.txt

list:
	@echo "Generating safe file listing..."
	@mkdir -p z_project_list
	@rm -f $(LISTING_FILE)

	@find . \
		-type f \
		-not -path "./venv/*" \
		-not -path "./.git/*" \
		-not -name ".env" \
		-not -name "*.pyc" \
		-not -name "*.pyo" \
		-not -name "*.so" \
		-not -name "*.swp" \
		-not -name "*.png" \
		-not -name "*.jpg" \
		-not -name "*.jpeg" \
		-not -name "*.gif" \
		-not -name "*.zip" \
		-not -name "*.db" \
		-not -name "*.sqlite" \
		-not -name "*.pdf" \
		-not -name "*.exe" \
		-not -name "*.out" \
		-not -name "*.bin" \
		-not -name "*.a" \
		-not -name "*.o" \
		-not -name "*.tar" \
		-not -name "*.gz" \
		-not -name "*.tgz" \
		-not -name "*.ico" \
		| sort \
		| while read file; do \
			echo "FILE START: $$file" >> $(LISTING_FILE); \
			cat "$$file" >> $(LISTING_FILE); \
			echo "FILE END: $$file" >> $(LISTING_FILE); \
			echo "" >> $(LISTING_FILE); \
		done
	@echo "--- END OF LISTING ---" >> $(LISTING_FILE)
	@echo "Listing saved to $(LISTING_FILE)"
