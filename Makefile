.PHONY: dev down migrate migration test test-api lint format shell logs

dev:
	docker-compose up

down:
	docker-compose down

migrate:
	docker-compose exec api alembic upgrade head

migration:
	docker-compose exec api alembic revision --autogenerate -m "$(name)"

test:
	pytest tests/ -x

test-api:
	pytest tests/api/ -x

lint:
	ruff check .

format:
	ruff format .

shell:
	docker exec -it singularity-api-1 bash

logs:
	docker-compose logs -f
