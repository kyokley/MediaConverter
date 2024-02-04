.PHONY: autoformat build build-dev ci-tests down exec publish shell tests up

DOCKER_COMPOSE_EXECUTABLE=$$(which docker-compose >/dev/null 2>&1 && echo "docker-compose" || echo "docker compose")
NO_CACHE?=0

build:
	docker build -t kyokley/mediaconverter \
		$$(test ${NO_CACHE} -ne 0 && echo "--no-cache" || echo "") \
		--target=prod .

build-dev:
	docker build -t kyokley/mediaconverter \
		$$(test ${NO_CACHE} -ne 0 && echo "--no-cache" || echo "") \
		--target=dev .

publish: build
	docker push kyokley/mediaconverter

shell:
	${DOCKER_COMPOSE_EXECUTABLE} run mediaconverter /bin/bash

tests: build-dev up
	${DOCKER_COMPOSE_EXECUTABLE} exec mediaconverter pytest

ci-tests: build-dev up
	${DOCKER_COMPOSE_EXECUTABLE} exec -T mediaconverter pytest

autoformat: build-dev
	${DOCKER_COMPOSE_EXECUTABLE} run --no-deps mediaconverter /venv/bin/black .

up:
	${DOCKER_COMPOSE_EXECUTABLE} up -d

down:
	${DOCKER_COMPOSE_EXECUTABLE} down -v

exec:
	${DOCKER_COMPOSE_EXECUTABLE} exec mediaconverter /venv/bin/python /code/main.py
