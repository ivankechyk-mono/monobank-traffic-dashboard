.PHONY: install test lint

install:
	python3.11 -m pip install -r requirements.txt

test:
	python3.11 -m pytest tests/ --cov=src --cov-report=term-missing -q --ignore=tests/integration || true

lint:
	python3.11 -m flake8 src/ --max-line-length=100
