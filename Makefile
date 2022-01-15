build:
	docker build -t kyokley/mediaconverter --target=prod .

build-dev:
	docker build -t kyokley/mediaconverter --target=dev .

shell: build-dev
	docker run --rm -it -v $$(pwd):/code kyokley/mediaconverter /bin/bash
