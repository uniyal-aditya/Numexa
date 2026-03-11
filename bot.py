# ============================================================
#  Numexa — Scientific Discord Calculator Bot
# ============================================================

import discord
from discord import app_commands
from discord.ext import commands
import sympy as sp
import math
import json
import os
import itertools
import asyncio
import time
from simpleeval import simple_eval

# ───────────────────────────── CONFIG ─────────────────────────────
TOKEN            = os.getenv("TOKEN")
OWNER_ID         = 800553680704110624
EXTRA_OWNERS     = {111111111111111111}          # replace with real IDs
ALL_OWNERS       = EXTRA_OWNERS | {OWNER_ID}
DEFAULT_PREFIX   = "!"
DATA_FILE        = "bot_data.json"
CHECK_EMOJI_ID   = 1460663385472503874
CROSS_EMOJI_ID   = 1460663471623504185
DEVZONE_INVITE   = "https://discord.gg/SmSx4uvVCD"
INVITE_URL       = (
    "https://discord.com/oauth2/authorize"
    "?client_id=1460289617264775333"
    "&permissions=5629501681765440"
    "&scope=bot+applications.commands"
)
DASHBOARD_URL    = "https://numexa.netlify.app"
BOT_COLOR        = 0x8A2BE2
START_TIME       = time.time()

# Custom emoji helpers — used everywhere instead of plain ✅ / ❌
def CHECK(bot):
    e = bot.get_emoji(CHECK_EMOJI_ID)
    return str(e) if e else "✅"

def CROSS(bot):
    e = bot.get_emoji(CROSS_EMOJI_ID)
    return str(e) if e else "❌"


# ───────────────────────── DATA STORAGE ───────────────────────────
def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"prefixes": {}, "noprefix": [], "angle": {}, "counting": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

for _key, _default in (("prefixes", {}), ("noprefix", []), ("angle", {}), ("counting", {})):
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

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

x = sp.symbols("x")


