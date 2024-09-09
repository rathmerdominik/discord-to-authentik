import logging
import os
from typing import List

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
DISCORD_AUTO_SYNC_CREATE_DELETE = os.environ.get(
    "DISCORD_AUTO_SYNC_CREATE_DELETE", False
)
DISCORD_AUTO_SYNC_ROLES = os.environ.get("DISCORD_AUTO_SYNC_ROLES", False)


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

    @commands.is_owner()  # type: ignore
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

        await ctx.response.send_message(
            f"Synced roles: {"\n".join(synced_roles)} | Deleted roles: {"\n".join(deleted_roles)}",
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not DISCORD_AUTO_SYNC_ROLES:
            return

        core_api = authentik_client.CoreApi(self.authentik_client)
        assert after.guild is not None
        found_user = core_api.core_users_list(username=after.name).results

        if found_user is None:
            LOGGER.warning(f"User {after.name} not found in authentik. Sync manually!")
            return

        user_account_request = authentik_client.models.UserAccountRequest(
            pk=found_user[0].pk,
        )

        self._sync_roles(core_api, after, found_user, user_account_request)
        self._remove_roles(core_api, after, before.roles, user_account_request)

    def _sync_roles(
        self,
        core_api: authentik_client.CoreApi,
        after: discord.Member,
        found_user: List[authentik_client.models.User],
        user_account_request: authentik_client.models.UserAccountRequest,
    ):
        for role in after.roles:
            if role.is_bot_managed():
                continue
            if role.is_default():
                continue

            found_group = core_api.core_groups_list(name=role.name).results
            if not found_group:
                LOGGER.warning(
                    f"Group {role.name} not found in authentik. Sync manually!"
                )
                continue

            if (
                found_group[0].users is not None
                and found_user[0].pk in found_group[0].users
            ):
                LOGGER.debug(f"User {after.name} already in group {role.name}")
                continue

            if after.name in []:
                continue

            try:
                core_api.core_groups_add_user_create(
                    found_group[0].pk, user_account_request
                )
                LOGGER.info(f"Added user {after.name} to group {role.name}")
            except Exception as e:
                LOGGER.error(f"Error adding user to group: {e}")
                continue

    def _remove_roles(
        self,
        core_api: authentik_client.CoreApi,
        after: discord.Member,
        before_roles: List[discord.Role],
        user_account_request: authentik_client.models.UserAccountRequest,
    ):
        for group in core_api.core_groups_list().results:
            removed_roles = list(set(before_roles) - set(after.roles))
            if group.name not in [role.name for role in removed_roles]:
                continue

            if (
                group.attributes is None
                or group.attributes.get("discord_role_id") is None
            ):
                continue

            removed_role = after.guild.get_role(group.attributes["discord_role_id"])
            assert removed_role is not None
            core_api.core_groups_remove_user_create(group.pk, user_account_request)
            LOGGER.info(f"Removed user {after.name} from group {removed_role.name}")


class AuthentikSync(commands.Bot):
    def __init__(self, *args, **kwargs):
        intents = Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.members = True
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
