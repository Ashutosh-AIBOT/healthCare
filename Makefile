.PHONY: dev migrate test seed reset load-test eval down

dev:
	docker compose up -d --build

down:
	docker compose down

migrate:
	docker compose exec api alembic upgrade head

test:
	cd backend && pytest -q

seed:
	docker compose exec api python /app/seed/seed.py

reset:
	docker compose down -v
	docker compose up -d --build
	@echo "Waiting for API health..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do \
		curl -sf http://localhost:8000/health >/dev/null && break; \
		sleep 3; \
	done
	$(MAKE) seed

load-test:
	@echo "load-test — wire k6 in M23"

eval:
	@echo "eval — wire AI eval harness in M6+"
