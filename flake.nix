{
  description = "gang.guide dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            nodejs_22
            python312
            ruff
            just
            lefthook
          ];

          shellHook = ''
            echo "gang.guide dev shell"
            echo "node $(node --version) | python $(python3 --version | cut -d' ' -f2) | just $(just --version | cut -d' ' -f2)"
          '';
        };
      });
}
