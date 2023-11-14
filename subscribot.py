import discord
import csv
from watchlist import Watchlist
from subscription import Subscription
from discord.ext import tasks
from discord import app_commands


def save_data():
    output = []
    for watchl in Liste_di_monitorati.values():
        output.append(f"{watchl.guild},{watchl.channel}\n")
    with open("data/watchlists.csv", "w") as dest:
        dest.writelines(output)

    output = []
    for watchl in Liste_di_monitorati.values():
        for monitorato in watchl.monitoring.values():
            output.append(
                f"{monitorato.nome},{monitorato.website},{monitorato.last_checksum},{watchl.guild}\n"
            )
    with open("data/subscriptions.csv", "w") as dest:
        dest.writelines(output)

    output = []
    for watchl in Liste_di_monitorati.values():
        for monitorato in watchl.monitoring.values():
            for iscritto in monitorato.iscritti:
                output.append(f"{iscritto},{monitorato.nome},{watchl.guild}\n")
    with open("data/iscritti.csv", "w") as dest:
        dest.writelines(output)


def load_data() -> dict[int, Watchlist]:
    liste: dict[int, Watchlist] = {}
    with open("data/watchlists.csv", "r") as src:
        data = src.readlines()
    for guild, channel in csv.reader(data):
        liste[int(guild)] = Watchlist(int(channel), int(guild))

    with open("data/subscriptions.csv", "r") as src:
        data = src.readlines()
    for nome, website, checksum, guild in csv.reader(data):
        liste[int(guild)]._add(Subscription(nome, website, checksum))

    with open("data/iscritti.csv", "r") as src:
        data = src.readlines()
    for iscritto, nome, guild in csv.reader(data):
        liste[int(guild)].subscribe(int(iscritto), nome)

    return liste


Liste_di_monitorati: dict[int, Watchlist] = load_data()


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


@tasks.loop(seconds=10)
async def update_counter(bot: MyClient):
    count = 0
    for watchl in Liste_di_monitorati.values():
        for _ in watchl.monitoring:
            count += 1

    activity = discord.Game(f"I'm monitoring {count} websites!")
    await bot.change_presence(activity=activity)


@tasks.loop(minutes=1)
async def check_updates(bot: MyClient):
    for watchl in Liste_di_monitorati.values():
        for monitorato in watchl.monitoring.values():
            if monitorato.check_update():
                output = f"{monitorato.nome} è stato aggiornato!\n"
                for user in monitorato.iscritti:
                    output += f"* <@{user}>\n"
                await bot.get_channel(watchl.channel).send(output)
    save_data()


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
    if Liste_di_monitorati[interaction.guild_id].add_website(name, website):
        await interaction.response.send_message(
            f"'{name}' is now being monitored at '{website}'"
        )
    else:
        await interaction.response.send_message(
            f"'{name}' was already being monitored at '{website}'"
        )


@client.tree.command(
    description="Remove a website from the list of monitored websites",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.describe(name="The name of the subscription you want to remove")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def unmonitor_website(interaction: discord.Interaction, name: str):
    # rimuovere il sito dai monitorati
    if not Liste_di_monitorati[interaction.guild_id].rem_website(name):
        await interaction.response.send_message(
            f"{name} is not being monitored anymore"
        )
    else:
        await interaction.response.send_message(
            f"{name} is not being monitored anymore"
        )


@client.tree.command(
    description="List the currently monitored websites",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.checks.has_permissions(send_messages=True)
async def list_websites(interaction: discord.Interaction):
    # mostrare i monitorati
    await interaction.response.send_message(
        "Ecco a te:\n\n" + str(Liste_di_monitorati[interaction.guild_id])
    )


@client.tree.command(
    description="Subscribe to one of the monitored websites",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.describe(name="The name of the website you want to subscribe to")
@discord.app_commands.checks.has_permissions(send_messages=True)
async def subscribe(interaction: discord.Interaction, name: str):
    if Liste_di_monitorati[interaction.guild_id].subscribe(interaction.user.id, name):
        await interaction.response.send_message(
            f"<@{interaction.user.id}> is now subscribed to {name}"
        )
    else:
        await interaction.response.send_message(
            f"<@{interaction.user.id}> is already subscribed to {name}, or {name} is not being monitored"
        )




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
    if Liste_di_monitorati[interaction.guild_id].unsubscribe(interaction.user.id, name):
        await interaction.response.send_message(
            f"<@{interaction.user.id}> is now unsubscribed from {name}"
        )
    else:
        await interaction.response.send_message(
            f"<@{interaction.user.id}> is not subscribed to {name}, or {name} is not being monitored"
        )


@client.tree.command(
    description="List the currently monitored websites",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.checks.has_permissions(send_messages=True)
async def list_subscriptions(interaction: discord.Interaction):
    # mostrare i monitorati di questo utente
    output = "Ecco i siti che segui:\n\n"
    for monitorato in Liste_di_monitorati[interaction.guild_id].monitoring.values():
        if interaction.user.id in monitorato.iscritti:
            output += f"* {monitorato.nome}\n"
    await interaction.response.send_message(output)


@client.tree.command(
    description="Subscribe someone to this website",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.describe(member="Tag the person you want to add",name="The website you want to subscribe them to" )
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def subscribe_member(interaction:discord.Interaction, member:str,name:str):
    if Liste_di_monitorati[interaction.guild_id].subscribe(member[2:-1], name):
        await interaction.response.send_message(
            f"<@{member[2:-1]}> is now subscribed to {name}"
        )
    else:
        await interaction.response.send_message(
            f"<@{member[2:-1]}> is already subscribed to {name}, or {name} is not being monitored"
        )

@client.tree.command(
    description="Unubscribe someone from this website",
    nsfw=False,
    auto_locale_strings=False,
)
@discord.app_commands.describe(member="Tag the person you want to unsubscribe",name="The website you want to unsubscribe them from" )
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def unsubscribe_member(interaction:discord.Interaction, member:str,name:str):
    if Liste_di_monitorati[interaction.guild_id].unsubscribe(member[2:-1], name):
        await interaction.response.send_message(
            f"<@{member[2:-1]}> is now unsubscribed from {name}"
        )
    else:
        await interaction.response.send_message(
            f"<@{member[2:-1]}> was not subscribed to {name}, or {name} is not being monitored"
        )

with open("token.txt", "r") as file:
    tkn = file.readline().strip()

client.run(tkn)
