.PHONY: install test lint phenotypic metadata pilot atlases atlases-trial qc frozen \
	connectomes verify week2 fixtures api api-fixtures smoke db db-fixtures integrity \
	integrity-fixtures confounds clean

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

# SQLite view of the run log, registry and analysis log (memos 0008 and 0013)
db:
	python scripts/build_db.py

db-fixtures:
	python scripts/build_db.py --data fixtures

# Registry, run log, checkpoints, data files and analysis log agree (before every demo)
integrity:
	python scripts/check_integrity.py

integrity-fixtures:
	python scripts/check_integrity.py --data fixtures

# Confound check on the out-of-fold predictions (docs/reports/confound_check.md)
confounds:
	python scripts/confound_check.py

clean:
	rm -rf .pytest_cache __pycache__ */__pycache__ .coverage