# ──────────────────────────── SAFE EVAL ───────────────────────────
def safe_eval(expr: str, user_id: int = None) -> str:
    expr = (expr
            .replace("^",  "**")
            .replace("π",  "pi")
            .replace("×",  "*")
            .replace("÷",  "/")
            .replace("–",  "-")
            .strip())

    mode = angle_mode.get(user_id, "rad")

    def _sin(v):  return math.sin(math.radians(v))  if mode == "deg" else math.sin(v)
    def _cos(v):  return math.cos(math.radians(v))  if mode == "deg" else math.cos(v)
    def _tan(v):  return math.tan(math.radians(v))  if mode == "deg" else math.tan(v)
    def _asin(v): return math.degrees(math.asin(v)) if mode == "deg" else math.asin(v)
    def _acos(v): return math.degrees(math.acos(v)) if mode == "deg" else math.acos(v)
    def _atan(v): return math.degrees(math.atan(v)) if mode == "deg" else math.atan(v)

    names = {
        "sin":   _sin,  "cos":   _cos,  "tan":   _tan,
        "asin":  _asin, "acos":  _acos, "atan":  _atan,
        "log":   math.log10, "ln": math.log,
        "sqrt":  math.sqrt,  "abs": abs,
        "floor": math.floor, "ceil": math.ceil, "round": round,
        "pi":    math.pi,    "e":   math.e,
        "inf":   math.inf,
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

def ok(msg: str) -> str:
    """Success message using custom check emoji."""
    e = bot.get_emoji(CHECK_EMOJI_ID)
    emoji = str(e) if e else "✅"
    return f"{emoji} {msg}"

def err(msg: str) -> str:
    """Error message using custom cross emoji."""
    e = bot.get_emoji(CROSS_EMOJI_ID)
    emoji = str(e) if e else "❌"
    return f"{emoji} {msg}"


# ─────────────────────── HELP MENU SYSTEM ─────────────────────────

def _help_overview() -> discord.Embed:
    e = numexa_embed(
        "📘 Numexa — Help Menu",
        "Welcome to **Numexa**, your scientific Discord calculator!\n\n"
        "Use the **dropdown below** to browse command categories.\n"
        "Both prefix (`!`) and slash (`/`) commands are supported."
    )
    e.add_field(
        name="📂 Available Categories",
        value=(
            "> 🧮 **Calculator** — Evaluate expressions & interactive UI\n"
            "> 📐 **Calculus** — Derivatives, integrals & differential equations\n"
            "> ⚙️ **Settings** — Prefix, angle mode & no-prefix\n"
            "> 🔢 **Counting** — Server counting game setup\n"
            "> 🛠️ **Utility** — Ping, stats, serverinfo, userinfo\n"
            "> 🔗 **Links** — Invite, support & dashboard"
        ),
        inline=False
    )
    e.set_thumbnail(url="https://numexa.netlify.app/favicon.ico")
    return e

def _help_calculator() -> discord.Embed:
    e = numexa_embed(
        "🧮 Calculator Commands",
        "Evaluate mathematical expressions with full scientific support."
    )
    e.add_field(
        name="📌 `calc <expr>`",
        value=(
            "Evaluate a math expression.\n"
            "```\n!calc sqrt(2)*pi\n!calc sin(45) + log(100)```"
            "**Supported:** `+` `-` `*` `/` `**` `^` `%` `sqrt` `abs`\n"
            "`log` `ln` `floor` `ceil` `round` `pi` `e` `inf`"
        ),
        inline=False
    )
    e.add_field(
        name="📌 `ui`",
        value=(
            "Open the **interactive button calculator** with full scientific functions.\n"
            "```\n!ui```"
            "Includes: `sin` `cos` `tan` `√` `log` and all standard operators."
        ),
        inline=False
    )
    return e

def _help_calculus() -> discord.Embed:
    e = numexa_embed(
        "📐 Calculus Commands",
        "Powered by **SymPy** — all expressions are w.r.t. `x`."
    )
    e.add_field(
        name="📌 `diff <expr>`",
        value="Differentiate an expression.\n```\n!diff x**3 + 2*x```",
        inline=False
    )
    e.add_field(
        name="📌 `integrate <expr>`",
        value="Integrate an expression (indefinite).\n```\n!integrate x**2 + 3*x```",
        inline=False
    )
    e.add_field(
        name="📌 `dsolve <eq>`",
        value="Solve a differential equation.\n```\n!dsolve f(x).diff(x) - f(x)```",
        inline=False
    )
    return e

def _help_settings() -> discord.Embed:
    e = numexa_embed(
        "⚙️ Settings Commands",
        "Configure Numexa for your server or personal preferences."
    )
    e.add_field(
        name="📌 `setprefix <prefix>`  *(Admin only)*",
        value="Change the server's command prefix.\n```\n!setprefix ?```",
        inline=False
    )
    e.add_field(
        name="📌 `anglemode <deg|rad>`",
        value="Set your personal trig angle unit.\n```\n!anglemode deg```",
        inline=False
    )
    e.add_field(
        name="📌 `noprefix <@user>`  *(Owner only)*",
        value="Toggle no-prefix mode for a user.\n```\n!noprefix @user```",
        inline=False
    )
    return e

def _help_counting() -> discord.Embed:
    e = numexa_embed(
        "🔢 Counting Game",
        "Set up a counting channel where members count together!"
    )
    e.add_field(
        name="📌 `setcount`  *(Admin only)*",
        value="Set the current channel as the counting channel.\n```\n!setcount```",
        inline=False
    )
    e.add_field(
        name="📌 `resetcount`  *(Admin only)*",
        value="Reset the count back to 0.\n```\n!resetcount```",
        inline=False
    )
    e.add_field(
        name="📋 Rules",
        value=(
            "> • Count in order starting from **1**\n"
            "> • No two messages in a row from the same user\n"
            "> • Wrong number or non-number resets count to 0"
        ),
        inline=False
    )
    return e

def _help_utility() -> discord.Embed:
    e = numexa_embed(
        "🛠️ Utility Commands",
        "General purpose commands for server and user info."
    )
    e.add_field(name="📌 `ping`",              value="Check Numexa's WebSocket latency.",              inline=False)
    e.add_field(name="📌 `stats`",             value="View bot statistics (servers, users, uptime).",   inline=False)
    e.add_field(name="📌 `serverinfo`",        value="View information about the current server.",       inline=False)
    e.add_field(name="📌 `userinfo [@user]`",  value="View info about yourself or a mentioned member.", inline=False)
    return e

def _help_links() -> discord.Embed:
    e = numexa_embed(
        "🔗 Links & Resources",
        "Everything you need to get the most out of Numexa."
    )
    e.add_field(name="👋 `invite`",    value=f"[Add Numexa to your server]({INVITE_URL})",   inline=False)
    e.add_field(name="💬 `support`",   value=f"[Join The Devzone]({DEVZONE_INVITE})",         inline=False)
    e.add_field(name="🧠 `dashboard`", value=f"[Open the web dashboard]({DASHBOARD_URL})",    inline=False)
    return e


HELP_PAGES = {
    "overview":   ("📘 Overview",    _help_overview),
    "calculator": ("🧮 Calculator",  _help_calculator),
    "calculus":   ("📐 Calculus",    _help_calculus),
    "settings":   ("⚙️ Settings",    _help_settings),
    "counting":   ("🔢 Counting",    _help_counting),
    "utility":    ("🛠️ Utility",     _help_utility),
    "links":      ("🔗 Links",       _help_links),
}


class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=label,
                value=key,
                emoji=label.split()[0],
                description=self._desc(key),
                default=(key == "overview")
            )
            for key, (label, _) in HELP_PAGES.items()
        ]
        super().__init__(
            placeholder="📂 Select a category to explore…",
            min_values=1,
            max_values=1,
            options=options,
        )

    @staticmethod
    def _desc(key: str) -> str:
        descs = {
            "overview":   "Start here — all categories at a glance",
            "calculator": "calc, ui — expressions & button calculator",
            "calculus":   "diff, integrate, dsolve — SymPy powered",
            "settings":   "setprefix, anglemode, noprefix",
            "counting":   "setcount, resetcount — counting game",
            "utility":    "ping, stats, serverinfo, userinfo",
            "links":      "invite, support, dashboard",
        }
        return descs.get(key, "")

    async def callback(self, interaction: discord.Interaction):
        # Update the "default" highlight on the selected option
        for opt in self.options:
            opt.default = (opt.value == self.values[0])
        _, builder = HELP_PAGES[self.values[0]]
        await interaction.response.edit_message(embed=builder(), view=self.view)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(HelpSelect())
        self.message: discord.Message | None = None

    @discord.ui.button(label="🏠 Home", style=discord.ButtonStyle.secondary, row=1)
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Reset dropdown to overview default
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
        display = self.expression or "0"
        await interaction.response.edit_message(content=f"```\n{display}\n```", view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                err("This calculator belongs to someone else. Use `!ui` to open your own."),
                ephemeral=True
            )
            return False
        return True

    # ── Row 0 ──
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

    # ── Row 1 ──
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
        opens  = self.expression.count("(")
        closes = self.expression.count(")")
        self.expression += "(" if opens == closes else ")"
        await self.update(i)

    # ── Row 2 ──
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

    # ── Row 3 ──
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

    # ── Row 4 — Scientific ──
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
    custom_prefixes[ctx.guild.id]        = prefix
    data["prefixes"][str(ctx.guild.id)]  = prefix
    save_data()
    await ctx.send(ok(f"Prefix set to `{prefix}`"))

