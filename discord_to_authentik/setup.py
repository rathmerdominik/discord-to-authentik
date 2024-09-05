import os
import sys
from pathlib import Path

import click

SYSTEMD_PATH = "/etc/systemd/system/discord-to-authentik.service"

euid = os.geteuid()
if euid != 0:
    exit("Needs to be run as root!")


def generate_service_file(
    hostname: str, token: str, owner_id: int, bot_token: str
) -> str:
    return f"""[Unit]
Description=A Discord bot that synchronizes your discord roles to authentik groups
After=network.target
Wants=network-online.target

[Service]
Restart=always
Type=simple
ExecStart={sys.executable} {Path(__file__).parent / "main.py"}
Environment=DISCORD_OWNER_ID={owner_id}
Environment=DISCORD_BOT_TOKEN={bot_token}
Environment=AUTHENTIK_HOST={hostname}
Environment=AUTHENTIK_TOKEN={token}


[Install]
WantedBy=multi-user.target
"""


def main():
    click.echo("| ---- Welcome to Discord to authentik ---- |")
    click.echo("This script will help you to create a service file for the bot.")

    hostname: str
    while True:
        hostname = (
            click.prompt(
                "Enter the basename of your authentik instance e.g https://auth.example.com",
                type=str,
            )
            + "/api/v3"
        )
        if click.confirm(f'The full api path will be "{hostname}". Is that correct?'):
            break

    while True:
        token = click.prompt("Enter your authentik token", type=str)
        if click.confirm(f'The authentik token will be "{token}". Is that correct?'):
            break

    while True:
        owner_id = click.prompt("Enter the discord ID of your account", type=int)
        if click.confirm(
            f'The owner of the bot will have the following ID: "{owner_id}". Is that correct?'
        ):
            break

    while True:
        bot_token = click.prompt("Enter the discord bot token", type=str)
        if click.confirm(f'The bot token will be "{bot_token}". Is that correct?'):
            break

    click.echo("Creating service file...")
    service_file = generate_service_file(hostname, token, owner_id, bot_token)
    with open(SYSTEMD_PATH, "w") as f:
        f.write(service_file)
    click.echo(f"Created service file at {SYSTEMD_PATH}")
    click.echo(
        "To start the bot, run `sudo systemctl enable --now discord-to-authentik`"
    )
