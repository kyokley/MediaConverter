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
