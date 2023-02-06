import discord
from discord.ext import tasks
from random import choice
import datetime
import requests

WEBSITE="https://www.dia.uniroma3.it/~atzeni/didattica/BDN/20222023/proveParziali.html"
LAST_DATE='Wed, 11 Jan 2023 09:17:49 GMT'

class MyClient(discord.Client):
    async def on_ready(self):
        check_voti_pos.start(self)
        check_voti_neg.start(self)
        update_counter.start(self)
        print("Ready to go\n")


@tasks.loop(seconds=10)
async def update_counter(bot: MyClient):
    seconds:datetime.timedelta=(check_voti_neg.next_iteration-datetime.datetime.now(datetime.timezone.utc)).seconds/60
    seconds=round(seconds)
    activity= discord.Game(f"I'm checking every minute! Next message in {seconds}'")
    await bot.change_presence(activity=activity)


@tasks.loop(minutes=1)
async def check_voti_pos(bot:MyClient):
    global risposta
    risposta=requests.head(WEBSITE)
    if risposta.headers["Last-Modified"]!=LAST_DATE:
        await bot.get_channel(1071923920527167530).send(f"SONO USCITI <@&962777211604172891>")
        await bot.get_channel(1071923920527167530).send(f"Il mio lavoro è finito, mi spengo")
        exit(0)

@tasks.loop(minutes=30)
async def check_voti_neg(bot):
    if risposta.headers["Last-Modified"]==LAST_DATE:
        await bot.get_channel(1071923920527167530).send("(non) SONO USCITI")

with open("token.txt", "r") as file:
    tkn = file.readline().strip()
risposta=requests.head(WEBSITE)

intents = discord.Intents.default()
client = MyClient(intents=intents)
client.run(tkn)