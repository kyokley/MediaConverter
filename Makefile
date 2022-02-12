publish:
	docker build -t kyokley/mediaconverter --target=prod --build-arg UID=$$(id -u) .
	docker push kyokley/mediaconverter

build-dev-root:
	docker build -t kyokley/mediaconverter --target=dev-root --build-arg UID=$$(id -u) .

build-dev: write-env
	docker build -t kyokley/mediaconverter --target=dev --build-arg UID=$$(id -u) .

shell: write-env up
	docker-compose exec mediaconverter /bin/bash

shell-root: up-root
	docker-compose exec mediaconverter /bin/bash

tests: build-dev up
	docker-compose exec mediaconverter pytest

ci-tests: build-dev up
	docker-compose exec -T mediaconverter pytest

autoformat: build-dev
	docker-compose run --no-deps mediaconverter /venv/bin/black .

up-root: build-dev-root
	docker-compose up -d

up:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

down:
	docker-compose down -v

exec:
	docker-compose exec mediaconverter /venv/bin/python /code/main.py

write-env:
	@echo "UID=$$UID\nGID=$$GID" > .env
