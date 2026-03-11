# ============================================================
#  Numexa — Scientific Discord Calculator Bot
#  Premium system + all premium features
# ============================================================

import discord
from discord import app_commands
from discord.ext import commands
import sympy as sp
import math, json, os, itertools, asyncio, time, io, random
from simpleeval import simple_eval
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ───────────────────────────── CONFIG ─────────────────────────────
TOKEN            = os.getenv("TOKEN")
OWNER_ID         = 800553680704110624
EXTRA_OWNERS     = set()  # add extra owner IDs here if needed
ALL_OWNERS       = EXTRA_OWNERS | {OWNER_ID}
DEFAULT_PREFIX   = "!"
DATA_FILE        = "bot_data.json"
CHECK_EMOJI_ID   = 1460832001723732139
CROSS_EMOJI_ID   = 1460831985428594789
DEVZONE_INVITE   = "https://discord.gg/SmSx4uvVCD"
INVITE_URL       = (
    "https://discord.com/oauth2/authorize"
    "?client_id=1460289617264775333"
    "&permissions=5629501681765440"
    "&scope=bot+applications.commands"
)
DASHBOARD_URL    = "https://numexa.netlify.app"
BOT_COLOR        = 0x8A2BE2
PREMIUM_COLOR    = 0xFFD700
START_TIME       = time.time()
TRIAL_DAYS       = 7

DAILY_PROBLEMS = [
    ("Differentiate f(x) = x³ + 2x² − 5x + 1", "3x² + 4x − 5"),
    ("Integrate f(x) = 4x³ − 6x + 2", "x⁴ − 3x² + 2x + C"),
    ("Evaluate: sin(π/6) + cos(π/3)", "1"),
    ("Simplify: log(1000) + log(0.001)", "0"),
    ("Solve: What is √(144) + √(225)?", "27"),
    ("Evaluate: 2⁸ − 2⁶", "192"),
    ("What is the derivative of e^x?", "e^x"),
    ("Integrate f(x) = 1/x", "ln|x| + C"),
    ("Evaluate: tan(45°) × cos(60°)", "0.5"),
    ("What is the limit of sin(x)/x as x→0?", "1"),
    ("Simplify: ln(e⁵)", "5"),
    ("Evaluate: floor(π²)", "9"),
    ("What is √2 × √8?", "4"),
    ("Differentiate f(x) = sin(x)·cos(x)", "cos(2x)"),
    ("Evaluate: 5! / 3!", "20"),
]

# ─────────────────────── APP EMOJI CACHE ──────────────────────────
_app_emojis: dict = {}

def CHECK() -> str:
    e = _app_emojis.get("checkmark")
    return str(e) if e else "✅"

def CROSS() -> str:
    e = _app_emojis.get("wrong")
    return str(e) if e else "❌"

def ok(msg: str)  -> str: return f"{CHECK()} {msg}"
def err(msg: str) -> str: return f"{CROSS()} {msg}"


# ───────────────────────── DATA STORAGE ───────────────────────────
def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"prefixes": {}, "noprefix": [], "angle": {},
                "counting": {}, "premium": {}, "history": {},
                "bookmarks": {}, "daily": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

for _key, _default in (
    ("prefixes", {}), ("noprefix", []), ("angle", {}),
    ("counting", {}), ("premium", {}), ("history", {}),
    ("bookmarks", {}), ("daily", {}),
):
    data.setdefault(_key, _default)

custom_prefixes = {int(k): v for k, v in data["prefixes"].items()}
no_prefix_users = set(data["noprefix"])
angle_mode      = {int(k): v for k, v in data["angle"].items()}


# ──────────────────────── PREFIX HANDLER ──────────────────────────
def get_prefix(bot, message):
    guild_id      = message.guild.id if message.guild else None
    server_prefix = custom_prefixes.get(guild_id, DEFAULT_PREFIX)
    if message.author.id in no_prefix_users:
        return ["", server_prefix]
    return [server_prefix]


intents = discord.Intents.default()
intents.message_content = True
intents.members         = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)
x   = sp.symbols("x")


# ═══════════════════════ PREMIUM SYSTEM ═══════════════════════════

def get_premium(guild_id: int) -> dict | None:
    gid = str(guild_id)
    rec = data["premium"].get(gid)
    if not rec:
        return None
    if rec.get("expires") and time.time() > rec["expires"]:
        rec["active"] = False
        save_data()
        return None
    return rec if rec.get("active") else None

def is_premium(guild_id: int) -> bool:
    return get_premium(guild_id) is not None

def has_premium_access(ctx_or_interaction) -> bool:
    """
    True if:
    - caller is OWNER_ID (Aditya) — always allowed, any server, no premium needed
    - OR the server has an active premium subscription
    """
    if isinstance(ctx_or_interaction, commands.Context):
        user_id  = ctx_or_interaction.author.id
        guild_id = ctx_or_interaction.guild.id if ctx_or_interaction.guild else None
    else:
        user_id  = ctx_or_interaction.user.id
        guild_id = getattr(ctx_or_interaction, "guild_id", None)

    # Owner bypass — always first
    if user_id == OWNER_ID:
        return True
    # Server premium check
    if guild_id and is_premium(guild_id):
        return True
    return False

def trial_used(guild_id: int) -> bool:
    return data["premium"].get(str(guild_id), {}).get("trial_used", False)

def activate_premium(guild_id: int, activated_by: int, days, plan: str):
    gid     = str(guild_id)
    expires = int(time.time() + days * 86400) if days else None
    existing = data["premium"].get(gid, {})
    data["premium"][gid] = {
        "active":       True,
        "plan":         plan,
        "expires":      expires,
        "activated_by": activated_by,
        "trial_used":   existing.get("trial_used", False) or (plan == "trial"),
    }
    save_data()

def revoke_premium(guild_id: int):
    gid = str(guild_id)
    if gid in data["premium"]:
        data["premium"][gid]["active"] = False
        save_data()

def premium_embed(title: str, description: str = "") -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=PREMIUM_COLOR)
    e.set_footer(text="Numexa Premium ⭐ • Made with 💜 by Aditya")
    return e

PREMIUM_UPSELL = (
    "⭐ **This is a Premium feature!**\n\n"
    f"Start a free **{TRIAL_DAYS}-day trial** with `!trial`\n"
    f"Or get Premium by opening a ticket in [The Devzone]({DEVZONE_INVITE})"
)


# ──────────────────────────── SAFE EVAL ───────────────────────────
def safe_eval(expr: str, user_id: int = None) -> str:
    expr = (expr
            .replace("^",  "**").replace("π", "pi")
            .replace("×",  "*") .replace("÷", "/")
            .replace("–",  "-") .strip())
    mode = angle_mode.get(user_id, "rad")

    def _sin(v):  return math.sin(math.radians(v))  if mode == "deg" else math.sin(v)
    def _cos(v):  return math.cos(math.radians(v))  if mode == "deg" else math.cos(v)
    def _tan(v):  return math.tan(math.radians(v))  if mode == "deg" else math.tan(v)
    def _asin(v): return math.degrees(math.asin(v)) if mode == "deg" else math.asin(v)
    def _acos(v): return math.degrees(math.acos(v)) if mode == "deg" else math.acos(v)
    def _atan(v): return math.degrees(math.atan(v)) if mode == "deg" else math.atan(v)

    names = {
        "sin": _sin, "cos": _cos, "tan": _tan,
        "asin": _asin, "acos": _acos, "atan": _atan,
        "log": math.log10, "ln": math.log,
        "sqrt": math.sqrt, "abs": abs,
        "floor": math.floor, "ceil": math.ceil, "round": round,
        "pi": math.pi, "e": math.e, "inf": math.inf,
    }
    try:
        result = simple_eval(expr, names=names)
    except ZeroDivisionError:
        raise ValueError("Division by zero.")
    except OverflowError:
        raise ValueError("Result too large to compute.")

    if isinstance(result, float) and result.is_integer():
        return str(int(result))
    return str(result)


def record_history(guild_id: int, user_id: int, expr: str, result: str):
    gid = str(guild_id)
    data["history"].setdefault(gid, [])
    data["history"][gid].append({
        "user": user_id, "expr": expr,
        "result": result, "ts": int(time.time())
    })
    data["history"][gid] = data["history"][gid][-10:]
    save_data()