@bot.command(name="anglemode")
async def cmd_anglemode(ctx, mode: str):
    mode = mode.lower()
    if mode not in ("deg", "rad"):
        return await ctx.send(err("Use `deg` or `rad`."))
    angle_mode[ctx.author.id]             = mode
    data["angle"][str(ctx.author.id)]     = mode
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
    data["counting"][gid] = {"channel": ctx.channel.id, "current": 0, "last_user": None}
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
    latency = round(bot.latency * 1000)
    e = numexa_embed("🏓 Pong!")
    e.add_field(name="WebSocket Latency", value=f"`{latency}ms`")
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
        return await ctx.send(err("This command can only be used in a server."))
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


# ═══════════════════════ SLASH COMMANDS ═══════════════════════════

# ── Math ──────────────────────────────────────────────────────────
@bot.tree.command(name="calc", description="Evaluate a math expression")
@app_commands.describe(expr="The expression to evaluate (e.g. sqrt(2)*pi)")
async def slash_calc(i: discord.Interaction, expr: str):
    try:
        result = safe_eval(expr, i.user.id)
        e = numexa_embed("🧮 Result")
        e.add_field(name="Expression", value=f"`{expr}`",     inline=False)
        e.add_field(name="Result",     value=f"**{result}**", inline=False)
        await i.response.send_message(embed=e)
    except Exception as ex:
        await i.response.send_message(err(f"**Error:** `{ex}`"), ephemeral=True)

