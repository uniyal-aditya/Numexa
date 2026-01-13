# Discord Calculator Bot — Numexa
# Features:
# - Custom prefix (persistent, per server)
# - No-prefix users (persistent, owner controlled)
# - Prefix + Slash commands
# - UI using Discord Buttons
# - DEG / RAD angle switch (persistent)
# - Scientific, calculus & differential equations
# - Server-based counting channel system (admin configurable)

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
OWNER_ID = 800553680704110624
EXTRA_OWNERS = {111111111111111111}
DEFAULT_PREFIX = "!"
DATA_FILE = "bot_data.json"
CHECK_EMOJI_ID = 1460663385472503874
CROSS_EMOJI_ID = 1460663471623504185


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

custom_prefixes = {int(k): v for k, v in data.get("prefixes", {}).items()}
no_prefix_users = set(data.get("noprefix", []))
angle_mode = {int(k): v for k, v in data.get("angle", {}).items()}

if "counting" not in data:
    data["counting"] = {}

# ================= PREFIX HANDLER =================
def get_prefix(bot, message):
    if message.author.id in no_prefix_users:
        return ""
    return custom_prefixes.get(message.guild.id if message.guild else None, DEFAULT_PREFIX)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None
)

x = sp.symbols("x")

# ================= SAFE EVAL =================
def safe_eval(expr: str, user_id=None):
    expr = expr.replace("^", "**").replace("π", "pi")
    mode = angle_mode.get(user_id, "rad")

    def sin(v): return math.sin(math.radians(v)) if mode == "deg" else math.sin(v)
    def cos(v): return math.cos(math.radians(v)) if mode == "deg" else math.cos(v)
    def tan(v): return math.tan(math.radians(v)) if mode == "deg" else math.tan(v)

    return eval(expr, {"__builtins__": None}, {
        "sin": sin,
        "cos": cos,
        "tan": tan,
        "log": math.log10,
        "ln": math.log,
        "sqrt": math.sqrt,
        "pi": math.pi,
        "e": math.e
    })

# ================= UI =================
class CalculatorView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.expression = ""
        self.user_id = user_id

    async def update(self, interaction):
        await interaction.response.edit_message(
            content=f"```{self.expression}```",
            view=self
        )

    @discord.ui.button(label="7", style=discord.ButtonStyle.secondary)
    async def seven(self, i, b): self.expression += "7"; await self.update(i)

    @discord.ui.button(label="8", style=discord.ButtonStyle.secondary)
    async def eight(self, i, b): self.expression += "8"; await self.update(i)

    @discord.ui.button(label="9", style=discord.ButtonStyle.secondary)
    async def nine(self, i, b): self.expression += "9"; await self.update(i)

    @discord.ui.button(label="+", style=discord.ButtonStyle.primary)
    async def add(self, i, b): self.expression += "+"; await self.update(i)

    @discord.ui.button(label="=", style=discord.ButtonStyle.success)
    async def equal(self, i, b):
        try:
            self.expression = str(safe_eval(self.expression, self.user_id))
        except:
            self.expression = "Error"
        await self.update(i)

    @discord.ui.button(label="C", style=discord.ButtonStyle.danger)
    async def clear(self, i, b): self.expression = ""; await self.update(i)

# ================= HELP =================
def help_embed():
    embed = discord.Embed(
        title="📘 Numexa — Help",
        description="Scientific calculator & math utility bot",
        color=0x8A2BE2
    )

    embed.add_field(
        name="🧮 Calculator",
        value="`!calc`, `/calc`",
        inline=False
    )

    embed.add_field(
        name="📐 Calculus",
        value="`!diff`, `!integrate`, `!dsolve`",
        inline=False
    )

    embed.add_field(
        name="🔢 Counting System",
        value=(
            "`!setcount` (Admin)\n"
            "`!resetcount` (Admin)\n"
            "Count numbers in a channel starting from **0**"
        ),
        inline=False
    )

    embed.add_field(
        name="🖥 UI",
        value="`!ui`",
        inline=False
    )

    embed.set_footer(text="Numexa • Scientific Discord Bot")
    return embed

