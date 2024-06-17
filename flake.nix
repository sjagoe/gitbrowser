{
  description = " Dumb curses git browser for reading files from arbitraty git revisions ";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    systems.url = "github:nix-systems/default";
    utils = {
      url = "github:numtide/flake-utils";
      inputs.systems.follows = "systems";
    };
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "utils";
      inputs.systems.follows = "systems";
    };
  };

  outputs = { self, nixpkgs, utils, poetry2nix, ... }:
    (utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        poetry2nix' = poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };
        inherit (poetry2nix') mkPoetryApplication;
      in
        {
          packages =
            {
              gitbrowser =
                let
                  haas = pkgs.python3Packages.buildPythonPackage rec {
                    pname = "haas";
                    version = "0.9.0";
                    pyproject = true;
                    disabled = pkgs.python3Packages.pythonOlder "3.8";

                    patches = [ ./0001-Remove-enum34-dependency.patch ];

                    src = pkgs.fetchFromGitHub {
                      owner = "scalative";
                      repo = "haas";
                      rev = "refs/tags/v${version}";
                      hash = "sha256-EKhHvF11spwgV8SRZSvu7TOqHELLsOMMmgrlWCqQfrc=";
                    };

                    buildInputs = with pkgs.python3Packages; [ setuptools enum34 ];
                    propagatedBuildInputs = with pkgs.python3Packages; [
                      statistics
                      (stevedore.overrideAttrs (old: rec {
                        pname = "stevedore";
                        version = "4.1.1";
                        src = fetchPypi {
                          inherit pname version;
                          hash = "sha256-f4rrbj+Q+WgywwG/8hp+te776JTIjFBkg9NVVl2IzBo=";
                        };
                      }))
                    ];
                  };
                in
                  mkPoetryApplication {
                    projectDir = self;
                    preferWheels = true;
                    overrides = poetry2nix'.overrides.withDefaults (self: super: {
                      inherit haas;
                    });
                  };
              default = self.packages.${system}.gitbrowser;
            };

          apps = {
            default = self.apps."${system}".gitbrowser;
            gitbrowser = {
              type = "app";
              program = "${self.packages."${system}".default}/bin/gitbrowser";
            };
          };

          devShells.default = pkgs.mkShell {
            inputsFrom = [ self.packages.${system}.gitbrowser ];
            packages = [ pkgs.poetry ];
          };
        })) // {
          overlays.default = final: prev: {
            gitbrowser = self.packages.${prev.stdenv.hostPlatform.system}.gitbrowser;
          };
        };
}
