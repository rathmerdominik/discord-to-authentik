import logging
import os

import authentik_client
import authentik_client.api_client
import authentik_client.models
import authentik_client.models.group_request
import discord
from discord import Intents, app_commands
from discord.ext import commands
from dotenv import load_dotenv

LOGGER = logging.getLogger("discord")
OWNER_ID = [int(os.environ["DISCORD_OWNER_ID"])]
AUTHENTIK_BEARER_TOKEN = os.environ["AUTHENTIK_TOKEN"]
AUTHENTIK_HOST = os.environ["AUTHENTIK_HOST"]
DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]


class MainCog(commands.Cog):
    def __init__(self, bot, authentik_client: authentik_client.api_client.ApiClient):
        self.authentik_client = authentik_client
        self.bot = bot

    @commands.is_owner()
    @commands.command()
    async def sync(self, ctx: commands.Context):
        assert ctx.guild is not None
        guild = discord.Object(id=ctx.guild.id)
        self.bot.tree.copy_global_to(guild=guild)

        commands = await self.bot.tree.sync(guild=guild)
        for command in commands:
            await ctx.reply(f"Synced {command.name} command group", ephemeral=True)

    @commands.is_owner()    # type: ignore
    @app_commands.command(
        name="sync_roles", description="Sync roles from discord to authentik"
    )
    async def sync_roles(self, ctx: discord.Interaction):
        core_api = authentik_client.CoreApi(self.authentik_client)
        assert ctx.guild is not None

        synced_roles = []
        deleted_roles = []
        for role in ctx.guild.roles:
            if role.is_bot_managed():
                continue
            if role.is_default():
                continue

            if core_api.core_groups_list(name=role.name).results:
                continue

            group_request = authentik_client.models.group_request.GroupRequest(
                name=role.name,
                attributes={"discord_role_id": role.id},
            )
            core_api.core_groups_create(group_request=group_request)
            synced_roles.append(role.name)

        for group in core_api.core_groups_list().results:
            assert group.attributes is not None
            if group.attributes.get("discord_role_id") is None:
                continue

            if ctx.guild.get_role(group.attributes["discord_role_id"]) is None:
                core_api.core_groups_destroy(group.pk)
                deleted_roles.append(group.name)

        await ctx.response.send_message(f"Synced roles: {"\n".join(synced_roles)} | Deleted roles: {"\n".join(deleted_roles)}", ephemeral=True)


class AuthentikSync(commands.Bot):
    def __init__(self, *args, **kwargs):
        intents = Intents.default()
        intents.messages = True
        intents.message_content = True
        self.authentik_client = kwargs.get("authentik_client")
        self.owner_id = OWNER_ID
        super().__init__(*args, **kwargs, intents=intents)

    async def setup_hook(self):
        await self.add_cog(
            MainCog(self, self.authentik_client),
        )


def create_authentik_client() -> authentik_client.api_client.ApiClient:
    return authentik_client.api_client.ApiClient(
        authentik_client.Configuration(
            host=AUTHENTIK_HOST,
            access_token=AUTHENTIK_BEARER_TOKEN,
        )
    )


def main():
    LOGGER.info("Booting up discord bot")
    load_dotenv()

    bot = AuthentikSync(command_prefix="!", authentik_client=create_authentik_client())
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