# ================= PREFIX COMMANDS =================
@bot.command()
async def calc(ctx, *, expr: str):
    try:
        await ctx.send(f"**Result:** {safe_eval(expr, ctx.author.id)}")
    except:
        await ctx.send("❌ Invalid expression")

@bot.command()
async def diff(ctx, *, expr: str):
    try:
        await ctx.send(f"**d/dx:** {sp.diff(sp.sympify(expr), x)}")
    except:
        await ctx.send("❌ Invalid expression")

@bot.command()
async def integrate(ctx, *, expr: str):
    try:
        await ctx.send(f"**∫dx:** {sp.integrate(sp.sympify(expr), x)} + C")
    except:
        await ctx.send("❌ Invalid expression")

@bot.command()
async def dsolve(ctx, *, eq: str):
    try:
        await ctx.send(f"**Solution:** {sp.dsolve(sp.sympify(eq))}")
    except:
        await ctx.send("❌ Invalid equation")

@bot.command(name="help")
async def help_cmd(ctx):
    await ctx.send(embed=help_embed())

@bot.command()
@commands.has_permissions(administrator=True)
async def setcount(ctx):
    gid = str(ctx.guild.id)
    data["counting"][gid] = {
        "channel": ctx.channel.id,
        "current": 0
    }
    save_data()
    await ctx.send(f"✅ Counting channel set to {ctx.channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def resetcount(ctx):
    gid = str(ctx.guild.id)
    if gid in data["counting"]:
        data["counting"][gid]["current"] = 0
        save_data()
        await ctx.send("🔄 Count reset to **0**")

@bot.command()
async def ui(ctx):
    await ctx.send("Calculator", view=CalculatorView(ctx.author.id))

# ================= SLASH HELP =================
@bot.tree.command(name="help")
async def slash_help(interaction: discord.Interaction):
    await interaction.response.send_message(embed=help_embed(), ephemeral=True)

# ================= COUNTING LOGIC =================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    gid = str(message.guild.id)
    counting = data["counting"].get(gid)

    if counting and message.channel.id == counting["channel"]:
        content = message.content.strip()

        check_emoji = bot.get_emoji(CHECK_EMOJI_ID)
        cross_emoji = bot.get_emoji(CROSS_EMOJI_ID) if CROSS_EMOJI_ID else "❌"

        # Must be a number
        if not content.isdigit():
            counting["current"] = 0
            counting["last_user"] = None
            save_data()
            await message.add_reaction(cross_emoji)
            return

        number = int(content)

        # Prevent same user twice
        if counting.get("last_user") == message.author.id:
            counting["current"] = 0
            counting["last_user"] = None
            save_data()
            await message.add_reaction(cross_emoji)
            return

        # Wrong number
        if number != counting["current"]:
            counting["current"] = 0
            counting["last_user"] = None
            save_data()
            await message.add_reaction(cross_emoji)
            return

        # Correct number
        counting["current"] += 1
        counting["last_user"] = message.author.id
        save_data()

        if check_emoji:
            await message.add_reaction(check_emoji)

    await bot.process_commands(message)


# ================= STATUS =================
async def status_loop():
    statuses = itertools.cycle([
        discord.Activity(type=discord.ActivityType.watching, name="math problems"),
        discord.Activity(type=discord.ActivityType.playing, name="with equations"),
        discord.Activity(type=discord.ActivityType.listening, name="!help | /help"),
    ])

    await bot.wait_until_ready()
    while not bot.is_closed():
        await bot.change_presence(activity=next(statuses))
        await asyncio.sleep(30)

@bot.event
async def on_ready():
    await bot.tree.sync()
    bot.loop.create_task(status_loop())
    print(f"Logged in as {bot.user}")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable not set")

bot.run(TOKEN)
