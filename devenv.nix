{ pkgs, lib, config, inputs, ... }:

{
  cachix.pull = ["horus"];
  # https://devenv.sh/basics/
  env.GREET = "MV";

  # https://devenv.sh/packages/
  packages = [
    pkgs.docker
  ];

  # https://devenv.sh/scripts/
  scripts = {
    hello.exec = "echo hello from $GREET";
    build.exec = ''
      ${pkgs.docker}/bin/docker build -t kyokley/mediaconverter --target=prod "$@" .
    '';
    build-dev.exec = ''
      ${pkgs.docker}/bin/docker build -t kyokley/mediaconverter --target=dev "$@" .
    '';
    up.exec = ''
      ${pkgs.docker}/bin/docker compose up "$@"
    '';
    down.exec = ''
      ${pkgs.docker}/bin/docker compose down "$@"
    '';
    runtests.exec = ''
      build-dev
      up -d
      ${pkgs.docker}/bin/docker compose exec mediaconverter pytest
    '';
  };

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

  git-hooks.hooks = {
    hadolint.enable = false;
    check-merge-conflicts.enable = true;
    check-added-large-files.enable = true;
    check-toml.enable = true;
    check-yaml.enable = true;
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