# ─────────────────────────── HELPERS ──────────────────────────────
def is_owner(user_id: int) -> bool:
    return user_id in ALL_OWNERS

def numexa_embed(title: str, description: str = "") -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=BOT_COLOR)
    e.set_footer(text="Numexa • Scientific Discord Bot")
    return e

def uptime_str() -> str:
    secs   = int(time.time() - START_TIME)
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    return f"{h}h {m}m {s}s"


# ─────────────────────── HELP MENU SYSTEM ─────────────────────────

def _help_overview() -> discord.Embed:
    e = numexa_embed(
        "📘 Numexa — Help Menu",
        "Your scientific Discord calculator.\n"
        "Pick a category below to explore commands.\n"
        "Supports both `!` prefix and `/` slash commands."
    )
    e.add_field(name="🧮 Calculator", value="Math & expressions",      inline=True)
    e.add_field(name="📐 Calculus",   value="Diff, integrate & more",  inline=True)
    e.add_field(name="⚙️ Settings",   value="Prefix & angle mode",     inline=True)
    e.add_field(name="🔢 Counting",   value="Server counting game",    inline=True)
    e.add_field(name="🛠️ Utility",    value="Stats, info & ping",      inline=True)
    e.add_field(name="🔗 Links",      value="Invite, support & more",  inline=True)
    e.add_field(name="⭐ Premium",    value="Exclusive features",      inline=True)
    e.set_thumbnail(url="https://numexa.netlify.app/favicon.ico")
    return e

def _help_calculator() -> discord.Embed:
    e = numexa_embed("🧮 Calculator Commands", "Evaluate mathematical expressions.")
    e.add_field(name="`calc <expr>`", value="Evaluate an expression.\n```\n!calc sqrt(2)*pi```", inline=False)
    e.add_field(name="`ui`",          value="Interactive button calculator.\n```\n!ui```",        inline=False)
    return e

def _help_calculus() -> discord.Embed:
    e = numexa_embed("📐 Calculus Commands", "Powered by SymPy — all w.r.t. `x`.")
    e.add_field(name="`diff <expr>`",      value="Differentiate.\n```\n!diff x**3 + 2*x```",         inline=False)
    e.add_field(name="`integrate <expr>`", value="Integrate.\n```\n!integrate x**2```",               inline=False)
    e.add_field(name="`dsolve <eq>`",      value="Solve a differential equation.",                     inline=False)
    return e

def _help_settings() -> discord.Embed:
    e = numexa_embed("⚙️ Settings Commands")
    e.add_field(name="`setprefix <p>`  *(Admin)*",   value="Change server prefix.",          inline=False)
    e.add_field(name="`anglemode <deg|rad>`",         value="Set your trig angle unit.",      inline=False)
    e.add_field(name="`noprefix <@user>`  *(Owner)*", value="Toggle no-prefix for a user.",  inline=False)
    return e

def _help_counting() -> discord.Embed:
    e = numexa_embed("🔢 Counting Game")
    e.add_field(name="`setcount`  *(Admin)*",   value="Set counting channel.",    inline=False)
    e.add_field(name="`resetcount`  *(Admin)*", value="Reset count to 0.",        inline=False)
    e.add_field(name="📋 Rules",
                value="> Count from **1**, no two in a row, wrong number resets.", inline=False)
    e.add_field(name="⭐ `setmilestone`  *(Premium)*",
                value="Award a role at a count milestone.", inline=False)
    return e

def _help_utility() -> discord.Embed:
    e = numexa_embed("🛠️ Utility Commands")
    e.add_field(name="`ping`",             value="WebSocket latency.",  inline=True)
    e.add_field(name="`stats`",            value="Bot statistics.",     inline=True)
    e.add_field(name="`serverinfo`",       value="Server information.", inline=True)
    e.add_field(name="`userinfo [@user]`", value="User information.",   inline=True)
    return e

def _help_links() -> discord.Embed:
    e = numexa_embed("🔗 Links & Resources")
    e.add_field(name="👋 `invite`",    value=f"[Add Numexa]({INVITE_URL})",           inline=False)
    e.add_field(name="💬 `support`",   value=f"[Join The Devzone]({DEVZONE_INVITE})", inline=False)
    e.add_field(name="🧠 `dashboard`", value=f"[Web Dashboard]({DASHBOARD_URL})",     inline=False)
    return e

def _help_premium() -> discord.Embed:
    e = discord.Embed(
        title="⭐ Numexa Premium",
        description=(
            "Unlock powerful features for your server!\n\n"
            f"**Free Trial:** `!trial` — {TRIAL_DAYS} days, one-time per server\n"
            f"**Buy Premium:** Open a ticket in [The Devzone]({DEVZONE_INVITE})\n"
            "**Check Status:** `!premium`"
        ),
        color=PREMIUM_COLOR
    )
    e.add_field(name="📊 `plot <expr>`",        value="Graph any function",             inline=True)
    e.add_field(name="📝 `history`",            value="Last 10 calculations",           inline=True)
    e.add_field(name="🧮 `matrix <op>`",        value="Matrix operations",             inline=True)
    e.add_field(name="📐 `stepdiff / stepint`", value="Step-by-step calculus",         inline=True)
    e.add_field(name="🔢 `setmilestone`",       value="Count milestone role rewards",  inline=True)
    e.add_field(name="🔔 `setdaily`",           value="Daily math problem in channel", inline=True)
    e.add_field(name="📌 `bookmark`",           value="Save & recall expressions",     inline=True)
    e.add_field(name="🎨 `botnick`",            value="Custom bot nickname",           inline=True)
    e.set_footer(text="Numexa Premium ⭐ • Made with 💜 by Aditya")
    return e


HELP_PAGES = {
    "overview":   ("📘 Overview",   _help_overview),
    "calculator": ("🧮 Calculator", _help_calculator),
    "calculus":   ("📐 Calculus",   _help_calculus),
    "settings":   ("⚙️ Settings",   _help_settings),
    "counting":   ("🔢 Counting",   _help_counting),
    "utility":    ("🛠️ Utility",    _help_utility),
    "links":      ("🔗 Links",      _help_links),
    "premium":    ("⭐ Premium",    _help_premium),
}


