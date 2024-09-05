{
  config,
  lib,
  pkgs,
  ...
}: let
  inherit
    (lib)
    types
    ;

  inherit
    (lib.modules)
    mkIf
    ;

  inherit
    (lib.options)
    mdDoc
    mkEnableOption
    mkOption
    ;

  cfg = config.services.discord-to-authentik;
in {
  options.services = {
    discord-to-authentik = {
      enable = mkEnableOption "discord-to-authentik";

      environmentFile = mkOption {
        type = types.path;
        example = "/run/secrets/discord-to-authentik/discord-to-authentik-env";
        description = mdDoc ''

          Environment file as defined in {manpage}`systemd.exec(5)`.

          ```
            # required content
            DISCORD_OWNER_ID=<your discord user id>
            DISCORD_BOT_TOKEN=<your discord bot token>
            AUTHENTIK_HOST=<your authenti host>
            AUTHENTIK_TOKEN=<your authenti token>
          ```
        '';
      };
    };
  };

  config = {
    systemd.services.discord-to-authentik = mkIf config.services.discord-to-authentik.enable {
      description = "A Discord bot that synchronizes your discord roles to authentik groups";
      after = ["network.target"];
      wants = ["network-online.target"];

      serviceConfig = {
        Type = "simple";
        Restart = "always";
        ExecStart = ''
          ${pkgs.discord-to-authentik}/bin/discord-to-authentik
        '';
        EnvironmentFile = config.services.discord-to-authentik.environmentFile;
      };

      wantedBy = ["multi-user.target"];
    };
  };
}