@bot.tree.command(name="diff", description="Differentiate an expression w.r.t. x")
@app_commands.describe(expr="Expression to differentiate (e.g. x**3 + 2*x)")
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
@app_commands.describe(expr="Expression to integrate (e.g. x**2 + 3*x)")
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
@app_commands.describe(eq="Differential equation (e.g. f(x).diff(x) - f(x))")
async def slash_dsolve(i: discord.Interaction, eq: str):
    try:
        result = sp.dsolve(sp.sympify(eq))
        e = numexa_embed("🔬 Differential Equation Solution")
        e.add_field(name="Equation", value=f"`{eq}`",     inline=False)
        e.add_field(name="Solution", value=f"`{result}`", inline=False)
        await i.response.send_message(embed=e)
    except Exception as ex:
        await i.response.send_message(err(f"**Error:** `{ex}`"), ephemeral=True)

@bot.tree.command(name="ui", description="Open the interactive button calculator")
async def slash_ui(i: discord.Interaction):
    mode = angle_mode.get(i.user.id, "rad").upper()
    await i.response.send_message(
        f"```\n0\n```\n*Angle mode: **{mode}***",
        view=CalculatorView(i.user.id)
    )


# ── Settings ──────────────────────────────────────────────────────
@bot.tree.command(name="setprefix", description="Change the server prefix (admin only)")
@app_commands.describe(prefix="New prefix (max 5 characters)")
async def slash_setprefix(i: discord.Interaction, prefix: str):
    if not i.guild:
        return await i.response.send_message(err("Server-only command."), ephemeral=True)
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message(err("Administrator permission required."), ephemeral=True)
    if len(prefix) > 5:
        return await i.response.send_message(err("Prefix must be 5 characters or fewer."), ephemeral=True)
    custom_prefixes[i.guild.id]         = prefix
    data["prefixes"][str(i.guild.id)]   = prefix
    save_data()
    await i.response.send_message(ok(f"Prefix set to `{prefix}`"), ephemeral=True)

@bot.tree.command(name="anglemode", description="Set your trig angle unit")
@app_commands.describe(mode="deg for degrees, rad for radians")
@app_commands.choices(mode=[
    app_commands.Choice(name="Degrees", value="deg"),
    app_commands.Choice(name="Radians", value="rad"),
])
async def slash_anglemode(i: discord.Interaction, mode: str):
    angle_mode[i.user.id]             = mode
    data["angle"][str(i.user.id)]     = mode
    save_data()
    label = "Degrees 🔺" if mode == "deg" else "Radians 〰️"
    await i.response.send_message(ok(f"Angle mode set to **{label}**"), ephemeral=True)

@bot.tree.command(name="noprefix", description="Toggle no-prefix mode for a user (owner only)")
@app_commands.describe(member="The member to toggle no-prefix for")
async def slash_noprefix(i: discord.Interaction, member: discord.Member):
    if not is_owner(i.user.id):
        return await i.response.send_message(err("Owner only."), ephemeral=True)
    if member.id in no_prefix_users:
        no_prefix_users.discard(member.id)
        msg = ok(f"Removed no-prefix from {member.mention}.")
    else:
        no_prefix_users.add(member.id)
        msg = ok(f"{member.mention} can now use commands without a prefix.")
    data["noprefix"] = list(no_prefix_users)
    save_data()
    await i.response.send_message(msg, ephemeral=True)


# ── Counting ──────────────────────────────────────────────────────
@bot.tree.command(name="setcount", description="Set this channel as the counting channel (admin only)")
async def slash_setcount(i: discord.Interaction):
    if not i.guild:
        return await i.response.send_message(err("Server-only command."), ephemeral=True)
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message(err("Administrator permission required."), ephemeral=True)
    gid = str(i.guild.id)
    data["counting"][gid] = {"channel": i.channel.id, "current": 0, "last_user": None}
    save_data()
    await i.response.send_message(
        ok(f"Counting channel set to {i.channel.mention}. Start from **1**!"), ephemeral=True
    )

