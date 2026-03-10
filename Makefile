.PHONY: setup run backend frontend clean

setup:
	@echo "→ Setting up Python environment..."
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements-api.txt
	@echo "→ Setting up frontend..."
	cd frontend && npm install --silent
	@echo "✓ Setup complete. Run 'make run' to start."

run:
	@echo "Starting AutoPulseSynth..."
	@make -j2 backend frontend

backend:
	.venv/bin/uvicorn api.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

clean:
	rm -rf .venv frontend/node_modules frontend/.next
	@echo "✓ Cleaned all build artifacts."
