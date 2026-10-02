.PHONY: install test lint phenotypic metadata pilot atlases atlases-trial clean

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

pilot:
	python scripts/03_pilot_atlas.py --n 5

atlases-trial:
	python scripts/04_fetch_all_atlases.py --limit 20

atlases:
	caffeinate -i python scripts/04_fetch_all_atlases.py

clean:
	rm -rf .pytest_cache __pycache__ */__pycache__ .coverage
