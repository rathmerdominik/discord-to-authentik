{
  lib,
  mkPoetryApplication,
  defaultPoetryOverrides,
  self,
}:
mkPoetryApplication {
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
  meta = {
    description = "A Discord bot that synchronizes your discord roles to authentik groups";
    homepage = "https://github.com/rathmerdominik/discord-to-authentik";
    license = lib.licenses.gpl3;
    platforms = lib.platforms.all;
    mainProgram = "discord-to-authentik";
  };
}
