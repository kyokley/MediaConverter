# MediaConverter [![Build Status](https://travis-ci.org/kyokley/MediaConverter.svg)](https://travis-ci.org/kyokley/MediaConverter)
Convert media files to HTML5 streamable format

## Nix Flake Installation

This project includes a `flake.nix` file created with uv2nix for easy installation and development using Nix.

### Development Shell

To enter a development environment with all dependencies installed:

```bash
nix develop
```

This will provide you with:
- Python 3.12
- All project dependencies from `uv.lock` (via uv2nix)
- All development dependencies (pytest, black, faker, bandit, etc.)
- The `uv` package manager
- `ruff` for linting
- `ffmpeg-full` with **libfdk_aac** support enabled
- `srt-to-vtt-cl` for subtitle conversion

### Building the Package

To build the package:

```bash
nix build
```

This creates a `./result` symlink with the built package.

### Running the Application

You can run the application directly with:

```bash
nix run
# or specifically
nix run .#mediaconverter
```

### Running from Flake URL

Once pushed to a git repository, you can run directly from the flake URL:

```bash
# Enter dev shell
nix develop github:kyokley2/MediaConverter

# Build
nix build github:kyokley2/MediaConverter

# Run
nix run github:kyokley2/MediaConverter
```

### About This Setup

This flake uses [uv2nix](https://github.com/pyproject-nix/uv2nix) which:
- Loads dependencies from `uv.lock` ensuring reproducibility
- Creates a Nix overlay with Python packages
- Provides proper integration with the pyproject-nix ecosystem
- Uses `mkVirtualEnv` to create isolated Python environments
- Follows the recommended uv2nix patterns for Python projects

#### FFmpeg with libfdk_aac

The flake includes a custom build of `ffmpeg-full` with **libfdk_aac** codec support enabled. This is configured through:
- Enabling unfree packages in nixpkgs configuration
- Overriding `ffmpeg-full` with `withFdkAac = true` and `withUnfree = true`
- This provides high-quality AAC encoding capabilities for media conversion

The flake supports multiple platforms: x86_64-linux, aarch64-linux, x86_64-darwin, and aarch64-darwin.

### Building Docker Image

The flake includes a Docker image output that bundles the application with all dependencies including FFmpeg with libfdk_aac support.

To build the Docker image:

```bash
nix build .#mc-image
```

This creates a `./result` file containing the Docker image tarball.

### Loading and Running the Docker Image

Load the image into Docker:

```bash
docker load < result
```

The image will be tagged as `kyokley/mediaconverter:0.1.0` (version from pyproject.toml).

Run the container:

```bash
# Run the default application
docker run --rm -v /path/to/data:/data kyokley/mediaconverter:0.1.0

# Run with celery worker (as intended for the application)
docker run --rm -e BROKER=redis://redis:6379 kyokley/mediaconverter:0.1.0 celery -A main worker --loglevel=info

# Run interactive bash shell
docker run --rm -it --entrypoint bash kyokley/mediaconverter:0.1.0

# Execute commands via bash
docker run --rm kyokley/mediaconverter:0.1.0 bash -c "python --version && celery --version"

# Test with Python imports
docker run --rm kyokley/mediaconverter:0.1.0 python -c "from tv_runner import TvRunner; print('OK')"

# Check FFmpeg with FDK AAC support
docker run --rm --entrypoint ffmpeg kyokley/mediaconverter:0.1.0 -codecs 2>&1 | grep fdk
```

The Docker image includes:
- Bash shell for interactive sessions and scripting
- Python 3.12 with all application dependencies
- FFmpeg with libfdk_aac codec support
- srt-to-vtt-cl for subtitle conversion
- Working directory mounted at `/data`
- All Python modules properly configured in PYTHONPATH