class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=label, value=key,
                emoji=label.split()[0],
                description=self._desc(key),
                default=(key == "overview")
            )
            for key, (label, _) in HELP_PAGES.items()
        ]
        super().__init__(placeholder="📂 Select a category…", min_values=1, max_values=1, options=options)

    @staticmethod
    def _desc(key: str) -> str:
        return {
            "overview":   "All categories at a glance",
            "calculator": "calc, ui",
            "calculus":   "diff, integrate, dsolve",
            "settings":   "setprefix, anglemode, noprefix",
            "counting":   "setcount, resetcount, milestone",
            "utility":    "ping, stats, serverinfo, userinfo",
            "links":      "invite, support, dashboard",
            "premium":    "All ⭐ premium features",
        }.get(key, "")

    async def callback(self, interaction: discord.Interaction):
        for opt in self.options:
            opt.default = (opt.value == self.values[0])
        _, builder = HELP_PAGES[self.values[0]]
        await interaction.response.edit_message(embed=builder(), view=self.view)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(HelpSelect())
        self.message = None

    @discord.ui.button(label="🏠 Home", style=discord.ButtonStyle.secondary, row=1)
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            if isinstance(item, HelpSelect):
                for opt in item.options:
                    opt.default = (opt.value == "overview")
        await interaction.response.edit_message(embed=_help_overview(), view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass


# ───────────────────────── CALCULATOR UI ──────────────────────────
class CalculatorView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.expression = ""
        self.user_id    = user_id
        self.message    = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            if self.message:
                await self.message.edit(content="*Calculator timed out.*", view=self)
        except Exception:
            pass

    async def update(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=f"```\n{self.expression or '0'}\n```", view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                err("This calculator belongs to someone else. Use `!ui` to open your own."),
                ephemeral=True)
            return False
        return True

    @discord.ui.button(label="7", style=discord.ButtonStyle.secondary, row=0)
    async def b7(self, i, b): self.expression += "7"; await self.update(i)
    @discord.ui.button(label="8", style=discord.ButtonStyle.secondary, row=0)
    async def b8(self, i, b): self.expression += "8"; await self.update(i)
    @discord.ui.button(label="9", style=discord.ButtonStyle.secondary, row=0)
    async def b9(self, i, b): self.expression += "9"; await self.update(i)
    @discord.ui.button(label="÷", style=discord.ButtonStyle.primary, row=0)
    async def bdiv(self, i, b): self.expression += "/"; await self.update(i)
    @discord.ui.button(label="⌫", style=discord.ButtonStyle.danger, row=0)
    async def bback(self, i, b): self.expression = self.expression[:-1]; await self.update(i)

    @discord.ui.button(label="4", style=discord.ButtonStyle.secondary, row=1)
    async def b4(self, i, b): self.expression += "4"; await self.update(i)
    @discord.ui.button(label="5", style=discord.ButtonStyle.secondary, row=1)
    async def b5(self, i, b): self.expression += "5"; await self.update(i)
    @discord.ui.button(label="6", style=discord.ButtonStyle.secondary, row=1)
    async def b6(self, i, b): self.expression += "6"; await self.update(i)
    @discord.ui.button(label="×", style=discord.ButtonStyle.primary, row=1)
    async def bmul(self, i, b): self.expression += "*"; await self.update(i)
    @discord.ui.button(label="( )", style=discord.ButtonStyle.secondary, row=1)
    async def bparen(self, i, b):
        self.expression += "(" if self.expression.count("(") == self.expression.count(")") else ")"
        await self.update(i)

    @discord.ui.button(label="1", style=discord.ButtonStyle.secondary, row=2)
    async def b1(self, i, b): self.expression += "1"; await self.update(i)
    @discord.ui.button(label="2", style=discord.ButtonStyle.secondary, row=2)
    async def b2(self, i, b): self.expression += "2"; await self.update(i)
    @discord.ui.button(label="3", style=discord.ButtonStyle.secondary, row=2)
    async def b3(self, i, b): self.expression += "3"; await self.update(i)
    @discord.ui.button(label="−", style=discord.ButtonStyle.primary, row=2)
    async def bsub(self, i, b): self.expression += "-"; await self.update(i)
    @discord.ui.button(label="^", style=discord.ButtonStyle.secondary, row=2)
    async def bpow(self, i, b): self.expression += "**"; await self.update(i)

    @discord.ui.button(label="0", style=discord.ButtonStyle.secondary, row=3)
    async def b0(self, i, b): self.expression += "0"; await self.update(i)
    @discord.ui.button(label=".", style=discord.ButtonStyle.secondary, row=3)
    async def bdot(self, i, b): self.expression += "."; await self.update(i)
    @discord.ui.button(label="C", style=discord.ButtonStyle.danger, row=3)
    async def bclear(self, i, b): self.expression = ""; await self.update(i)
    @discord.ui.button(label="+", style=discord.ButtonStyle.primary, row=3)
    async def badd(self, i, b): self.expression += "+"; await self.update(i)
    @discord.ui.button(label="=", style=discord.ButtonStyle.success, row=3)
    async def bequals(self, i, b):
        try:
            self.expression = safe_eval(self.expression, self.user_id)
        except Exception as e:
            self.expression = f"Error: {e}"
        await self.update(i)

    @discord.ui.button(label="sin", style=discord.ButtonStyle.secondary, row=4)
    async def bsin(self, i, b): self.expression += "sin("; await self.update(i)
    @discord.ui.button(label="cos", style=discord.ButtonStyle.secondary, row=4)
    async def bcos(self, i, b): self.expression += "cos("; await self.update(i)
    @discord.ui.button(label="tan", style=discord.ButtonStyle.secondary, row=4)
    async def btan(self, i, b): self.expression += "tan("; await self.update(i)
    @discord.ui.button(label="√", style=discord.ButtonStyle.secondary, row=4)
    async def bsqrt(self, i, b): self.expression += "sqrt("; await self.update(i)
    @discord.ui.button(label="log", style=discord.ButtonStyle.secondary, row=4)
    async def blog(self, i, b): self.expression += "log("; await self.update(i)


# ═══════════════════════ PREFIX COMMANDS ══════════════════════════

# ── Math ──────────────────────────────────────────────────────────
@bot.command(name="calc")
async def cmd_calc(ctx, *, expr: str):
    try:
        result = safe_eval(expr, ctx.author.id)
        if ctx.guild and is_premium(ctx.guild.id):
            record_history(ctx.guild.id, ctx.author.id, expr, result)
        e = numexa_embed("🧮 Result")
        e.add_field(name="Expression", value=f"`{expr}`",     inline=False)
        e.add_field(name="Result",     value=f"**{result}**", inline=False)
        await ctx.send(embed=e)
    except Exception as ex:
        await ctx.send(err(f"**Error:** `{ex}`"))

@bot.command(name="diff")
async def cmd_diff(ctx, *, expr: str):
    try:
        result = sp.diff(sp.sympify(expr), x)
        e = numexa_embed("📐 Derivative")
        e.add_field(name="f(x)",  value=f"`{expr}`",   inline=False)
        e.add_field(name="f′(x)", value=f"`{result}`", inline=False)
        await ctx.send(embed=e)
    except Exception as ex:
        await ctx.send(err(f"**Error:** `{ex}`"))

@bot.command(name="integrate")
async def cmd_integrate(ctx, *, expr: str):
    try:
        result = sp.integrate(sp.sympify(expr), x)
        e = numexa_embed("∫ Integral")
        e.add_field(name="f(x)",    value=f"`{expr}`",       inline=False)
        e.add_field(name="∫f(x)dx", value=f"`{result} + C`", inline=False)
        await ctx.send(embed=e)
    except Exception as ex:
        await ctx.send(err(f"**Error:** `{ex}`"))

@bot.command(name="dsolve")
async def cmd_dsolve(ctx, *, eq: str):
    try:
        result = sp.dsolve(sp.sympify(eq))
        e = numexa_embed("🔬 Differential Equation Solution")
        e.add_field(name="Equation", value=f"`{eq}`",     inline=False)
        e.add_field(name="Solution", value=f"`{result}`", inline=False)
        await ctx.send(embed=e)
    except Exception as ex:
        await ctx.send(err(f"**Error:** `{ex}`"))

@bot.command(name="ui")
async def cmd_ui(ctx):
    mode = angle_mode.get(ctx.author.id, "rad").upper()
    view = CalculatorView(ctx.author.id)
    msg  = await ctx.send(f"```\n0\n```\n*Angle mode: **{mode}***", view=view)
    view.message = msg


# ── Settings ──────────────────────────────────────────────────────
@bot.command(name="setprefix")
@commands.has_permissions(administrator=True)
async def cmd_setprefix(ctx, prefix: str):
    if len(prefix) > 5:
        return await ctx.send(err("Prefix must be 5 characters or fewer."))
    custom_prefixes[ctx.guild.id]       = prefix
    data["prefixes"][str(ctx.guild.id)] = prefix
    save_data()
    await ctx.send(ok(f"Prefix set to `{prefix}`"))

@bot.command(name="anglemode")
async def cmd_anglemode(ctx, mode: str):
    mode = mode.lower()
    if mode not in ("deg", "rad"):
        return await ctx.send(err("Use `deg` or `rad`."))
    angle_mode[ctx.author.id]         = mode
    data["angle"][str(ctx.author.id)] = mode
    save_data()
    label = "Degrees 🔺" if mode == "deg" else "Radians 〰️"
    await ctx.send(ok(f"Angle mode set to **{label}**"))

@bot.command(name="noprefix")
async def cmd_noprefix(ctx, member: discord.Member):
    if not is_owner(ctx.author.id):
        return await ctx.send(err("Only the bot owner can use this command."))
    if member.id in no_prefix_users:
        no_prefix_users.discard(member.id)
        msg = ok(f"Removed no-prefix from {member.mention}.")
    else:
        no_prefix_users.add(member.id)
        msg = ok(f"{member.mention} can now use commands without a prefix.")
    data["noprefix"] = list(no_prefix_users)
    save_data()
    await ctx.send(msg)


# ── Counting ──────────────────────────────────────────────────────
@bot.command(name="setcount")
@commands.has_permissions(administrator=True)
async def cmd_setcount(ctx):
    gid = str(ctx.guild.id)
    data["counting"][gid] = {
        "channel": ctx.channel.id, "current": 0,
        "last_user": None, "milestones": {}
    }
    save_data()
    await ctx.send(ok(f"Counting channel set to {ctx.channel.mention}. Start counting from **1**!"))

@bot.command(name="resetcount")
@commands.has_permissions(administrator=True)
async def cmd_resetcount(ctx):
    gid = str(ctx.guild.id)
    if gid in data["counting"]:
        data["counting"][gid]["current"]   = 0
        data["counting"][gid]["last_user"] = None
        save_data()
        await ctx.send("🔄 Count reset to **0**. Start again from **1**!")
    else:
        await ctx.send(err("No counting channel set for this server."))


# ── Utility ───────────────────────────────────────────────────────
@bot.command(name="ping")
async def cmd_ping(ctx):
    e = numexa_embed("🏓 Pong!")
    e.add_field(name="WebSocket Latency", value=f"`{round(bot.latency * 1000)}ms`")
    await ctx.send(embed=e)

@bot.command(name="stats")
async def cmd_stats(ctx):
    e = numexa_embed("📊 Numexa Stats")
    e.add_field(name="Servers",  value=f"`{len(bot.guilds)}`",                inline=True)
    e.add_field(name="Users",    value=f"`{len(set(bot.get_all_members()))}`", inline=True)
    e.add_field(name="Latency",  value=f"`{round(bot.latency * 1000)}ms`",    inline=True)
    e.add_field(name="Uptime",   value=f"`{uptime_str()}`",                   inline=True)
    e.add_field(name="Library",  value=f"`discord.py {discord.__version__}`", inline=True)
    await ctx.send(embed=e)

@bot.command(name="serverinfo")
async def cmd_serverinfo(ctx):
    if not ctx.guild:
        return await ctx.send(err("Server-only command."))
    g = ctx.guild
    e = numexa_embed(f"🏠 {g.name}")
    e.set_thumbnail(url=g.icon.url if g.icon else None)
    e.add_field(name="Owner",    value=g.owner.mention if g.owner else "Unknown", inline=True)
    e.add_field(name="Members",  value=f"`{g.member_count}`",                     inline=True)
    e.add_field(name="Channels", value=f"`{len(g.channels)}`",                    inline=True)
    e.add_field(name="Roles",    value=f"`{len(g.roles)}`",                       inline=True)
    e.add_field(name="Created",  value=f"<t:{int(g.created_at.timestamp())}:R>",  inline=True)
    await ctx.send(embed=e)

@bot.command(name="userinfo")
async def cmd_userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = numexa_embed(f"👤 {member}")
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="ID",       value=f"`{member.id}`",                             inline=True)
    e.add_field(name="Nickname", value=member.display_name,                           inline=True)
    e.add_field(name="Bot",      value="Yes" if member.bot else "No",                 inline=True)
    joined = f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown"
    e.add_field(name="Joined",   value=joined,                                        inline=True)
    e.add_field(name="Created",  value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    e.add_field(name="Top Role", value=member.top_role.mention,                       inline=True)
    await ctx.send(embed=e)


# ── Links ─────────────────────────────────────────────────────────
@bot.command(name="help")
async def cmd_help(ctx):
    view = HelpView()
    msg  = await ctx.send(embed=_help_overview(), view=view)
    view.message = msg

@bot.command(name="support")
async def cmd_support(ctx):
    e = numexa_embed("💬 Support Server", "Join **The Devzone** for help, updates & announcements.")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Join Devzone", style=discord.ButtonStyle.link, url=DEVZONE_INVITE))
    await ctx.send(embed=e, view=v)

@bot.command(name="dashboard")
async def cmd_dashboard(ctx):
    e = numexa_embed("🧠 Numexa Dashboard", "Manage settings, view stats, and configure Numexa.")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Open Dashboard", style=discord.ButtonStyle.link, url=DASHBOARD_URL))
    await ctx.send(embed=e, view=v)

@bot.command(name="invite")
async def cmd_invite(ctx):
    e = numexa_embed("👋 Invite Numexa", "Click below to add me to your server!")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Add Numexa", style=discord.ButtonStyle.link, url=INVITE_URL))
    await ctx.send(embed=e, view=v)


# ═══════════════════ PREMIUM USER COMMANDS ════════════════════════

@bot.command(name="trial")
async def cmd_trial(ctx):
    if not ctx.guild:
        return await ctx.send(err("Server-only command."))
    if ctx.author.id != ctx.guild.owner_id and not is_owner(ctx.author.id):
        return await ctx.send(err("Only the **server owner** can activate the trial."))
    if is_premium(ctx.guild.id):
        rec = get_premium(ctx.guild.id)
        exp = f"<t:{rec['expires']}:R>" if rec.get("expires") else "never"
        return await ctx.send(err(f"This server already has Premium active (expires {exp})."))
    if trial_used(ctx.guild.id):
        e = discord.Embed(
            title="⭐ Trial Already Used",
            description=(
                "This server has already used its free trial.\n\n"
                f"To get Premium, open a ticket in [The Devzone]({DEVZONE_INVITE}) after payment."
            ),
            color=PREMIUM_COLOR
        )
        v = discord.ui.View()
        v.add_item(discord.ui.Button(label="Open Ticket", style=discord.ButtonStyle.link, url=DEVZONE_INVITE))
        return await ctx.send(embed=e, view=v)

    activate_premium(ctx.guild.id, ctx.author.id, TRIAL_DAYS, "trial")
    expires_ts = int(time.time() + TRIAL_DAYS * 86400)
    e = discord.Embed(
        title="🎉 Premium Trial Activated!",
        description=(
            f"**{ctx.guild.name}** now has **Numexa Premium** for **{TRIAL_DAYS} days**!\n\n"
            f"Trial expires: <t:{expires_ts}:R>\n\n"
            "Use `!help` → ⭐ Premium to explore all features."
        ),
        color=PREMIUM_COLOR
    )
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="View Premium Features", style=discord.ButtonStyle.link, url=DEVZONE_INVITE))
    await ctx.send(embed=e, view=v)

