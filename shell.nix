# -*- coding: utf-8 -*-
with import <nixpkgs> {};
with pkgs.python37Packages;

stdenv.mkDerivation {
  name = "manta-backend-impurePythonEnv";
  buildInputs = [
    python37Full
    python37Packages.virtualenv
    python37Packages.pip
    # The following are build dependencies
    gnumake
    libffi
    mosquitto
    openssl
  ];
  src = null;
  shellHook = ''
  # set SOURCE_DATE_EPOCH so that we can use python wheels
  SOURCE_DATE_EPOCH=$(date +%s)
  export PATH=$PWD/venv/bin:$PATH
  make
  '';
}