@bot.tree.command(name="resetcount", description="Reset the counting game to 0 (admin only)")
async def slash_resetcount(i: discord.Interaction):
    if not i.guild:
        return await i.response.send_message(err("Server-only command."), ephemeral=True)
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message(err("Administrator permission required."), ephemeral=True)
    gid = str(i.guild.id)
    if gid in data["counting"]:
        data["counting"][gid]["current"]   = 0
        data["counting"][gid]["last_user"] = None
        save_data()
        await i.response.send_message("🔄 Count reset to **0**. Start again from **1**!", ephemeral=True)
    else:
        await i.response.send_message(err("No counting channel set."), ephemeral=True)


# ── Utility ───────────────────────────────────────────────────────
@bot.tree.command(name="ping", description="Check Numexa's latency")
async def slash_ping(i: discord.Interaction):
    latency = round(bot.latency * 1000)
    e = numexa_embed("🏓 Pong!")
    e.add_field(name="WebSocket Latency", value=f"`{latency}ms`")
    await i.response.send_message(embed=e)

@bot.tree.command(name="stats", description="View bot statistics")
async def slash_stats(i: discord.Interaction):
    e = numexa_embed("📊 Numexa Stats")
    e.add_field(name="Servers",  value=f"`{len(bot.guilds)}`",                inline=True)
    e.add_field(name="Users",    value=f"`{len(set(bot.get_all_members()))}`", inline=True)
    e.add_field(name="Latency",  value=f"`{round(bot.latency * 1000)}ms`",    inline=True)
    e.add_field(name="Uptime",   value=f"`{uptime_str()}`",                   inline=True)
    e.add_field(name="Library",  value=f"`discord.py {discord.__version__}`", inline=True)
    await i.response.send_message(embed=e)

@bot.tree.command(name="serverinfo", description="View server information")
async def slash_serverinfo(i: discord.Interaction):
    if not i.guild:
        return await i.response.send_message(err("Server-only command."), ephemeral=True)
    g = i.guild
    e = numexa_embed(f"🏠 {g.name}")
    e.set_thumbnail(url=g.icon.url if g.icon else None)
    e.add_field(name="Owner",    value=g.owner.mention if g.owner else "Unknown", inline=True)
    e.add_field(name="Members",  value=f"`{g.member_count}`",                     inline=True)
    e.add_field(name="Channels", value=f"`{len(g.channels)}`",                    inline=True)
    e.add_field(name="Roles",    value=f"`{len(g.roles)}`",                       inline=True)
    e.add_field(name="Created",  value=f"<t:{int(g.created_at.timestamp())}:R>",  inline=True)
    await i.response.send_message(embed=e)

@bot.tree.command(name="userinfo", description="View info about a user")
@app_commands.describe(member="The member to look up (defaults to yourself)")
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


# ── Links ─────────────────────────────────────────────────────────
@bot.tree.command(name="help", description="Show all Numexa commands")
async def slash_help(i: discord.Interaction):
    view = HelpView()
    await i.response.send_message(embed=_help_overview(), view=view, ephemeral=True)

@bot.tree.command(name="invite", description="Get the invite link for Numexa")
async def slash_invite(i: discord.Interaction):
    e = numexa_embed("👋 Invite Numexa", "Click below to add me to your server!")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Add Numexa", style=discord.ButtonStyle.link, url=INVITE_URL))
    await i.response.send_message(embed=e, view=v, ephemeral=True)

@bot.tree.command(name="support", description="Get the support server link")
async def slash_support(i: discord.Interaction):
    e = numexa_embed("💬 Support Server", "Join **The Devzone** for help, updates & announcements.")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Join Devzone", style=discord.ButtonStyle.link, url=DEVZONE_INVITE))
    await i.response.send_message(embed=e, view=v, ephemeral=True)

@bot.tree.command(name="dashboard", description="Open the Numexa web dashboard")
async def slash_dashboard(i: discord.Interaction):
    e = numexa_embed("🧠 Numexa Dashboard", "Manage settings, view stats, and configure Numexa.")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Open Dashboard", style=discord.ButtonStyle.link, url=DASHBOARD_URL))
    await i.response.send_message(embed=e, view=v, ephemeral=True)


# ═════════════════════════ BOT EVENTS ═════════════════════════════