@bot.command(name="premium")
async def cmd_premium(ctx):
    if not ctx.guild:
        return await ctx.send(err("Server-only command."))
    rec = get_premium(ctx.guild.id)
    if rec:
        plan    = rec["plan"].capitalize()
        expires = f"<t:{rec['expires']}:R>" if rec.get("expires") else "**Lifetime**"
        e = discord.Embed(
            title="⭐ Premium Active",
            description=f"**{ctx.guild.name}** has an active **{plan}** subscription.",
            color=PREMIUM_COLOR
        )
        e.add_field(name="Plan",    value=plan,    inline=True)
        e.add_field(name="Expires", value=expires, inline=True)
        await ctx.send(embed=e)
    else:
        used = trial_used(ctx.guild.id)
        e = discord.Embed(
            title="💤 No Premium",
            description=(
                f"Trial expired. [Open a ticket]({DEVZONE_INVITE}) to buy Premium." if used
                else f"No Premium active. Start your free **{TRIAL_DAYS}-day trial** with `!trial`!"
            ),
            color=BOT_COLOR
        )
        v = discord.ui.View()
        v.add_item(discord.ui.Button(label="Buy Premium", style=discord.ButtonStyle.link, url=DEVZONE_INVITE))
        await ctx.send(embed=e, view=v)


# ══════════════ OWNER-ONLY PREMIUM MANAGEMENT ═════════════════════

@bot.command(name="grantpremium")
async def cmd_grantpremium(ctx, guild_id: int, days: int = None):
    if not is_owner(ctx.author.id):
        return await ctx.send(err("Owner only."))
    activate_premium(guild_id, ctx.author.id, days, "paid")
    exp = f"{days} days" if days else "lifetime"
    await ctx.send(ok(f"Premium granted to guild `{guild_id}` for **{exp}**."))
    guild = bot.get_guild(guild_id)
    if guild and guild.owner:
        try:
            e = discord.Embed(
                title="⭐ Numexa Premium Activated!",
                description=(
                    f"**{guild.name}** now has **Numexa Premium**!\n\n"
                    f"{'Expires in **' + str(days) + ' days**' if days else '**Lifetime** access'}.\n\n"
                    "Use `!help` → ⭐ Premium to explore all features."
                ),
                color=PREMIUM_COLOR
            )
            await guild.owner.send(embed=e)
        except discord.Forbidden:
            pass

@bot.command(name="revokepremium")
async def cmd_revokepremium(ctx, guild_id: int):
    if not is_owner(ctx.author.id):
        return await ctx.send(err("Owner only."))
    revoke_premium(guild_id)
    await ctx.send(ok(f"Premium revoked from guild `{guild_id}`."))

