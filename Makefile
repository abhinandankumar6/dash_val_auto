install:
	pip install -e ".[dev]"
	playwright install chromium

run-api:
	uvicorn bi_validator.main:app --reload --host 0.0.0.0 --port 8000

run-worker:
	python -m bi_validator.services.queue.worker

lint:
	python -m compileall src tests scripts

test:
	pytest

alembic-upgrade:
	alembic upgrade head

build-executable:
	python scripts/build_executable.py
