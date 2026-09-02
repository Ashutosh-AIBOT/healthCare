dev:
	docker compose up -d --build

migrate:
	cd apps/api && alembic upgrade head

test:
	cd apps/api && pytest -q

seed:
	echo "seed — coming in M0 seed milestone"
