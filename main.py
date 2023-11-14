from pathlib import Path
import discord
from discord.ext import tasks
from discord import app_commands
from domain.classes import Server
from persistence.csv import CSVDomainLoader, CSVDomainSaver

DATA_FOLDER: Path = Path("data")
SERVERS: list[Server] = CSVDomainLoader.load(DATA_FOLDER)


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        check_updates.start(self)
        update_counter.start(self)
        print("Ready to go\n")


intents = discord.Intents.default()
client = MyClient(intents=intents)


@tasks.loop(minutes=5)
async def update_counter(bot: MyClient):
    count = 0
    for server in SERVERS:
        for channel in server.get_channels():
            count += len(channel.get_websites())

    activity = discord.Game(f"I'm monitoring {count} websites!")
    await bot.change_presence(activity=activity)


@tasks.loop(minutes=10)
async def check_updates(bot: MyClient):
    for server in SERVERS:
        for channel in server.get_channels():
            for website in channel.get_websites():
                monitor = website.get_monitor()
                monitor.check_update()
                if monitor.is_updated():
                    output: str = f"{website.get_name} è stato aggiornato!\n"
                    for user in website.get_users():
                        output += f"* <@{user.get_id()}>\n"
                    await bot.get_channel(website.get_channel().get_id()).send(output)
    CSVDomainSaver.save(SERVERS, DATA_FOLDER)

@client.tree.command(
    description="Add a website to the list of monitored websites",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.describe(
    name="The name of this subscription",
    website="The full URL of the website that you want to monitor for changes",
)
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def monitor_website(interaction: discord.Interaction, name: str, website: str):
    # aggiungere il sito web ai monitorati
    guild:Server|None=None
    for server in SERVERS:
        if server.get_id()==interaction.guild_id
            guild=server

    if guild is None:
        await interaction.response.send_message(
            f"This discord server is unrecognized"
        )
        return
    
    if Liste_di_monitorati[interaction.guild_id].add_website(name, website):
        await interaction.response.send_message(
            f"'{name}' is now being monitored at '{website}'"
        )
    else:
        await interaction.response.send_message(
            f"'{name}' was already being monitored at '{website}'"
        )