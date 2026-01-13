# Discord Calculator Bot — Numexa

import discord
from discord.ext import commands
import sympy as sp
import math
import json
import os
import itertools
import asyncio

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
DEFAULT_PREFIX = "!"
DATA_FILE = "bot_data.json"

CHECK_EMOJI_ID = 1460663385472503874
CROSS_EMOJI_ID = 1460663471623504185
DEVZONE_INVITE = "https://discord.gg/SmSx4uvVCD"

# ================= DATA STORAGE =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "prefixes": {},
            "noprefix": [],
            "angle": {},
            "counting": {}
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ================= BOT SETUP =================
def get_prefix(bot, message):
    return DEFAULT_PREFIX

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None
)

x = sp.symbols("x")

# ================= SAFE EVAL =================
def safe_eval(expr: str):
    expr = expr.replace("^", "**").replace("π", "pi")
    return eval(expr, {"__builtins__": None}, {
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log10,
        "sqrt": math.sqrt,
        "pi": math.pi,
        "e": math.e
    })

# ================= UI =================
class CalculatorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.expression = ""

    async def update(self, interaction):
        await interaction.response.edit_message(
            content=f"```{self.expression or '0'}```",
            view=self
        )

    @discord.ui.button(label="7", style=discord.ButtonStyle.secondary)
    async def b7(self, i, b): self.expression += "7"; await self.update(i)

    @discord.ui.button(label="8", style=discord.ButtonStyle.secondary)
    async def b8(self, i, b): self.expression += "8"; await self.update(i)

    @discord.ui.button(label="9", style=discord.ButtonStyle.secondary)
    async def b9(self, i, b): self.expression += "9"; await self.update(i)

    @discord.ui.button(label="+", style=discord.ButtonStyle.primary)
    async def add(self, i, b): self.expression += "+"; await self.update(i)

    @discord.ui.button(label="=", style=discord.ButtonStyle.success)
    async def equals(self, i, b):
        try:
            self.expression = str(safe_eval(self.expression))
        except:
            self.expression = "Error"
        await self.update(i)

    @discord.ui.button(label="C", style=discord.ButtonStyle.danger)
    async def clear(self, i, b):
        self.expression = ""
        await self.update(i)

# ================= COMMANDS =================
@bot.command()
async def ui(ctx):
    await ctx.send("Calculator", view=CalculatorView())

@bot.command()
@commands.has_permissions(administrator=True)
async def setcount(ctx):
    gid = str(ctx.guild.id)
    data["counting"][gid] = {
        "channel": ctx.channel.id,
        "current": 0,
        "last_user": None
    }
    save_data()
    await ctx.send(f"✅ Counting enabled in {ctx.channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def resetcount(ctx):
    gid = str(ctx.guild.id)
    if gid in data["counting"]:
        data["counting"][gid]["current"] = 0
        data["counting"][gid]["last_user"] = None
        save_data()
        await ctx.send("🔄 Count reset to **0**")

# ================= COUNTING LOGIC =================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    gid = str(message.guild.id)
    counting = data["counting"].get(gid)

    if counting and message.channel.id == counting["channel"]:
        content = message.content.strip()

        check = bot.get_emoji(CHECK_EMOJI_ID) or "✅"
        cross = bot.get_emoji(CROSS_EMOJI_ID) or "❌"

        if not content.isdigit():
            counting["current"] = 0
            counting["last_user"] = None
            save_data()
            await message.add_reaction(cross)
            return

        number = int(content)
