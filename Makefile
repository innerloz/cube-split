.PHONY: all install-generator install-viewer generate serve clean help

# Default target
all: help

# Install dependencies
install-generator: ## Install Python dependencies for the generator
	@echo "Installing generator dependencies..."
	python3.12 -m venv generator/venv
	. generator/venv/bin/activate && pip install -r generator/requirements.txt

install-viewer: ## Install Node.js dependencies for the viewer
	@echo "Installing viewer dependencies..."
	cd viewer && npm install

install: install-generator install-viewer ## Install all dependencies

# Run tasks
generate: ## Run the Python generator to create GLB models
	@echo "Generating models..."
	. generator/venv/bin/activate && cd generator && python generate.py

serve: ## Start the Vite development server for the viewer
	@echo "Starting viewer..."
	cd viewer && npm run dev

# Cleanup
clean: ## Remove generated models, virtual environment, and node_modules
	@echo "Cleaning up..."
	rm -rf generator/venv
	rm -rf viewer/node_modules
	rm -f viewer/public/*.glb

# Help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
