{
  description = "Python application packaged using poetry2nix";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.poetry2nix.url = "github:nix-community/poetry2nix";

  outputs = {
    self,
    nixpkgs,
    poetry2nix,
  }: let
    supportedSystems = ["x86_64-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin"];
    forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    pkgs = forAllSystems (system: nixpkgs.legacyPackages.${system});
  in {
    nixosModules.default = {pkgs, ...}: {
      imports = [./module.nix];
    };
    packages = forAllSystems (system: let
      inherit (poetry2nix.lib.mkPoetry2Nix {pkgs = pkgs.${system};}) mkPoetryApplication defaultPoetryOverrides;
    in {
      default = mkPoetryApplication {
        projectDir = self;
        preferWheels = true;
        overrides =
          defaultPoetryOverrides.extend
          (
            final: prev: {
              authentik-client =
                prev.authentik-client.overridePythonAttrs
                (
                  old: {
                    buildInputs = (old.buildInputs or []) ++ [prev.setuptools];
                  }
                );
            }
          );
      };
    });
  };
}