@bot.event
async def on_guild_join(guild):
    try:
        owner = guild.owner
        if owner is None:
            return
        e = numexa_embed(
            "👋 Thanks for adding Numexa!",
            "Thank you for inviting **Numexa** to your server 🎉\n\n"
            "🧮 Numexa helps with calculations, calculus, and a server counting game.\n"
            "⚙️ Use `!help` or `/help` to get started."
        )
        e.add_field(name="🔗 Support Server", value=f"[Join The Devzone]({DEVZONE_INVITE})", inline=False)
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

    # ── @Numexa mention-only → send about embed ───────────────────
    if bot.user in message.mentions and message.content.strip() in (
        f"<@{bot.user.id}>", f"<@!{bot.user.id}>"
    ):
        latency = round(bot.latency * 1000)
        owner   = await bot.fetch_user(OWNER_ID)          # Aditya
        e = discord.Embed(
            title="👋 Hey there! I'm Numexa",
            description=(
                f"I'm a **scientific Discord calculator bot** built to make math feel effortless.\n\n"
                f"Whether you need to evaluate expressions, solve calculus problems, or run a "
                f"fun counting game in your server — I've got you covered!\n\n"
                f"Use `!help` or `/help` to explore all my commands."
            ),
            color=BOT_COLOR
        )
        e.set_thumbnail(url=bot.user.display_avatar.url)
        e.add_field(name="🧮 Calculator",  value="Evaluate math expressions",        inline=True)
        e.add_field(name="📐 Calculus",    value="Derivatives, integrals & more",    inline=True)
        e.add_field(name="🔢 Counting",    value="Server counting game",             inline=True)
        e.add_field(name="⚙️ Settings",    value="Prefix & angle mode",             inline=True)
        e.add_field(name="🏓 Ping",        value=f"`{latency}ms`",                   inline=True)
        e.add_field(name="🌐 Dashboard",   value=f"[Open]({DASHBOARD_URL})",         inline=True)
        e.set_footer(
            text=f"Made with 💜 by Aditya  •  {owner}",
            icon_url=owner.display_avatar.url if owner else None
        )
        v = discord.ui.View()
        v.add_item(discord.ui.Button(label="Add Numexa",   style=discord.ButtonStyle.link, url=INVITE_URL))
        v.add_item(discord.ui.Button(label="Join Devzone", style=discord.ButtonStyle.link, url=DEVZONE_INVITE))
        v.add_item(discord.ui.Button(label="Dashboard",    style=discord.ButtonStyle.link, url=DASHBOARD_URL))
        await message.reply(embed=e, view=v, mention_author=False)
        # Also ping the owner so Aditya gets notified
        await message.channel.send(f"<@{OWNER_ID}>", delete_after=1)
        return

    gid      = str(message.guild.id)
    counting = data["counting"].get(gid)

    if counting and message.channel.id == counting["channel"]:
        content     = message.content.strip()
        check_emoji = f"<:checkmark:{CHECK_EMOJI_ID}>"
        cross_emoji = f"<:wrong:{CROSS_EMOJI_ID}>"

        if not content.isdigit():
            counting["current"]   = 0
            counting["last_user"] = None
            save_data()
            await message.add_reaction(cross_emoji)
            await message.channel.send(
                f"{cross_emoji} {message.author.mention} broke the count! "
                f"Only numbers allowed. Start again from **1**.",
                delete_after=8
            )
            await bot.process_commands(message)
            return

        number   = int(content)
        expected = counting["current"] + 1

        if counting.get("last_user") == message.author.id:
            counting["current"]   = 0
            counting["last_user"] = None
            save_data()
            await message.add_reaction(cross_emoji)
            await message.channel.send(
                f"{cross_emoji} {message.author.mention} can't count twice in a row! "
                f"Start again from **1**.",
                delete_after=8
            )
            await bot.process_commands(message)
            return

        if number != expected:
            counting["current"]   = 0
            counting["last_user"] = None
            save_data()
            await message.add_reaction(cross_emoji)
            await message.channel.send(
                f"{cross_emoji} {message.author.mention} said **{number}** but the next number was **{expected}**! "
                f"Start again from **1**.",
                delete_after=8
            )
            await bot.process_commands(message)
            return

        counting["current"]   = number
        counting["last_user"] = message.author.id
        save_data()
        await message.add_reaction(check_emoji)

    await bot.process_commands(message)


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
    await bot.tree.sync()
    asyncio.create_task(status_loop())
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    print(f"   Guilds : {len(bot.guilds)}")
    print(f"   Prefix : {DEFAULT_PREFIX}")


# ──────────────────────────── RUN ─────────────────────────────────
if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set.")

bot.run(TOKEN)
