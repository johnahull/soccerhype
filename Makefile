.PHONY: test lint typecheck run setup clean

test:
	python -m pytest tests/ -v

lint:
	python -m flake8 *.py utils/ --max-line-length=120

typecheck:
	python -m mypy render/ utils/ --ignore-missing-imports

run:
	python soccerhype_gui.py

setup:
	./setup.sh

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	rm -rf .pytest_cache .mypy_cache
