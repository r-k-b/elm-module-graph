{
  inputs = { utils.url = "github:numtide/flake-utils"; };

  outputs = { self, nixpkgs, utils }:
    utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages."${system}";
        inherit (pkgs) mkShell stdenv;
        inherit (pkgs.lib) fileset;

        graph-builder = stdenv.mkDerivation {
          name = "elm-module-graph-builder";
          buildInputs = with pkgs; [ python3 ];
          installPhase = ''
            mkdir -p $out/bin
            cp ./elm-module-graph.py $out/bin/
          '';
          src = fileset.toSource {
            root = ./.;
            fileset = ./elm-module-graph.py;
          };
          passthru = { exePath = "/bin/elm-module-graph.py"; };

          system = system;
        };

        emgApp = {
          type = "app";
          program = "${graph-builder}/${graph-builder.passthru.exePath}";
          meta = {
            description = "Extract the module structure of an Elm project into a graph, as a json file.";
          };
        };

      in {
        # `nix build`
        packages.graph-builder = graph-builder;
        packages.default = graph-builder;

        # `nix run`
        apps.graph-builder = emgApp;
        apps.default = emgApp;

        # `nix develop`
        devShells.default = mkShell {
          nativeBuildInputs = (with pkgs; [ nodejs python3 simple-http-server ])
            ++ (with pkgs.elmPackages; [ elm elm-upgrade elm-format ]);
        };
      });
}
