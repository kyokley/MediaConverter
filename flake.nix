{
  description = "MediaConverter - A Python media conversion tool";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    # Core pyproject-nix ecosystem tools
    pyproject-nix.url = "github:pyproject-nix/pyproject.nix";
    uv2nix.url = "github:pyproject-nix/uv2nix";
    pyproject-build-systems.url = "github:pyproject-nix/build-system-pkgs";

    # Ensure consistent dependencies between these tools
    pyproject-nix.inputs.nixpkgs.follows = "nixpkgs";
    uv2nix.inputs.nixpkgs.follows = "nixpkgs";
    pyproject-build-systems.inputs.nixpkgs.follows = "nixpkgs";
    uv2nix.inputs.pyproject-nix.follows = "pyproject-nix";
    pyproject-build-systems.inputs.pyproject-nix.follows = "pyproject-nix";
  };

  outputs = { self, nixpkgs, flake-utils, uv2nix, pyproject-nix, pyproject-build-systems, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # Import nixpkgs with unfree packages enabled (needed for libfdk_aac)
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
        python = pkgs.python312; # Your desired Python version

        # Override ffmpeg-full to include libfdk_aac support
        ffmpeg-full-fdk = pkgs.ffmpeg-full.override {
          withFdkAac = true;  # Enable FDK AAC codec
          withUnfree = true;  # Required for FDK AAC
        };

        # 1. Load Project Workspace (parses pyproject.toml, uv.lock)
        workspace = uv2nix.lib.workspace.loadWorkspace {
          workspaceRoot = ./.; # Root of your flake/project
        };

        # 2. Generate Nix Overlay from uv.lock (via workspace)
        uvLockedOverlay = workspace.mkPyprojectOverlay {
          sourcePreference = "wheel"; # Or "sdist"
        };

        # 3. Placeholder for Your Custom Package Overrides
        myCustomOverrides = final: prev: {
          # e.g., some-package = prev.some-package.overridePythonAttrs (...);
        };

        # 4. Construct the Final Python Package Set
        pythonSet =
          (pkgs.callPackage pyproject-nix.build.packages { inherit python; })
          .overrideScope (nixpkgs.lib.composeManyExtensions [
            pyproject-build-systems.overlays.default # For build tools
            uvLockedOverlay                          # Your locked dependencies
            myCustomOverrides                        # Your fixes
          ]);

        # --- This is where your project's metadata is accessed ---
        projectNameInToml = "mediaconverter"; # Package names are normalized to lowercase
        thisProjectAsNixPkg = pythonSet.${projectNameInToml};
        # ---

        # 5. Create the Python Runtime Environment
        appPythonEnv = pythonSet.mkVirtualEnv
          (thisProjectAsNixPkg.pname + "-env")
          workspace.deps.default; # Uses deps from pyproject.toml [project.dependencies]

        # 6. Create the Development Python Environment with dev dependencies
        # Merge default and dev dependencies
        allDeps = workspace.deps.default // (workspace.deps.dev or {});
        devPythonEnv = pythonSet.mkVirtualEnv
          (thisProjectAsNixPkg.pname + "-dev-env")
          allDeps; # Includes both default and dev deps

        osDeps = with pkgs; [
          srt-to-vtt-cl
          ffmpeg-full-fdk  # Use the custom ffmpeg with libfdk_aac
        ];
      in
      {
        # Development Shell
        devShells.default = pkgs.mkShell {
          packages = [ devPythonEnv pkgs.ruff pkgs.uv ] ++ osDeps;
          shellHook = ''
            echo "MediaConverter development environment"
            echo "Python version: ${python.version}"
            echo "Environment with dependencies from uv.lock (including dev dependencies)"
            export PYTHONPATH="$PWD:$PYTHONPATH"
          '';
        };

        # Nix Package for Your Application
        packages.default = pkgs.stdenv.mkDerivation {
          pname = thisProjectAsNixPkg.pname;
          version = thisProjectAsNixPkg.version;
          src = ./.; # Source of your main script

          nativeBuildInputs = [ pkgs.makeWrapper ];
          buildInputs = [ appPythonEnv ] ++ osDeps; # Runtime Python environment

          # Skip the build phase to avoid running Makefile
          dontBuild = true;

          installPhase = ''
            mkdir -p $out/bin $out/lib
            # Copy all Python modules to lib directory
            cp *.py $out/lib/
            chmod +x $out/lib/main.py
            # Create wrapper that sets PYTHONPATH to include our modules
            makeWrapper ${appPythonEnv}/bin/python $out/bin/${thisProjectAsNixPkg.pname} \
              --add-flags $out/lib/main.py \
              --prefix PYTHONPATH : $out/lib
          '';
        };
        packages.${thisProjectAsNixPkg.pname} = self.packages.${system}.default;

        # Docker image for MediaConverter
        packages.mc-image = pkgs.dockerTools.buildImage {
          name = "kyokley/MediaConverter";
          tag = thisProjectAsNixPkg.version;
          created = "now";

          copyToRoot = pkgs.buildEnv {
            name = "image-root";
            paths = [
              self.packages.${system}.default
              appPythonEnv
              pkgs.bash
            ] ++ osDeps;
            pathsToLink = [ "/bin" ];
          };

          config = {
            Cmd = [ "${self.packages.${system}.default}/bin/${thisProjectAsNixPkg.pname}" ];
            WorkingDir = "/data";
            Volumes = {
              "/data" = {};
            };
            Env = [
              "PYTHONPATH=${self.packages.${system}.default}/lib:${appPythonEnv}/lib/python3.12/site-packages"
            ];
          };
        };

        # App for `nix run`
        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/${thisProjectAsNixPkg.pname}";
        };
        apps.${thisProjectAsNixPkg.pname} = self.apps.${system}.default;
      }
    );
}
