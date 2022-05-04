.PHONY: autoformat build build-dev ci-tests down exec publish shell tests up


build:
	docker build -t kyokley/mediaconverter --target=prod .

build-dev:
	# docker build -t kyokley/mediaconverter --target=dev .

publish: build
	docker push kyokley/mediaconverter

shell: up
	docker-compose exec mediaconverter /bin/bash

tests: build-dev up
	docker-compose exec mediaconverter pytest

ci-tests: build-dev up
	docker-compose exec -T mediaconverter pytest

autoformat: build-dev
	docker-compose run --no-deps mediaconverter /venv/bin/black .

up:
	docker-compose up -d

down:
	docker-compose down -v

exec:
	docker-compose exec mediaconverter /venv/bin/python /code/main.py
