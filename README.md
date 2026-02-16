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
- The `uv` package manager
- `ruff` for linting

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

The flake supports multiple platforms: x86_64-linux, aarch64-linux, x86_64-darwin, and aarch64-darwin.