@bot.command(name="premiumlist")
async def cmd_premiumlist(ctx):
    if not is_owner(ctx.author.id):
        return await ctx.send(err("Owner only."))
    active = [
        (gid, rec) for gid, rec in data["premium"].items()
        if rec.get("active") and (not rec.get("expires") or time.time() < rec["expires"])
    ]
    if not active:
        return await ctx.send("No active premium servers.")
    e = numexa_embed("⭐ Premium Servers", f"{len(active)} active")
    for gid, rec in active[:10]:
        guild = bot.get_guild(int(gid))
        name  = guild.name if guild else f"ID: {gid}"
        exp   = f"<t:{rec['expires']}:R>" if rec.get("expires") else "Lifetime"
        e.add_field(name=name, value=f"Plan: `{rec['plan']}` • Expires: {exp}", inline=False)
    await ctx.send(embed=e)


# ══════════════════════ PREMIUM FEATURES ══════════════════════════

# ── 1. Graph Plotting ─────────────────────────────────────────────
@bot.command(name="plot")
async def cmd_plot(ctx, *, expr: str):
    if not has_premium_access(ctx):
        return await ctx.send(embed=discord.Embed(description=PREMIUM_UPSELL, color=PREMIUM_COLOR))
    try:
        x_vals = np.linspace(-10, 10, 800)
        safe_names = {
            "x": x_vals, "pi": np.pi, "e": np.e,
            "sin": np.sin, "cos": np.cos, "tan": np.tan,
            "sqrt": np.sqrt, "abs": np.abs, "log": np.log10,
            "ln": np.log, "exp": np.exp,
        }
        clean  = expr.replace("^", "**").replace("π", "pi")
        y_vals = eval(clean, {"__builtins__": {}}, safe_names)

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(x_vals, y_vals, color="#8A2BE2", linewidth=2)
        ax.axhline(0, color="white", linewidth=0.5)
        ax.axvline(0, color="white", linewidth=0.5)
        ax.set_facecolor("#2b2d31")
        fig.patch.set_facecolor("#2b2d31")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("#555")
        ax.set_title(f"f(x) = {expr}", color="white", fontsize=13)
        ax.set_xlabel("x", color="white")
        ax.set_ylabel("f(x)", color="white")
        ax.set_ylim(-50, 50)
        ax.grid(True, color="#444", linestyle="--", linewidth=0.5)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=120)
        buf.seek(0)
        plt.close(fig)

        e    = premium_embed("📊 Graph", f"f(x) = `{expr}`")
        file = discord.File(buf, filename="plot.png")
        e.set_image(url="attachment://plot.png")
        await ctx.send(embed=e, file=file)
    except Exception as ex:
        await ctx.send(err(f"Could not plot: `{ex}`"))


# ── 2. Calculation History ────────────────────────────────────────
@bot.command(name="history")
async def cmd_history(ctx):
    if not has_premium_access(ctx):
        return await ctx.send(embed=discord.Embed(description=PREMIUM_UPSELL, color=PREMIUM_COLOR))
    hist = data["history"].get(str(ctx.guild.id), [])
    if not hist:
        return await ctx.send(err("No calculation history yet. Use `!calc` to start building it."))
    e = premium_embed("📝 Calculation History", f"Last {len(hist)} calculations in this server")
    for i, entry in enumerate(reversed(hist), 1):
        user = ctx.guild.get_member(entry["user"])
        name = user.display_name if user else "Unknown"
        e.add_field(
            name=f"{i}. `{entry['expr']}`",
            value=f"= **{entry['result']}** — {name} <t:{entry['ts']}:R>",
            inline=False
        )
    await ctx.send(embed=e)


# ── 3. Matrix Operations ──────────────────────────────────────────
@bot.command(name="matrix")
async def cmd_matrix(ctx, operation: str, *, data_str: str):
    """
    !matrix det 1,2|3,4
    !matrix inv 1,2|3,4
    !matrix trans 1,2|3,4
    !matrix add 1,2|3,4 + 5,6|7,8
    !matrix mul 1,2|3,4 * 5,6|7,8
    """
    if not has_premium_access(ctx):
        return await ctx.send(embed=discord.Embed(description=PREMIUM_UPSELL, color=PREMIUM_COLOR))

    def parse_matrix(s: str):
        return sp.Matrix([[sp.sympify(v.strip()) for v in row.split(",")]
                          for row in s.strip().split("|")])
    try:
        op = operation.lower()
        if op == "add":
            parts = data_str.split("+")
            if len(parts) != 2:
                return await ctx.send(err("For `add`, separate two matrices with `+`."))
            result, label = parse_matrix(parts[0]) + parse_matrix(parts[1]), "A + B"
        elif op == "mul":
            parts = data_str.split("*")
            if len(parts) != 2:
                return await ctx.send(err("For `mul`, separate two matrices with `*`."))
            result, label = parse_matrix(parts[0]) * parse_matrix(parts[1]), "A × B"
        elif op == "det":
            result, label = parse_matrix(data_str).det(), "det(A)"
        elif op == "inv":
            result, label = parse_matrix(data_str).inv(), "A⁻¹"
        elif op == "trans":
            result, label = parse_matrix(data_str).T, "Aᵀ"
        else:
            return await ctx.send(err("Unknown operation. Use: `det`, `inv`, `add`, `mul`, `trans`"))

        e = premium_embed(f"🧮 Matrix — {label}")
        e.add_field(name="Result", value=f"```\n{result}\n```", inline=False)
        await ctx.send(embed=e)
    except Exception as ex:
        await ctx.send(err(f"Matrix error: `{ex}`\nFormat: rows with `|`, values with `,` — e.g. `1,2|3,4`"))


# ── 4. Step-by-step Differentiation ──────────────────────────────
@bot.command(name="stepdiff")
async def cmd_stepdiff(ctx, *, expr: str):
    if not has_premium_access(ctx):
        return await ctx.send(embed=discord.Embed(description=PREMIUM_UPSELL, color=PREMIUM_COLOR))
    try:
        sym_expr = sp.sympify(expr)
        terms    = sp.Add.make_args(sym_expr)
        steps    = [f"d/dx [{t}] = **{sp.diff(t, x)}**" for t in terms]
        final    = sp.diff(sym_expr, x)
        e = premium_embed("📐 Step-by-step Derivative", f"f(x) = `{expr}`")
        e.add_field(name="Steps",       value="\n".join(steps) or "Single term", inline=False)
        e.add_field(name="Final f′(x)", value=f"`{final}`",                      inline=False)
        await ctx.send(embed=e)
    except Exception as ex:
        await ctx.send(err(f"**Error:** `{ex}`"))


# ── 5. Step-by-step Integration ───────────────────────────────────
@bot.command(name="stepint")
async def cmd_stepint(ctx, *, expr: str):
    if not has_premium_access(ctx):
        return await ctx.send(embed=discord.Embed(description=PREMIUM_UPSELL, color=PREMIUM_COLOR))
    try:
        sym_expr = sp.sympify(expr)
        terms    = sp.Add.make_args(sym_expr)
        steps    = [f"∫ {t} dx = **{sp.integrate(t, x)}**" for t in terms]
        final    = sp.integrate(sym_expr, x)
        e = premium_embed("∫ Step-by-step Integral", f"f(x) = `{expr}`")
        e.add_field(name="Steps",         value="\n".join(steps) or "Single term", inline=False)
        e.add_field(name="Final ∫f(x)dx", value=f"`{final} + C`",                  inline=False)
        await ctx.send(embed=e)
    except Exception as ex:
        await ctx.send(err(f"**Error:** `{ex}`"))


# ── 6. Counting Milestone Rewards ────────────────────────────────
@bot.command(name="setmilestone")
@commands.has_permissions(administrator=True)
async def cmd_setmilestone(ctx, count: int, role: discord.Role):
    if not has_premium_access(ctx):
        return await ctx.send(embed=discord.Embed(description=PREMIUM_UPSELL, color=PREMIUM_COLOR))
    gid = str(ctx.guild.id)
    if gid not in data["counting"]:
        return await ctx.send(err("Set up a counting channel first with `!setcount`."))
    data["counting"][gid].setdefault("milestones", {})
    data["counting"][gid]["milestones"][str(count)] = role.id
    save_data()
    await ctx.send(ok(f"At count **{count}**, {role.mention} will be awarded to the counter!"))

