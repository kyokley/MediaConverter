build:
	docker build -t kyokley/mediaconverter --target=prod .

build-dev:
	docker build -t kyokley/mediaconverter --target=dev .

shell: build-dev
	docker run --rm -it -v $$(pwd):/code kyokley/mediaconverter /bin/bash

tests: build-dev
	docker run --rm -it -v $$(pwd):/code kyokley/mediaconverter pytest

autoformat:
	docker-compose run --rm --no-deps kyokley/mediaconverter /venv/bin/black .
