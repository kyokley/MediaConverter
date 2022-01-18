build:
	docker build -t kyokley/mediaconverter --target=prod .

build-dev:
	docker build -t kyokley/mediaconverter --target=dev .

shell: build-dev
	docker-compose run mediaconverter /bin/bash

tests: build-dev
	docker-compose run mediaconverter pytest

autoformat: build-dev
	docker-compose run mediaconverter /venv/bin/black .

up:
	docker-compose up

down:
	docker-compose down -v

exec:
	docker-compose exec /venv/bin/python /code/main.py