@bot.command(name="milestones")
async def cmd_milestones(ctx):
    if not ctx.guild:
        return await ctx.send(err("Server-only command."))
    gid = str(ctx.guild.id)
    ms  = data["counting"].get(gid, {}).get("milestones", {})
    if not ms:
        return await ctx.send("No milestones set. Use `!setmilestone <count> <@role>` (Premium).")
    e = numexa_embed("🔢 Counting Milestones")
    for count, role_id in sorted(ms.items(), key=lambda i: int(i[0])):
        role = ctx.guild.get_role(role_id)
        e.add_field(name=f"Count {count}", value=role.mention if role else "Role deleted", inline=True)
    await ctx.send(embed=e)


# ── 7. Daily Math Problem ─────────────────────────────────────────
@bot.command(name="setdaily")
@commands.has_permissions(administrator=True)
async def cmd_setdaily(ctx):
    if not has_premium_access(ctx):
        return await ctx.send(embed=discord.Embed(description=PREMIUM_UPSELL, color=PREMIUM_COLOR))
    data["daily"][str(ctx.guild.id)] = {"channel": ctx.channel.id, "last_sent": ""}
    save_data()
    await ctx.send(ok(f"Daily math problem will be posted in {ctx.channel.mention} every day at midnight UTC!"))

@bot.command(name="stopdaily")
@commands.has_permissions(administrator=True)
async def cmd_stopdaily(ctx):
    if not ctx.guild:
        return
    data["daily"].pop(str(ctx.guild.id), None)
    save_data()
    await ctx.send(ok("Daily math problem stopped."))


# ── 8. Expression Bookmarks ───────────────────────────────────────
@bot.command(name="bookmark")
async def cmd_bookmark(ctx, action: str, name: str = None, *, expr: str = None):
    """
    !bookmark save <name> <expr>
    !bookmark list
    !bookmark use <name>
    !bookmark delete <name>
    """
    if not has_premium_access(ctx):
        return await ctx.send(embed=discord.Embed(description=PREMIUM_UPSELL, color=PREMIUM_COLOR))

    uid = str(ctx.author.id)
    data["bookmarks"].setdefault(uid, {})
    bm  = data["bookmarks"][uid]
    act = action.lower()

    if act == "save":
        if not name or not expr:
            return await ctx.send(err("Usage: `!bookmark save <name> <expression>`"))
        bm[name] = expr
        save_data()
        await ctx.send(ok(f"Bookmark **{name}** saved: `{expr}`"))

    elif act == "list":
        if not bm:
            return await ctx.send("You have no saved bookmarks.")
        e = premium_embed("📌 Your Bookmarks")
        for n, ex in bm.items():
            e.add_field(name=f"`{n}`", value=f"`{ex}`", inline=False)
        await ctx.send(embed=e)

    elif act == "use":
        if not name or name not in bm:
            return await ctx.send(err(f"Bookmark `{name}` not found. Use `!bookmark list`."))
        try:
            result = safe_eval(bm[name], ctx.author.id)
            e = premium_embed(f"📌 Bookmark: {name}")
            e.add_field(name="Expression", value=f"`{bm[name]}`", inline=False)
            e.add_field(name="Result",     value=f"**{result}**", inline=False)
            await ctx.send(embed=e)
        except Exception as ex:
            await ctx.send(err(f"Error evaluating bookmark: `{ex}`"))

    elif act == "delete":
        if not name or name not in bm:
            return await ctx.send(err(f"Bookmark `{name}` not found."))
        del bm[name]
        save_data()
        await ctx.send(ok(f"Bookmark **{name}** deleted."))

    else:
        await ctx.send(err("Unknown action. Use: `save`, `list`, `use`, `delete`"))


# ── 9. Custom Bot Nickname ────────────────────────────────────────
@bot.command(name="botnick")
@commands.has_permissions(administrator=True)
async def cmd_botnick(ctx, *, nick: str = None):
    if not has_premium_access(ctx):
        return await ctx.send(embed=discord.Embed(description=PREMIUM_UPSELL, color=PREMIUM_COLOR))
    try:
        await ctx.guild.me.edit(nick=nick)
        await ctx.send(ok(f"Bot nickname set to **{nick}**." if nick else "Bot nickname reset."))
    except discord.Forbidden:
        await ctx.send(err("I don't have permission to change my nickname."))



@bot.command(name="sync")
async def cmd_sync(ctx):
    """Force re-sync all slash commands (owner only)."""
    if not is_owner(ctx.author.id):
        return await ctx.send(err("Owner only."))
    await ctx.send("⏳ Syncing slash commands...")
    synced = await bot.tree.sync()
    await ctx.send(ok(f"Synced **{len(synced)}** slash commands globally."))

# ═══════════════════════ SLASH COMMANDS ═══════════════════════════

@bot.tree.command(name="calc", description="Evaluate a math expression")
@app_commands.describe(expr="The expression to evaluate")
async def slash_calc(i: discord.Interaction, expr: str):
    try:
        result = safe_eval(expr, i.user.id)
        if i.guild and is_premium(i.guild.id):
            record_history(i.guild.id, i.user.id, expr, result)
        e = numexa_embed("🧮 Result")
        e.add_field(name="Expression", value=f"`{expr}`",     inline=False)
        e.add_field(name="Result",     value=f"**{result}**", inline=False)
        await i.response.send_message(embed=e)
    except Exception as ex:
        await i.response.send_message(err(f"**Error:** `{ex}`"), ephemeral=True)

@bot.tree.command(name="diff", description="Differentiate an expression w.r.t. x")
@app_commands.describe(expr="Expression to differentiate")
async def slash_diff(i: discord.Interaction, expr: str):
    try:
        result = sp.diff(sp.sympify(expr), x)
        e = numexa_embed("📐 Derivative")
        e.add_field(name="f(x)",  value=f"`{expr}`",   inline=False)
        e.add_field(name="f′(x)", value=f"`{result}`", inline=False)
        await i.response.send_message(embed=e)
    except Exception as ex:
        await i.response.send_message(err(f"**Error:** `{ex}`"), ephemeral=True)

@bot.tree.command(name="integrate", description="Integrate an expression w.r.t. x")
@app_commands.describe(expr="Expression to integrate")
async def slash_integrate(i: discord.Interaction, expr: str):
    try:
        result = sp.integrate(sp.sympify(expr), x)
        e = numexa_embed("∫ Integral")
        e.add_field(name="f(x)",    value=f"`{expr}`",       inline=False)
        e.add_field(name="∫f(x)dx", value=f"`{result} + C`", inline=False)
        await i.response.send_message(embed=e)
    except Exception as ex:
        await i.response.send_message(err(f"**Error:** `{ex}`"), ephemeral=True)

@bot.tree.command(name="dsolve", description="Solve a differential equation")
@app_commands.describe(eq="Differential equation")
async def slash_dsolve(i: discord.Interaction, eq: str):
    try:
        result = sp.dsolve(sp.sympify(eq))
        e = numexa_embed("🔬 Differential Equation")
        e.add_field(name="Equation", value=f"`{eq}`",     inline=False)
        e.add_field(name="Solution", value=f"`{result}`", inline=False)
        await i.response.send_message(embed=e)
    except Exception as ex:
        await i.response.send_message(err(f"**Error:** `{ex}`"), ephemeral=True)

@bot.tree.command(name="ui", description="Open the interactive button calculator")
async def slash_ui(i: discord.Interaction):
    mode = angle_mode.get(i.user.id, "rad").upper()
    await i.response.send_message(
        f"```\n0\n```\n*Angle mode: **{mode}***", view=CalculatorView(i.user.id))

@bot.tree.command(name="trial", description="Activate the free 7-day premium trial")
async def slash_trial(i: discord.Interaction):
    if not i.guild:
        return await i.response.send_message(err("Server-only."), ephemeral=True)
    if i.user.id != i.guild.owner_id and not is_owner(i.user.id):
        return await i.response.send_message(err("Only the server owner can activate the trial."), ephemeral=True)
    if is_premium(i.guild.id):
        return await i.response.send_message(err("This server already has Premium."), ephemeral=True)
    if trial_used(i.guild.id):
        return await i.response.send_message(
            embed=discord.Embed(
                description=f"Trial already used. [Open a ticket]({DEVZONE_INVITE}) to buy Premium.",
                color=PREMIUM_COLOR),
            ephemeral=True)
    activate_premium(i.guild.id, i.user.id, TRIAL_DAYS, "trial")
    expires_ts = int(time.time() + TRIAL_DAYS * 86400)
    e = discord.Embed(
        title="🎉 Premium Trial Activated!",
        description=f"**{i.guild.name}** now has Premium for **{TRIAL_DAYS} days**!\nExpires: <t:{expires_ts}:R>",
        color=PREMIUM_COLOR)
    await i.response.send_message(embed=e)

