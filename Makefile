.PHONY: install lint test coverage validate release run clean

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .

test:
	pytest

coverage:
	pytest --cov=valuation_tool --cov-report=term-missing --cov-fail-under=85

validate:
	valuation-validate data/raw/example

release:
	python scripts/build_release.py

run:
	streamlit run app.py

clean:
	rm -rf build dist .pytest_cache .ruff_cache htmlcov

