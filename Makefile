PYTHON ?= python3
VENV = .venv/bin
.PHONY: setup check test run crawl model smoke dist
setup:
	$(PYTHON) -m venv .venv
	$(VENV)/pip install -r requirements.lock
	$(VENV)/pip install --no-deps -e .
	cd frontend && npm ci
check:
	$(VENV)/ruff check backend tests scripts
	$(VENV)/mypy backend
	$(VENV)/pytest
	cd frontend && npm run typecheck && npm run lint && npm run build
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
	$(VENV)/python -m build
