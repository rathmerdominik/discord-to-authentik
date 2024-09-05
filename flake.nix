{
  description = "A Discord bot that synchronizes your discord roles to authentik groups";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };

  outputs = {
    self,
    nixpkgs,
    poetry2nix,
  }: let
    supportedSystems = nixpkgs.lib.systems.flakeExposed;
    forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
  in {
    nixosModules.default = import ./module.nix self;

    packages = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      inherit
        (poetry2nix.lib.mkPoetry2Nix {inherit pkgs;})
        mkPoetryApplication
        defaultPoetryOverrides
        ;
    in {
      default = pkgs.callPackage ./package.nix {
        inherit self mkPoetryApplication defaultPoetryOverrides;
      };
    });
  };
}
