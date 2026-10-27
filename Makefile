.PHONY: install test lint phenotypic metadata pilot atlases atlases-trial qc frozen \
	connectomes verify week2 fixtures api api-fixtures smoke clean

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

qc:
	python scripts/05_apply_qc.py

frozen:
	python scripts/06_draw_frozen_set.py

connectomes:
	python scripts/07_build_connectomes.py

verify:
	python scripts/08_verify_connectomes.py

week2: qc frozen connectomes verify test

# Fixture dataset (memo 0014): synthetic, real formats, no real data needed
fixtures:
	python scripts/build_fixtures.py --force

api:
	python -m uvicorn neurographx.api.main:app --reload

api-fixtures:
	NGX_DATA=fixtures python -m uvicorn neurographx.api.main:app --reload

smoke:
	python scripts/smoke_api.py --data fixtures

clean:
	rm -rf .pytest_cache __pycache__ */__pycache__ .coverage
