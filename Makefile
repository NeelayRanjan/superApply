PYTHON ?= python3
VENV = .venv/bin
.PHONY: setup check test run crawl model smoke dist
setup:
	$(PYTHON) -m venv .venv
	$(VENV)/pip install -r requirements.lock
	cd frontend && npm ci && npm run build
	$(VENV)/pip install --no-deps --no-build-isolation -e .
check:
	$(VENV)/ruff check backend tests scripts
	$(VENV)/mypy backend
	cd frontend && npm run typecheck && npm run lint && npm run build
	$(VENV)/pytest
	$(VENV)/coverage json -o .firstlook/coverage.json
	$(VENV)/python scripts/check_coverage.py
test:
	$(VENV)/pytest
run:
	$(VENV)/firstlook serve
crawl:
	$(VENV)/firstlook crawl
model:
	$(VENV)/python scripts/download_model.py
smoke:
	$(VENV)/python scripts/smoke.py
dist:
	cd frontend && npm run build
	$(VENV)/python -m build --no-isolation
