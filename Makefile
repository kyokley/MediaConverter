build:
	docker build -t kyokley/mediaconverter --target=prod .

build-dev:
	docker build -t kyokley/mediaconverter --target=dev .

shell: build-dev
	docker run --rm -it -v $$(pwd):/code kyokley/mediaconverter /bin/bash

tests: build-dev
	docker run --rm -it -v $$(pwd):/code kyokley/mediaconverter pytest

autoformat: build-dev
	docker run --rm -t -v $$(pwd):/code kyokley/mediaconverter /venv/bin/black .
