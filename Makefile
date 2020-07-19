build:
	docker build --target=prod -t kyokley/mediaconverter .

build-dev:
	docker build --target=dev -t kyokley/mediaconverter .

shell:
	docker run --rm -it kyokley/mediaconverter /bin/sh
