with import <nixpkgs> {};
mkShell {
  packages = [
    bashInteractive
    gnumake
    (python3.withPackages(p: [ p.pycairo ]))
    ffmpeg
  ];
}
