# Discord Calculator Bot 
# Features:
# - Custom prefix (persistent, per server)
# - No-prefix users (persistent, owner controlled)
# - Prefix + Slash commands
# - UI using Discord Buttons
# - DEG / RAD angle switch (persistent)
# - Scientific, calculus & differential equations

import discord
from discord.ext import commands
import sympy as sp
import math
import json
import os

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
OWNER_ID = 800553680704110624
EXTRA_OWNERS = {111111111111111111}
DEFAULT_PREFIX = "!"

DATA_FILE = "bot_data.json"

# ================= DATA STORAGE =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"prefixes": {}, "noprefix": [], "angle": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Load persistent data
data = load_data()
custom_prefixes = {int(k): v for k, v in data["prefixes"].items()}
no_prefix_users = set(data["noprefix"])
angle_mode = {int(k): v for k, v in data["angle"].items()}

# ================= PREFIX HANDLER =================
def get_prefix(bot, message):
    if message.author.id in no_prefix_users:
        return ""
    return custom_prefixes.get(message.guild.id if message.guild else None, DEFAULT_PREFIX)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=get_prefix, intents=intents)

x = sp.symbols('x')

# ================= SAFE EVAL =================
def safe_eval(expr: str, user_id=None):
    expr = expr.replace('^', '**').replace('π', 'pi')
    mode = angle_mode.get(user_id, 'rad')

    def sin(v): return math.sin(math.radians(v)) if mode == 'deg' else math.sin(v)
    def cos(v): return math.cos(math.radians(v)) if mode == 'deg' else math.cos(v)
    def tan(v): return math.tan(math.radians(v)) if mode == 'deg' else math.tan(v)

    return eval(expr, {"__builtins__": None}, {
        'sin': sin,
        'cos': cos,
        'tan': tan,
        'log': math.log10,
        'ln': math.log,
        'sqrt': math.sqrt,
        'pi': math.pi,
        'e': math.e
    })

# ================= UI =================
class CalculatorView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.expression = ""
        self.user_id = user_id

    async def update(self, interaction):
        await interaction.response.edit_message(content=f"```{self.expression}```", view=self)

    @discord.ui.button(label="7", style=discord.ButtonStyle.secondary)
    async def seven(self, interaction, button): self.expression += "7"; await self.update(interaction)

    @discord.ui.button(label="8", style=discord.ButtonStyle.secondary)
    async def eight(self, interaction, button): self.expression += "8"; await self.update(interaction)

    @discord.ui.button(label="9", style=discord.ButtonStyle.secondary)
    async def nine(self, interaction, button): self.expression += "9"; await self.update(interaction)

    @discord.ui.button(label="+", style=discord.ButtonStyle.primary)
    async def add(self, interaction, button): self.expression += "+"; await self.update(interaction)

    @discord.ui.button(label="=", style=discord.ButtonStyle.success)
    async def equal(self, interaction, button):
        try:
            self.expression = str(safe_eval(self.expression, self.user_id))
        except:
            self.expression = "Error"
        await self.update(interaction)

    @discord.ui.button(label="C", style=discord.ButtonStyle.danger)
    async def clear(self, interaction, button): self.expression = ""; await self.update(interaction)

# ================= PREFIX COMMANDS =================
@bot.command()
async def calc(ctx, *, expression: str):
    try:
        await ctx.send(f"Result: **{safe_eval(expression, ctx.author.id)}**")
    except:
        await ctx.send("Invalid expression")

@bot.command()
async def diff(ctx, *, expression: str):
    try:
        await ctx.send(f"d/dx: **{sp.diff(sp.sympify(expression), x)}**")
    except:
        await ctx.send("Invalid expression")

@bot.command()
async def integrate(ctx, *, expression: str):
    try:
        await ctx.send(f"∫dx: **{sp.integrate(sp.sympify(expression), x)} + C**")
    except:
        await ctx.send("Invalid expression")

@bot.command()
async def dsolve(ctx, *, equation: str):
    try:
        eq = sp.sympify(equation)
        await ctx.send(f"Solution: **{sp.dsolve(eq)}**")
    except:
        await ctx.send("Invalid differential equation")

# ================= SLASH COMMANDS =================
@bot.tree.command(name="calc")
async def slash_calc(interaction: discord.Interaction, expression: str):
    try:
        await interaction.response.send_message(f"Result: **{safe_eval(expression, interaction.user.id)}**")
    except:
        await interaction.response.send_message("Invalid expression")

@bot.tree.command(name="diff")
async def slash_diff(interaction: discord.Interaction, expression: str):
    try:
        await interaction.response.send_message(f"d/dx: **{sp.diff(sp.sympify(expression), x)}**")
    except:
        await interaction.response.send_message("Invalid expression")

@bot.tree.command(name="integrate")
async def slash_integrate(interaction: discord.Interaction, expression: str):
    try:
        await interaction.response.send_message(f"∫dx: **{sp.integrate(sp.sympify(expression), x)} + C**")
    except:
        await interaction.response.send_message("Invalid expression")

@bot.tree.command(name="dsolve")
async def slash_dsolve(interaction: discord.Interaction, equation: str):
    try:
        await interaction.response.send_message(f"Solution: **{sp.dsolve(sp.sympify(equation))}**")
    except:
        await interaction.response.send_message("Invalid differential equation")

# ================= SETTINGS =================
@bot.command()
async def angle(ctx, mode: str):
    if mode.lower() not in ('deg', 'rad'):
        return await ctx.send("Use deg or rad")
    angle_mode[ctx.author.id] = mode.lower()
    data['angle'][str(ctx.author.id)] = mode.lower()
    save_data()
    await ctx.send(f"Angle mode set to **{mode.upper()}**")

@bot.command()
async def setprefix(ctx, prefix: str):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("Admin only")
    custom_prefixes[ctx.guild.id] = prefix
    data['prefixes'][str(ctx.guild.id)] = prefix
    save_data()
    await ctx.send(f"Prefix set to `{prefix}`")

@bot.command()
async def noprefix(ctx, member: discord.Member):
    if ctx.author.id not in {OWNER_ID} | EXTRA_OWNERS:
        return await ctx.send("Owner only")
    no_prefix_users.add(member.id)
    data['noprefix'] = list(no_prefix_users)
    save_data()
    await ctx.send(f"No-prefix enabled for {member.mention}")

@bot.command()
async def removeprefixaccess(ctx, member: discord.Member):
    if ctx.author.id not in {OWNER_ID} | EXTRA_OWNERS:
        return await ctx.send("Owner only")
    no_prefix_users.discard(member.id)
    data['noprefix'] = list(no_prefix_users)
    save_data()
    await ctx.send(f"No-prefix removed for {member.mention}")

@bot.command()
async def ui(ctx):
    await ctx.send("Calculator", view=CalculatorView(ctx.author.id))

# ================= READY =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)
