self: {
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

      package = mkOption {
        type = types.package;
        default = self.packages.${pkgs.system}.default;
        description = "The discord-to-authentik package";
      };

      autoSyncRoles = mkOption {
        type = types.bool;
        default = true;
        description = "Automatically sync roles from users";
      };

      environmentFile = mkOption {
        type = types.path;
        example = "/run/secrets/discord-to-authentik/discord-to-authentik-env";
        description = mdDoc ''

          Environment file as defined in {manpage}`systemd.exec(5)`.

          ```
            # required content
            DISCORD_OWNER_ID=<your discord user id>
            DISCORD_BOT_TOKEN=<your discord bot token>
            AUTHENTIK_HOST=<your authentik host>
            AUTHENTIK_TOKEN=<your authentik token>
          ```
        '';
      };
    };
  };

  config = mkIf cfg.enable {
    systemd.services.discord-to-authentik = {
      description = "A Discord bot that synchronizes your discord roles to authentik groups";
      after = ["network.target"];
      wants = ["network-online.target"];

      serviceConfig = {
        Type = "simple";
        Restart = "always";
        ExecStart = lib.getExe cfg.package;
        EnvironmentFile = config.services.discord-to-authentik.environmentFile;
        Environment = mkIf cfg.autoSyncRoles {
          DISCORD_AUTO_SYNC_ROLES = "true";
        };
      };

      wantedBy = ["multi-user.target"];
    };
  };
}
