# Makefile for EthioSurv-RiskToolbox QGIS Plugin

.PHONY: compile clean zip release test

# Define variables
PLUGIN_DIR = ethiosurv_risk_toolbox
UI_FILE = $(PLUGIN_DIR)/ui/main_dialog.ui
UI_PY_FILE = $(PLUGIN_DIR)/ui/main_dialog_ui.py
RESOURCE_FILE = $(PLUGIN_DIR)/resources.qrc
RESOURCE_PY_FILE = $(PLUGIN_DIR)/resources.py

# Default command to run when you just type 'make'
default: compile

# Compiles the .ui and .qrc files to Python files
compile:
	@echo "Compiling UI and resource files..."
	pyuic5 -x $(UI_FILE) -o $(UI_PY_FILE)
	pyrcc5 $(RESOURCE_FILE) -o $(RESOURCE_PY_FILE)
	@echo "Compilation complete."

# Cleans up compiled files and build artifacts
clean:
	@echo "Cleaning up compiled files..."
	rm -f $(UI_PY_FILE)
	rm -f $(RESOURCE_PY_FILE)
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Creates a zip file for deployment
zip: clean compile
	@echo "Creating plugin zip file..."
	git archive --format=zip --prefix=$(PLUGIN_DIR)/ -o $(PLUGIN_DIR).zip HEAD
	@echo "Zip file created: $(PLUGIN_DIR).zip"

# Runs tests (placeholder for when you add tests)
test:
	@echo "Running tests..."
	# pytest $(PLUGIN_DIR)/tests/

# A note on how to release
release:
	@echo "To create a release, use Git tags:"
	@echo "1. git tag vX.Y.Z"
	@echo "2. git push origin vX.Y.Z"