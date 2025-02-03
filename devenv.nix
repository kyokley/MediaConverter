{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/basics/
  # env.GREET = "MV";

  # https://devenv.sh/packages/
  # packages = [
  #   pkgs.git
  # ];

  # https://devenv.sh/scripts/
  # scripts.hello.exec = "echo hello from $GREET";

  # enterShell = ''
  #   # hello
  # '';

  # https://devenv.sh/tests/
  # enterTest = ''
  #   # echo "Running tests"
  #   # git --version | grep "2.42.0"
  # '';

  # https://devenv.sh/services/
  # services.postgres.enable = true;

  # https://devenv.sh/languages/
  # languages.nix.enable = true;
  languages.python = {
    enable = true;
    version = "3.12";
    uv = {
      enable = true;
    };
  };

  # https://devenv.sh/pre-commit-hooks/
  pre-commit.hooks = {
    hadolint.enable = false;
    check-merge-conflicts.enable = true;
    check-added-large-files.enable = true;
    check-toml.enable = true;
    check-yaml.enable = true;
    checkmake.enable = true;
    detect-private-keys.enable = true;
    ripsecrets.enable = true;
    ruff.enable = true;
    ruff-format.enable = true;
    trim-trailing-whitespace.enable = true;
    yamlfmt.enable = true;
    yamllint.enable = false;
  };

  # https://devenv.sh/processes/
  # processes.ping.exec = "ping example.com";

  # See full reference at https://devenv.sh/reference/options/
}