@bot.tree.command(name="premium", description="Check this server's premium status")
async def slash_premium(i: discord.Interaction):
    if not i.guild:
        return await i.response.send_message(err("Server-only."), ephemeral=True)
    rec = get_premium(i.guild.id)
    if rec:
        exp = f"<t:{rec['expires']}:R>" if rec.get("expires") else "Lifetime"
        e   = discord.Embed(title="⭐ Premium Active",
                            description=f"Plan: **{rec['plan'].capitalize()}** • Expires: {exp}",
                            color=PREMIUM_COLOR)
    else:
        used = trial_used(i.guild.id)
        e    = discord.Embed(
            title="💤 No Premium",
            description=(f"Trial expired. [Buy Premium]({DEVZONE_INVITE})" if used
                         else f"Start your free {TRIAL_DAYS}-day trial with `!trial`"),
            color=BOT_COLOR)
    await i.response.send_message(embed=e, ephemeral=True)

@bot.tree.command(name="setprefix", description="Change the server prefix (admin only)")
@app_commands.describe(prefix="New prefix (max 5 chars)")
async def slash_setprefix(i: discord.Interaction, prefix: str):
    if not i.guild or not i.user.guild_permissions.administrator:
        return await i.response.send_message(err("Admin only, server-only."), ephemeral=True)
    if len(prefix) > 5:
        return await i.response.send_message(err("Max 5 characters."), ephemeral=True)
    custom_prefixes[i.guild.id]        = prefix
    data["prefixes"][str(i.guild.id)]  = prefix
    save_data()
    await i.response.send_message(ok(f"Prefix set to `{prefix}`"), ephemeral=True)

@bot.tree.command(name="anglemode", description="Set your trig angle unit")
@app_commands.describe(mode="deg or rad")
@app_commands.choices(mode=[
    app_commands.Choice(name="Degrees", value="deg"),
    app_commands.Choice(name="Radians", value="rad"),
])
async def slash_anglemode(i: discord.Interaction, mode: str):
    angle_mode[i.user.id]            = mode
    data["angle"][str(i.user.id)]    = mode
    save_data()
    await i.response.send_message(
        ok(f"Angle mode set to **{'Degrees 🔺' if mode == 'deg' else 'Radians 〰️'}**"), ephemeral=True)

@bot.tree.command(name="noprefix", description="Toggle no-prefix for a user (owner only)")
@app_commands.describe(member="Member to toggle")
async def slash_noprefix(i: discord.Interaction, member: discord.Member):
    if not is_owner(i.user.id):
        return await i.response.send_message(err("Owner only."), ephemeral=True)
    if member.id in no_prefix_users:
        no_prefix_users.discard(member.id)
        msg = ok(f"Removed no-prefix from {member.mention}.")
    else:
        no_prefix_users.add(member.id)
        msg = ok(f"{member.mention} can now use commands without prefix.")
    data["noprefix"] = list(no_prefix_users)
    save_data()
    await i.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="setcount", description="Set counting channel (admin only)")
async def slash_setcount(i: discord.Interaction):
    if not i.guild or not i.user.guild_permissions.administrator:
        return await i.response.send_message(err("Admin only."), ephemeral=True)
    gid = str(i.guild.id)
    data["counting"][gid] = {"channel": i.channel.id, "current": 0, "last_user": None, "milestones": {}}
    save_data()
    await i.response.send_message(ok(f"Counting set to {i.channel.mention}. Start from **1**!"), ephemeral=True)

@bot.tree.command(name="resetcount", description="Reset the counting game (admin only)")
async def slash_resetcount(i: discord.Interaction):
    if not i.guild or not i.user.guild_permissions.administrator:
        return await i.response.send_message(err("Admin only."), ephemeral=True)
    gid = str(i.guild.id)
    if gid in data["counting"]:
        data["counting"][gid]["current"]   = 0
        data["counting"][gid]["last_user"] = None
        save_data()
        await i.response.send_message("🔄 Count reset to **0**. Start from **1**!", ephemeral=True)
    else:
        await i.response.send_message(err("No counting channel set."), ephemeral=True)

@bot.tree.command(name="ping", description="Check latency")
async def slash_ping(i: discord.Interaction):
    e = numexa_embed("🏓 Pong!")
    e.add_field(name="WebSocket Latency", value=f"`{round(bot.latency * 1000)}ms`")
    await i.response.send_message(embed=e)

@bot.tree.command(name="stats", description="View bot statistics")
async def slash_stats(i: discord.Interaction):
    e = numexa_embed("📊 Numexa Stats")
    e.add_field(name="Servers", value=f"`{len(bot.guilds)}`",                inline=True)
    e.add_field(name="Users",   value=f"`{len(set(bot.get_all_members()))}`", inline=True)
    e.add_field(name="Latency", value=f"`{round(bot.latency * 1000)}ms`",    inline=True)
    e.add_field(name="Uptime",  value=f"`{uptime_str()}`",                   inline=True)
    e.add_field(name="Library", value=f"`discord.py {discord.__version__}`", inline=True)
    await i.response.send_message(embed=e)

@bot.tree.command(name="serverinfo", description="View server information")
async def slash_serverinfo(i: discord.Interaction):
    if not i.guild:
        return await i.response.send_message(err("Server-only."), ephemeral=True)
    g = i.guild
    e = numexa_embed(f"🏠 {g.name}")
    e.set_thumbnail(url=g.icon.url if g.icon else None)
    e.add_field(name="Owner",    value=g.owner.mention if g.owner else "Unknown", inline=True)
    e.add_field(name="Members",  value=f"`{g.member_count}`",                     inline=True)
    e.add_field(name="Channels", value=f"`{len(g.channels)}`",                    inline=True)
    e.add_field(name="Roles",    value=f"`{len(g.roles)}`",                       inline=True)
    e.add_field(name="Created",  value=f"<t:{int(g.created_at.timestamp())}:R>",  inline=True)
    await i.response.send_message(embed=e)

