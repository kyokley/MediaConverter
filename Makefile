.PHONY: build build-dev shell autoformat tests

build:
	docker build --target=prod -t kyokley/mediaconverter .

build-dev:
	docker build --target=dev -t kyokley/mediaconverter .

shell:
	docker run --rm -it -v $$(pwd):/workspace kyokley/mediaconverter /bin/sh

autoformat:
	docker run --rm -t -v $$(pwd):/workspace kyokley/mediaconverter /bin/sh -c "git ls-files | grep '\.py$$' | xargs isort && \
                                                                              git ls-files | grep '\.py$$' | xargs black"

tests:
	docker run --rm -t -v $$(pwd):/workspace kyokley/mediaconverter pytest -v

down:
	docker-compose down
	docker ps -aqf name=converter | xargs -r docker rm
	docker ps -aqf name=rabbitmq | xargs -r docker rm

up:
	docker-compose up

attach:
	docker exec -it MediaConverter_converter_1 /bin/sh
