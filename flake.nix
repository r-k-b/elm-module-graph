{
  inputs = { utils.url = "github:numtide/flake-utils"; };

  outputs = { self, nixpkgs, utils }:
    utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages."${system}";
        inherit (pkgs) mkShell stdenv;
        elm-module-graph = stdenv.mkDerivation {
          name = "elm-module-graph";
          buildInputs = with pkgs; [ python ];
          buildPhase = ''
            echo hiya
          '';
          installPhase = ''
            mkdir -p $out/bin
            cp ./elm-module.graph.py $out/bin/
          '';
          src = ./.;
          passthru = { exePath = "/elm-module-graph.py"; };

          system = system;
        };
        edapp = utils.lib.mkApp { drv = elm-module-graph; };
      in {
        # `nix build`
        #packages.elm-module-graph = elm-module-graph;
        #defaultPackage = elm-module-graph;

        # `nix run`
        #apps.elm-module-graph = edapp;
        #defaultApp = edapp;

        # `nix develop`
        devShell = mkShell { nativeBuildInputs = with pkgs; [ python ]; };
      });
}