@bot.tree.command(name="userinfo", description="View user information")
@app_commands.describe(member="Member to look up")
async def slash_userinfo(i: discord.Interaction, member: discord.Member = None):
    member = member or i.user
    e = numexa_embed(f"👤 {member}")
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="ID",       value=f"`{member.id}`",                             inline=True)
    e.add_field(name="Nickname", value=member.display_name,                           inline=True)
    e.add_field(name="Bot",      value="Yes" if member.bot else "No",                 inline=True)
    joined = f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown"
    e.add_field(name="Joined",   value=joined,                                        inline=True)
    e.add_field(name="Created",  value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    e.add_field(name="Top Role", value=member.top_role.mention,                       inline=True)
    await i.response.send_message(embed=e)

@bot.tree.command(name="help", description="Show all Numexa commands")
async def slash_help(i: discord.Interaction):
    view = HelpView()
    await i.response.send_message(embed=_help_overview(), view=view, ephemeral=True)

@bot.tree.command(name="invite", description="Get the invite link")
async def slash_invite(i: discord.Interaction):
    e = numexa_embed("👋 Invite Numexa", "Click below to add me to your server!")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Add Numexa", style=discord.ButtonStyle.link, url=INVITE_URL))
    await i.response.send_message(embed=e, view=v, ephemeral=True)

@bot.tree.command(name="support", description="Get the support server link")
async def slash_support(i: discord.Interaction):
    e = numexa_embed("💬 Support Server", "Join **The Devzone**.")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Join Devzone", style=discord.ButtonStyle.link, url=DEVZONE_INVITE))
    await i.response.send_message(embed=e, view=v, ephemeral=True)

@bot.tree.command(name="dashboard", description="Open the Numexa web dashboard")
async def slash_dashboard(i: discord.Interaction):
    e = numexa_embed("🧠 Numexa Dashboard")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Open Dashboard", style=discord.ButtonStyle.link, url=DASHBOARD_URL))
    await i.response.send_message(embed=e, view=v, ephemeral=True)


# ═════════════════════════ BOT EVENTS ═════════════════════════════

@bot.event
async def on_guild_join(guild):
    try:
        owner = guild.owner
        if not owner:
            return
        e = numexa_embed(
            "👋 Thanks for adding Numexa!",
            "Thank you for inviting **Numexa** to your server 🎉\n\n"
            "🧮 Numexa helps with calculations, calculus, and a server counting game.\n"
            f"⭐ Start your **free {TRIAL_DAYS}-day Premium trial** with `!trial`\n"
            "⚙️ Use `!help` or `/help` to get started."
        )
        e.add_field(name="🔗 Support", value=f"[Join The Devzone]({DEVZONE_INVITE})", inline=False)
        v = discord.ui.View()
        v.add_item(discord.ui.Button(label="Add Numexa",   style=discord.ButtonStyle.link, url=INVITE_URL))
        v.add_item(discord.ui.Button(label="Join Devzone", style=discord.ButtonStyle.link, url=DEVZONE_INVITE))
        v.add_item(discord.ui.Button(label="Dashboard",    style=discord.ButtonStyle.link, url=DASHBOARD_URL))
        await owner.send(embed=e, view=v)
    except discord.Forbidden:
        pass


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(err("You don't have permission to use this command."))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(err(f"Missing argument: `{error.param.name}`"))
    elif isinstance(error, commands.BadArgument):
        await ctx.send(err(f"Bad argument: {error}"))
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        raise error


# ─────────────────────────── COUNTING ─────────────────────────────
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    # ── @Numexa mention-only → about embed ────────────────────────
    if bot.user in message.mentions and message.content.strip() in (
        f"<@{bot.user.id}>", f"<@!{bot.user.id}>"
    ):
        latency = round(bot.latency * 1000)
        owner   = await bot.fetch_user(OWNER_ID)
        e = discord.Embed(
            title="👋 Hey there! I'm Numexa",
            description=(
                "I'm a **scientific Discord calculator bot** built to make math feel effortless.\n\n"
                "Whether you need to evaluate expressions, solve calculus problems, or run a "
                "fun counting game in your server — I've got you covered!\n\n"
                "Use `!help` or `/help` to explore all my commands."
            ),
            color=BOT_COLOR
        )
        e.set_thumbnail(url=bot.user.display_avatar.url)
        e.add_field(name="🧮 Calculator", value="Math & expressions",   inline=True)
        e.add_field(name="📐 Calculus",   value="Diff, integrate…",     inline=True)
        e.add_field(name="🔢 Counting",   value="Server counting game", inline=True)
        e.add_field(name="⭐ Premium",    value="Exclusive features",   inline=True)
        e.add_field(name="🏓 Ping",       value=f"`{latency}ms`",        inline=True)
        e.add_field(name="🌐 Dashboard",  value=f"[Open]({DASHBOARD_URL})", inline=True)
        e.set_footer(
            text=f"Made with 💜 by Aditya  •  {owner}",
            icon_url=owner.display_avatar.url if owner else None
        )
        v = discord.ui.View()
        v.add_item(discord.ui.Button(label="Add Numexa",   style=discord.ButtonStyle.link, url=INVITE_URL))
        v.add_item(discord.ui.Button(label="Join Devzone", style=discord.ButtonStyle.link, url=DEVZONE_INVITE))
        v.add_item(discord.ui.Button(label="Dashboard",    style=discord.ButtonStyle.link, url=DASHBOARD_URL))
        await message.reply(embed=e, view=v, mention_author=False)
        await message.channel.send(f"<@{OWNER_ID}>", delete_after=1)
        return

    gid      = str(message.guild.id)
    counting = data["counting"].get(gid)

    if counting and message.channel.id == counting["channel"]:
        content     = message.content.strip()
        check_emoji = _app_emojis.get("checkmark") or f"<:checkmark:{CHECK_EMOJI_ID}>"
        cross_emoji = _app_emojis.get("wrong")     or f"<:wrong:{CROSS_EMOJI_ID}>"

        if not content.isdigit():
            counting["current"] = 0; counting["last_user"] = None; save_data()
            await message.add_reaction(cross_emoji)
            await message.channel.send(
                f"{cross_emoji} {message.author.mention} broke the count! Only numbers allowed. Start from **1**.",
                delete_after=8)
            await bot.process_commands(message)
            return

        number   = int(content)
        expected = counting["current"] + 1

        if counting.get("last_user") == message.author.id:
            counting["current"] = 0; counting["last_user"] = None; save_data()
            await message.add_reaction(cross_emoji)
            await message.channel.send(
                f"{cross_emoji} {message.author.mention} can't count twice in a row! Start from **1**.",
                delete_after=8)
            await bot.process_commands(message)
            return

        if number != expected:
            counting["current"] = 0; counting["last_user"] = None; save_data()
            await message.add_reaction(cross_emoji)
            await message.channel.send(
                f"{cross_emoji} {message.author.mention} said **{number}** but expected **{expected}**! Start from **1**.",
                delete_after=8)
            await bot.process_commands(message)
            return

        counting["current"]   = number
        counting["last_user"] = message.author.id
        save_data()
        await message.add_reaction(check_emoji)

        # ── Milestone check (Premium) ──────────────────────────────
        if is_premium(message.guild.id):
            ms = counting.get("milestones", {})
            if str(number) in ms:
                role = message.guild.get_role(ms[str(number)])
                if role:
                    try:
                        await message.author.add_roles(role)
                        e = premium_embed(
                            "🎉 Milestone Reached!",
                            f"{message.author.mention} reached count **{number}** and earned {role.mention}!"
                        )
                        await message.channel.send(embed=e)
                    except discord.Forbidden:
                        pass

    await bot.process_commands(message)


# ──────────────────────── DAILY PROBLEM LOOP ──────────────────────
async def daily_problem_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now   = time.gmtime()
        today = time.strftime("%Y-%m-%d", time.gmtime())
        if now.tm_hour == 0 and now.tm_min == 0:
            for gid, config in list(data["daily"].items()):
                if config.get("last_sent") == today:
                    continue
                guild = bot.get_guild(int(gid))
                if not guild or not is_premium(int(gid)):
                    continue
                channel = guild.get_channel(config["channel"])
                if not channel:
                    continue
                problem, answer = random.choice(DAILY_PROBLEMS)
                e = discord.Embed(
                    title="🔔 Daily Math Problem",
                    description=f"**{problem}**\n\n||Answer: **{answer}**||",
                    color=PREMIUM_COLOR
                )
                e.set_footer(text="Reveal the answer by clicking the spoiler • Numexa Premium ⭐")
                try:
                    await channel.send(embed=e)
                    data["daily"][gid]["last_sent"] = today
                    save_data()
                except Exception:
                    pass
        await asyncio.sleep(60)


# ──────────────────────────── STATUS ──────────────────────────────
async def status_loop():
    statuses = itertools.cycle([
        discord.Activity(type=discord.ActivityType.watching,  name="math problems"),
        discord.Activity(type=discord.ActivityType.playing,   name="with equations"),
        discord.Activity(type=discord.ActivityType.listening, name="!help | /help"),
        discord.Activity(type=discord.ActivityType.watching,  name=f"{len(bot.guilds)} servers"),
    ])
    await bot.wait_until_ready()
    while not bot.is_closed():
        await bot.change_presence(activity=next(statuses))
        await asyncio.sleep(30)


@bot.event
async def on_ready():
    # Sync slash commands globally (may take up to 1 hour to propagate)
    synced = await bot.tree.sync()
    print(f"   Synced  : {len(synced)} slash commands globally")
    asyncio.create_task(status_loop())
    asyncio.create_task(daily_problem_loop())

    try:
        app_emoji_list = await bot.fetch_application_emojis()
        for emoji in app_emoji_list:
            _app_emojis[emoji.name] = emoji
        print(f"   Emojis  : loaded {len(_app_emojis)} — {list(_app_emojis.keys())}")
    except Exception as e:
        print(f"   Emojis  : failed — {e}")

    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    print(f"   Guilds  : {len(bot.guilds)}")
    print(f"   Premium : {sum(1 for r in data['premium'].values() if r.get('active'))} active servers")
    print(f"   Prefix  : {DEFAULT_PREFIX}")


# ──────────────────────────── RUN ─────────────────────────────────
if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set.")

bot.run(TOKEN)
