up:
	docker compose -f docker-compose.yml up --build -d
down:
	docker compose -f docker-compose.yml down

volumes:
	docker volume ls


test-config:
	docker compose -f docker-compose.yml -f docker-compose-test.yml config

test-up:
	docker compose -f docker-compose.yml -f docker-compose-test.yml up --build -d

test-logs:
	docker compose -f docker-compose.yml -f docker-compose-test.yml logs -f

test-logs-api:
	docker compose -f docker-compose.yml -f docker-compose-test.yml logs api -f

test-down:
	docker compose -f docker-compose.yml -f docker-compose-test.yml down
	docker volume rm support_pgdata_test