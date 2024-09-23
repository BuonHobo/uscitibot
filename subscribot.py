from pathlib import Path
import discord
from discord.ext import tasks
from discord import app_commands
from domain.classes import Base, Channel, ETagMonitor, Server, Website, User
from persistence.csv import CSVDomainLoader, CSVDomainSaver
import os

DATA_FOLDER: Path = Path("data")
BASE: Base = CSVDomainLoader.load(DATA_FOLDER)


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        await update_counter(self)
        if not check_updates.is_running():
            check_updates.start(self)
        else:
            check_updates.restart(self)
        print("Ready to go\n")


intents = discord.Intents.default()
client = MyClient(intents=intents)


async def update_counter(bot: MyClient):
    count = 0
    for server in BASE.get_servers():
        for channel in server.get_channels():
            count += len(channel.get_websites())

    activity = discord.Game(f"I'm monitoring {count} websites!")
    await bot.change_presence(activity=activity)


@tasks.loop(minutes=5)
async def check_updates(bot: MyClient):
    for server in BASE.get_servers():
        for channel in server.get_channels():
            for website in channel.get_websites():
                monitor = website.get_monitor()
                monitor.check_update()
                update= monitor.is_updated()
                if update:
                    output: str = f"{website.get_hyperlink()} was updated!\n"
                    for user in website.get_users():
                        output += f"* <@{user.get_id()}>\n"
                    output += "\n```html\n"
                    output += update
                    output += "```"
                    if len(output) > 2000:
                        addition = "...```\nThe message was truncated because it was too long :("
                        output = output[:2000-len(addition)] + addition
                    await bot.get_channel(website.get_channel().get_id()).send(output)  # type: ignore
    CSVDomainSaver.save(BASE, DATA_FOLDER)


@client.tree.command(
    description="Add a website to the list of monitored websites",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.describe(
    name="The name of this subscription",
    website="The full URL of the website that you want to monitor for changes",
    channel="The discord channel where the updates should be sent",
)
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def monitor_website(
    interaction: discord.Interaction, name: str, website: str, channel: str
):
    # If this is not a discord server (like a DM)
    if interaction.guild_id is None:
        await interaction.response.send_message(f"This is not a discord server")
        return

    guild: Server | None = BASE.get_server(interaction.guild_id)
    # If this server is not a registered one
    if guild is None:
        await interaction.response.send_message(f"This discord server is unrecognized")
        return

    try:
        chanid = int(channel[2:-1])

    # If channel is not valid
    except ValueError:
        await interaction.response.send_message(f"Please use the #<channel> format")
        return

    chan = guild.get_channel(chanid)
    if chan is None:
        chan = Channel(chanid, guild)

    webs = Website(name, website, chan, ETagMonitor)
    webs.get_monitor().check_update()
    CSVDomainSaver.save(BASE, DATA_FOLDER)
    await interaction.response.send_message(
        f"{webs.get_hyperlink()} is now being monitored.\nUpdates will be posted in {chan.get_hyperlink()}"
    )

    await update_counter(client)


@client.tree.command(
    description="Remove a website from the list of monitored websites",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.describe(name="The name of the subscription you want to remove")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def unmonitor_website(interaction: discord.Interaction, name: str):
    if interaction.guild_id is None:
        await interaction.response.send_message(f"This is not a discord server")
        return

    guild: Server | None = BASE.get_server(interaction.guild_id)
    if guild is None:
        await interaction.response.send_message(f"This discord server is unrecognized")
        return

    webs = guild.remove_website(name)
    if webs:
        CSVDomainSaver.save(BASE, DATA_FOLDER)
        await interaction.response.send_message(
            f"{webs.get_hyperlink()} is not being monitored anymore"
        )
        await update_counter(client)
    else:
        await interaction.response.send_message(f"{name} wasn't being monitored")


@client.tree.command(
    description="List the currently monitored websites",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.checks.has_permissions(send_messages=True)
async def list_websites(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(f"This is not a discord server")
        return

    guild: Server | None = BASE.get_server(interaction.guild_id)
    if guild is None:
        await interaction.response.send_message(f"This discord server is unrecognized")
        return

    monitorati = guild.get_websites()
    if len(monitorati) > 0:
        output = ""
        for web in monitorati:
            output += (
                f"* {web.get_hyperlink()} in {web.get_channel().get_hyperlink()}\n"
            )
    else:
        output = "No websites are being monitored"
    await interaction.response.send_message(output)


@client.tree.command(
    description="Subscribe to one of the monitored websites",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.describe(name="The name of the website you want to subscribe to")
@discord.app_commands.checks.has_permissions(send_messages=True)
async def subscribe(interaction: discord.Interaction, name: str):
    # If this is not a discord server (like a DM)
    if interaction.guild_id is None:
        await interaction.response.send_message(f"This is not a discord server")
        return

    guild: Server | None = BASE.get_server(interaction.guild_id)
    # If this server is not a registered one
    if guild is None:
        await interaction.response.send_message(f"This discord server is unrecognized")
        return

    website = guild.get_website(name)
    if not website:
        await interaction.response.send_message(f"{name} is not being monitored")
        return

    user = guild.get_user(interaction.user.id)
    if not user:
        user = User(interaction.user.id)
        guild.add_user(user)

    user.add_website(website)

    await interaction.response.send_message(
        f"{user.get_hyperlink()} is now subscribed to {website.get_hyperlink()}"
    )

    CSVDomainSaver.save(BASE, DATA_FOLDER)


@client.tree.command(
    description="Unsubscribe from one of the monitored websites",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.describe(
    name="The name of the website you want to unsubscribe from"
)
@discord.app_commands.checks.has_permissions(send_messages=True)
async def unsubscribe(interaction: discord.Interaction, name: str):
    if interaction.guild_id is None:
        await interaction.response.send_message(f"This is not a discord server")
        return

    guild: Server | None = BASE.get_server(interaction.guild_id)
    if guild is None:
        await interaction.response.send_message(f"This discord server is unrecognized")
        return

    user = guild.get_user(interaction.user.id)
    if not user:
        await interaction.response.send_message(
            f"<@{interaction.user.id}> wasn't subscribed to {name}"
        )
        return

    website = user.remove_website(name)
    if not website:
        await interaction.response.send_message(
            f"{user.get_hyperlink()} wasn't subscribed to {name}"
        )
        return

    await interaction.response.send_message(
        f"{user.get_hyperlink()} is now unsubscribed from {website.get_hyperlink()}"
    )

    CSVDomainSaver.save(BASE, DATA_FOLDER)


@client.tree.command(
    description="List the currently monitored websites",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.checks.has_permissions(send_messages=True)
async def list_subscriptions(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(f"This is not a discord server")
        return

    guild: Server | None = BASE.get_server(interaction.guild_id)
    if guild is None:
        await interaction.response.send_message(f"This discord server is unrecognized")
        return

    user = guild.get_user(interaction.user.id)
    if not user:
        await interaction.response.send_message(f"You aren't subscribed to anything")
        return

    websites = user.get_websites()

    if len(websites) > 0:
        output = ""
        for web in websites:
            output += (
                f"* {web.get_hyperlink()} in {web.get_channel().get_hyperlink()}\n"
            )
    else:
        output = "You aren't subscribed to anything"
    # mostrare i monitorati
    await interaction.response.send_message(output)


tkn = os.environ.get("DISCORD_TOKEN")

client.run(tkn)
