.PHONY: install test lint phenotypic metadata clean

install:
	pip install -r requirements-dev.txt
	pip install -e .

test:
	pytest

lint:
	ruff check src scripts tests

phenotypic:
	python scripts/01_fetch_phenotypic.py

metadata:
	python scripts/02_metadata_report.py

clean:
	rm -rf .pytest_cache __pycache__ */__pycache__ .coverage
