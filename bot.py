# ============================================================
#  Numexa — Scientific Discord Calculator Bot  v2.0
# ============================================================

import discord
from discord.ext import commands
import sympy as sp
import math
import json
import os
import itertools
import asyncio
import time
import statistics
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ── HEALTH SERVER (keeps Render awake) ──
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Numexa is alive!')
    def log_message(self, *args):
        pass

threading.Thread(
    target=lambda: HTTPServer(('0.0.0.0', 8080), HealthHandler).serve_forever(),
    daemon=True
).start()

from simpleeval import simple_eval

# ───────────────────────────── CONFIG ─────────────────────────────
TOKEN            = os.getenv("TOKEN")
OWNER_ID         = 800553680704110624
EXTRA_OWNERS     = {111111111111111111}
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

# ───────────────────────── DATA STORAGE ───────────────────────────
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"prefixes": {}, "noprefix": [], "angle": {}, "counting": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()
for key in ("prefixes", "noprefix", "angle", "counting"):
    data.setdefault(key, {} if key != "noprefix" else [])

custom_prefixes = {int(k): v for k, v in data["prefixes"].items()}
no_prefix_users = set(data["noprefix"])
angle_mode      = {int(k): v for k, v in data["angle"].items()}

# ──────────────────────── PREFIX HANDLER ──────────────────────────
def get_prefix(bot, message):
    if message.author.id in no_prefix_users:
        return ""
    guild_id = message.guild.id if message.guild else None
    return custom_prefixes.get(guild_id, DEFAULT_PREFIX)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

x, y, n = sp.symbols("x y n")

# ──────────────────────────── SAFE EVAL ───────────────────────────
def safe_eval(expr: str, user_id=None) -> str:
    expr = (expr
            .replace("^", "**")
            .replace("π", "pi")
            .replace("×", "*")
            .replace("÷", "/")
            .strip())

    mode = angle_mode.get(user_id, "rad")

    def _sin(v):   return math.sin(math.radians(v))  if mode == "deg" else math.sin(v)
    def _cos(v):   return math.cos(math.radians(v))  if mode == "deg" else math.cos(v)
    def _tan(v):   return math.tan(math.radians(v))  if mode == "deg" else math.tan(v)
    def _asin(v):  return math.degrees(math.asin(v)) if mode == "deg" else math.asin(v)
    def _acos(v):  return math.degrees(math.acos(v)) if mode == "deg" else math.acos(v)
    def _atan(v):  return math.degrees(math.atan(v)) if mode == "deg" else math.atan(v)
    def _atan2(y, x): return math.degrees(math.atan2(y, x)) if mode == "deg" else math.atan2(y, x)
    def _sinh(v):  return math.sinh(v)
    def _cosh(v):  return math.cosh(v)
    def _tanh(v):  return math.tanh(v)
    def _log(v, base=10): return math.log(v, base)
    def _nCr(n, r): return math.comb(int(n), int(r))
    def _nPr(n, r): return math.perm(int(n), int(r))

    names = {
        # trig
        "sin": _sin, "cos": _cos, "tan": _tan,
        "asin": _asin, "acos": _acos, "atan": _atan, "atan2": _atan2,
        # hyperbolic
        "sinh": _sinh, "cosh": _cosh, "tanh": _tanh,
        # logarithms / exponential
        "log": _log, "log2": math.log2, "log10": math.log10, "ln": math.log, "exp": math.exp,
        # roots / powers
        "sqrt": math.sqrt, "cbrt": lambda v: v ** (1/3),
        "pow": pow,
        # rounding
        "abs": abs, "floor": math.floor, "ceil": math.ceil, "round": round,
        # combinatorics
        "factorial": math.factorial,
        "nCr": _nCr, "nPr": _nPr,
        "gcd": math.gcd, "lcm": math.lcm,
        # constants
        "pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf,
        "phi": (1 + math.sqrt(5)) / 2,
    }

    result = simple_eval(expr, names=names)
    if isinstance(result, float) and result.is_integer():
        return str(int(result))
    if isinstance(result, float):
        return str(round(result, 10)).rstrip('0').rstrip('.')
    return str(result)


# ─────────────────────────── HELPERS ──────────────────────────────
def is_owner(user_id): return user_id in ALL_OWNERS

def numexa_embed(title, description=""):
    e = discord.Embed(title=title, description=description, color=BOT_COLOR)
    e.set_footer(text="Numexa • Scientific Discord Bot")
    return e

def uptime_str():
    secs = int(time.time() - START_TIME)
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    return f"{h}h {m}m {s}s"

def fmt_result(expr, result, title="🧮 Result"):
    e = numexa_embed(title)
    e.add_field(name="Expression", value=f"```{expr}```", inline=False)
    e.add_field(name="Result",     value=f"```{result}```", inline=False)
    return e


# ───────────────────────── CALCULATOR UI ──────────────────────────
class CalculatorView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.expression = ""
        self.user_id    = user_id

    async def update(self, interaction):
        display = self.expression or "0"
        mode    = angle_mode.get(self.user_id, "rad").upper()
        await interaction.response.edit_message(
            content=f"```\n{display}\n```*Mode: **{mode}***",
            view=self
        )

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This calculator belongs to someone else. Use `!ui` to open your own.",
                ephemeral=True
            )
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
        opens = self.expression.count("(")
        closes = self.expression.count(")")
        self.expression += "(" if opens == closes else ")"
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
        except Exception:
            self.expression = "Error"
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


# ═══════════════════ REDESIGNED HELP EMBED ════════════════════════
def help_embed():
    e = discord.Embed(
        title="<:numexa:> Numexa — Command Centre",
        description=(
            "> Scientific Discord bot with calculus, math functions, counting & more.\n"
            "> Prefix: `!`  ·  Slash: `/`  ·  Both work for every command."
        ),
        color=BOT_COLOR
    )

    e.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🧮  Math & Calculator",
        value=(
            "`calc <expr>` — Evaluate any expression\n"
            "`ui` — Button calculator in Discord\n"
            "`matrix <op> <A>` — Matrix operations\n"
            "`stats <nums>` — Statistics on a list\n"
            "`conv <val> <from> <to>` — Unit conversion"
        ),
        inline=False
    )

    e.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n∫  Calculus",
        value=(
            "`diff <expr>` — Differentiate w.r.t. x\n"
            "`integrate <expr>` — Integrate w.r.t. x\n"
            "`dsolve <eq>` — Solve differential equation\n"
            "`limit <expr> <point>` — Compute a limit\n"
            "`taylor <expr> <n>` — Taylor series (n terms)"
        ),
        inline=False
    )

    e.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📐  Trig & Functions",
        value=(
            "`trig <expr>` — sin, cos, tan, asin, acos, atan\n"
            "`hyp <expr>` — sinh, cosh, tanh\n"
            "`anglemode <deg|rad>` — Switch angle unit\n"
            "**Supported in !calc:** `sin` `cos` `tan` `asin` `acos` `atan`\n"
            "`sinh` `cosh` `tanh` `sqrt` `cbrt` `log` `ln` `log2` `exp` `abs` `floor` `ceil` `round`"
        ),
        inline=False
    )

    e.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🔢  Number Theory & Combinatorics",
        value=(
            "`factor <n>` — Prime factorisation\n"
            "`isprime <n>` — Primality check\n"
            "`gcd <a> <b>` — GCD of two numbers\n"
            "`lcm <a> <b>` — LCM of two numbers\n"
            "`ncr <n> <r>` — Combinations  nCr\n"
            "`npr <n> <r>` — Permutations  nPr\n"
            "`factorial <n>` — n!"
        ),
        inline=False
    )

    e.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📊  Statistics",
        value=(
            "`mean <nums>` — Average\n"
            "`median <nums>` — Median\n"
            "`mode <nums>` — Mode\n"
            "`stddev <nums>` — Standard deviation\n"
            "`variance <nums>` — Variance\n"
            "*(pass numbers space-separated, e.g. `!mean 2 4 6 8`)*"
        ),
        inline=False
    )

    e.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🔡  Algebra & Symbolic",
        value=(
            "`simplify <expr>` — Simplify expression\n"
            "`expand <expr>` — Expand expression\n"
            "`factor_expr <expr>` — Factor a polynomial\n"
            "`solve <expr>` — Solve equation for x\n"
            "`roots <poly>` — Find polynomial roots"
        ),
        inline=False
    )

    e.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🔢  Counting Game",
        value=(
            "`setcount` — Set counting channel *(admin)*\n"
            "`resetcount` — Reset count to 0 *(admin)*"
        ),
        inline=False
    )

    e.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n⚙️  Settings & Utility",
        value=(
            "`setprefix <p>` — Change prefix *(admin)*\n"
            "`noprefix @user` — Toggle no-prefix *(owner)*\n"
            "`anglemode <deg|rad>` — Set trig unit\n"
            "`ping` — Latency  ·  `stats` — Bot stats\n"
            "`serverinfo` — Server info  ·  `userinfo [@u]` — User info\n"
            "`invite` — Invite link  ·  `support` — Support server\n"
            "`dashboard` — Web dashboard"
        ),
        inline=False
    )

    e.set_footer(text="Numexa v2.0 • numexa.netlify.app • !help for this menu")
    return e


# ═══════════════════════ MATH COMMANDS ════════════════════════════

# ── Basic Calculator ───────────────────────────────────────────────
@bot.command()
async def calc(ctx, *, expr: str):
    try:
        result = safe_eval(expr, ctx.author.id)
        await ctx.send(embed=fmt_result(expr, result))
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def ui(ctx):
    mode = angle_mode.get(ctx.author.id, "rad").upper()
    await ctx.send(
        f"```\n0\n```*Mode: **{mode}***",
        view=CalculatorView(ctx.author.id)
    )

# ── Calculus ───────────────────────────────────────────────────────
@bot.command()
async def diff(ctx, *, expr: str):
    try:
        result = sp.diff(sp.sympify(expr), x)
        e = numexa_embed("📐 Derivative")
        e.add_field(name="f(x)",  value=f"```{expr}```",      inline=False)
        e.add_field(name="f′(x)", value=f"```{result}```",    inline=False)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def integrate(ctx, *, expr: str):
    try:
        result = sp.integrate(sp.sympify(expr), x)
        e = numexa_embed("∫ Integral")
        e.add_field(name="f(x)",    value=f"```{expr}```",           inline=False)
        e.add_field(name="∫f(x)dx", value=f"```{result} + C```",     inline=False)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def dsolve(ctx, *, eq: str):
    try:
        result = sp.dsolve(sp.sympify(eq))
        e = numexa_embed("🔬 ODE Solution")
        e.add_field(name="Equation", value=f"```{eq}```",       inline=False)
        e.add_field(name="Solution", value=f"```{result}```",   inline=False)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def limit(ctx, expr: str, point: str = "0"):
    try:
        pt  = sp.sympify(point)
        result = sp.limit(sp.sympify(expr), x, pt)
        e = numexa_embed("🔢 Limit")
        e.add_field(name="Expression", value=f"```{expr}```",              inline=False)
        e.add_field(name=f"lim x→{point}", value=f"```{result}```",        inline=False)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def taylor(ctx, expr: str, n: int = 5):
    try:
        result = sp.series(sp.sympify(expr), x, 0, n)
        e = numexa_embed("📈 Taylor Series")
        e.add_field(name="f(x)",        value=f"```{expr}```",           inline=False)
        e.add_field(name=f"Around x=0, {n} terms", value=f"```{result}```", inline=False)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

# ── Algebra & Symbolic ─────────────────────────────────────────────
@bot.command()
async def simplify(ctx, *, expr: str):
    try:
        result = sp.simplify(sp.sympify(expr))
        await ctx.send(embed=fmt_result(expr, result, "✏️ Simplified"))
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def expand(ctx, *, expr: str):
    try:
        result = sp.expand(sp.sympify(expr))
        await ctx.send(embed=fmt_result(expr, result, "📤 Expanded"))
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command(name="factor_expr")
async def factor_expr(ctx, *, expr: str):
    try:
        result = sp.factor(sp.sympify(expr))
        await ctx.send(embed=fmt_result(expr, result, "🔳 Factored"))
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def solve(ctx, *, expr: str):
    try:
        result = sp.solve(sp.sympify(expr), x)
        e = numexa_embed("🔍 Solve for x")
        e.add_field(name="Equation",  value=f"```{expr} = 0```", inline=False)
        e.add_field(name="Solutions", value=f"```{result}```",    inline=False)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def roots(ctx, *, poly: str):
    try:
        result = sp.roots(sp.sympify(poly), x)
        formatted = "\n".join([f"x = {r}  (multiplicity {m})" for r, m in result.items()])
        e = numexa_embed("🌱 Polynomial Roots")
        e.add_field(name="Polynomial", value=f"```{poly}```",        inline=False)
        e.add_field(name="Roots",      value=f"```{formatted or 'No roots found'}```", inline=False)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

# ── Matrix Operations ──────────────────────────────────────────────
@bot.command()
async def matrix(ctx, op: str, *, expr: str):
    """
    !matrix inv [[1,2],[3,4]]
    !matrix det [[1,2],[3,4]]
    !matrix transpose [[1,2],[3,4]]
    !matrix eigenvals [[1,2],[3,4]]
    !matrix rref [[1,2,3],[4,5,6],[7,8,9]]
    """
    try:
        M = sp.Matrix(sp.sympify(expr))
        op = op.lower()
        if op == "inv":
            result = M.inv()
            title = "🔄 Matrix Inverse"
        elif op == "det":
            result = M.det()
            title = "🔢 Determinant"
        elif op in ("transpose", "T"):
            result = M.T
            title = "↔️ Transpose"
        elif op == "eigenvals":
            result = M.eigenvals()
            title = "λ Eigenvalues"
        elif op == "eigenvects":
            result = M.eigenvects()
            title = "→ Eigenvectors"
        elif op == "rref":
            result, pivots = M.rref()
            title = f"📊 RREF (pivots: {pivots})"
        elif op == "rank":
            result = M.rank()
            title = "📏 Rank"
        elif op == "trace":
            result = M.trace()
            title = "🔵 Trace"
        elif op == "norm":
            result = M.norm()
            title = "📐 Norm"
        else:
            return await ctx.send(f"❌ Unknown operation `{op}`. Use: `inv` `det` `transpose` `eigenvals` `rref` `rank` `trace`")

        e = numexa_embed(title)
        e.add_field(name="Matrix", value=f"```{expr}```",      inline=False)
        e.add_field(name="Result", value=f"```{result}```",    inline=False)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

# ── Number Theory ──────────────────────────────────────────────────
@bot.command()
async def factor(ctx, n: int):
    try:
        result = sp.factorint(n)
        formatted = " × ".join([f"{p}^{e}" if e > 1 else str(p) for p, e in result.items()])
        e = numexa_embed("🔳 Prime Factorisation")
        e.add_field(name="Number",        value=f"`{n}`",       inline=True)
        e.add_field(name="Factorisation", value=f"`{formatted}`", inline=True)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def isprime(ctx, n: int):
    result = sp.isprime(n)
    e = numexa_embed("🔍 Primality Check")
    e.add_field(name="Number",   value=f"`{n}`",                         inline=True)
    e.add_field(name="Is Prime", value="✅ Yes" if result else "❌ No",  inline=True)
    await ctx.send(embed=e)

@bot.command()
async def gcd(ctx, a: int, b: int):
    result = math.gcd(a, b)
    e = numexa_embed("🔢 GCD")
    e.add_field(name="Inputs", value=f"`{a}`, `{b}`",  inline=True)
    e.add_field(name="GCD",    value=f"`{result}`",     inline=True)
    await ctx.send(embed=e)

@bot.command()
async def lcm(ctx, a: int, b: int):
    result = math.lcm(a, b)
    e = numexa_embed("🔢 LCM")
    e.add_field(name="Inputs", value=f"`{a}`, `{b}`",  inline=True)
    e.add_field(name="LCM",    value=f"`{result}`",     inline=True)
    await ctx.send(embed=e)

@bot.command()
async def ncr(ctx, n: int, r: int):
    result = math.comb(n, r)
    e = numexa_embed("🎲 Combinations")
    e.add_field(name="C(n,r)", value=f"`C({n},{r})`",  inline=True)
    e.add_field(name="Result", value=f"`{result}`",    inline=True)
    await ctx.send(embed=e)

@bot.command()
async def npr(ctx, n: int, r: int):
    result = math.perm(n, r)
    e = numexa_embed("🎲 Permutations")
    e.add_field(name="P(n,r)", value=f"`P({n},{r})`",  inline=True)
    e.add_field(name="Result", value=f"`{result}`",    inline=True)
    await ctx.send(embed=e)

@bot.command()
async def factorial(ctx, n: int):
    if n > 1000:
        return await ctx.send("❌ Too large (max 1000).")
    result = math.factorial(n)
    e = numexa_embed("❗ Factorial")
    e.add_field(name="n",   value=f"`{n}`",      inline=True)
    e.add_field(name="n!",  value=f"`{result}`", inline=True)
    await ctx.send(embed=e)

# ── Statistics ─────────────────────────────────────────────────────
def parse_nums(args):
    return [float(x) for x in args]

@bot.command()
async def mean(ctx, *args):
    try:
        nums = parse_nums(args)
        result = statistics.mean(nums)
        e = numexa_embed("📊 Mean")
        e.add_field(name="Data",   value=f"`{nums}`",            inline=False)
        e.add_field(name="Mean",   value=f"`{round(result,6)}`", inline=True)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def median(ctx, *args):
    try:
        nums = parse_nums(args)
        result = statistics.median(nums)
        e = numexa_embed("📊 Median")
        e.add_field(name="Data",   value=f"`{sorted(nums)}`",   inline=False)
        e.add_field(name="Median", value=f"`{result}`",          inline=True)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def mode(ctx, *args):
    try:
        nums = parse_nums(args)
        result = statistics.multimode(nums)
        e = numexa_embed("📊 Mode")
        e.add_field(name="Data", value=f"`{nums}`",     inline=False)
        e.add_field(name="Mode", value=f"`{result}`",   inline=True)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def stddev(ctx, *args):
    try:
        nums = parse_nums(args)
        result = statistics.stdev(nums)
        e = numexa_embed("📊 Standard Deviation")
        e.add_field(name="Data",  value=f"`{nums}`",             inline=False)
        e.add_field(name="σ",     value=f"`{round(result,6)}`",  inline=True)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

@bot.command()
async def variance(ctx, *args):
    try:
        nums = parse_nums(args)
        result = statistics.variance(nums)
        e = numexa_embed("📊 Variance")
        e.add_field(name="Data",     value=f"`{nums}`",             inline=False)
        e.add_field(name="Variance", value=f"`{round(result,6)}`",  inline=True)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(f"❌ **Error:** `{err}`")

# ── Unit Conversion ────────────────────────────────────────────────
CONVERSIONS = {
    # length
    ("km",  "m"):   1000, ("m",  "km"):   0.001,
    ("m",   "cm"):  100,  ("cm", "m"):    0.01,
    ("m",   "mm"):  1000, ("mm", "m"):    0.001,
    ("mi",  "km"):  1.60934, ("km", "mi"): 0.62137,
    ("ft",  "m"):   0.3048,  ("m",  "ft"): 3.28084,
    ("in",  "cm"):  2.54,    ("cm", "in"): 0.39370,
    # mass
    ("kg",  "g"):   1000, ("g",  "kg"):   0.001,
    ("lb",  "kg"):  0.45359, ("kg", "lb"): 2.20462,
    ("oz",  "g"):   28.3495, ("g",  "oz"): 0.03527,
    # time
    ("h",   "min"): 60,   ("min", "h"):   1/60,
    ("min", "s"):   60,   ("s",   "min"): 1/60,
    ("h",   "s"):   3600, ("s",   "h"):   1/3600,
    ("day", "h"):   24,   ("h",   "day"): 1/24,
    # speed
    ("mph", "kmh"): 1.60934, ("kmh", "mph"): 0.62137,
    ("ms",  "kmh"): 3.6,     ("kmh", "ms"):  1/3.6,
    # temperature handled separately
    ("c", "f"): None, ("f", "c"): None, ("c", "k"): None, ("k", "c"): None,
}

@bot.command()
async def conv(ctx, value: float, from_unit: str, to_unit: str):
    fu, tu = from_unit.lower(), to_unit.lower()
    # temperature
    if fu == "c" and tu == "f":   result = value * 9/5 + 32
    elif fu == "f" and tu == "c": result = (value - 32) * 5/9
    elif fu == "c" and tu == "k": result = value + 273.15
    elif fu == "k" and tu == "c": result = value - 273.15
    elif fu == "f" and tu == "k": result = (value - 32) * 5/9 + 273.15
    elif fu == "k" and tu == "f": result = (value - 273.15) * 9/5 + 32
    elif (fu, tu) in CONVERSIONS:
        factor = CONVERSIONS[(fu, tu)]
        if factor is None:
            return await ctx.send(f"❌ Unsupported conversion: `{from_unit}` → `{to_unit}`")
        result = value * factor
    else:
        return await ctx.send(f"❌ Unknown conversion: `{from_unit}` → `{to_unit}`")

    e = numexa_embed("🔄 Unit Conversion")
    e.add_field(name="Input",  value=f"`{value} {from_unit}`",   inline=True)
    e.add_field(name="Output", value=f"`{round(result,6)} {to_unit}`", inline=True)
    await ctx.send(embed=e)


# ── Settings ───────────────────────────────────────────────────────
@bot.command()
@commands.has_permissions(administrator=True)
async def setprefix(ctx, prefix: str):
    if len(prefix) > 5:
        return await ctx.send("❌ Prefix must be 5 characters or fewer.")
    custom_prefixes[ctx.guild.id] = prefix
    data["prefixes"][str(ctx.guild.id)] = prefix
    save_data()
    await ctx.send(f"✅ Prefix set to `{prefix}`")

@bot.command()
async def anglemode(ctx, mode_str: str):
    m = mode_str.lower()
    if m not in ("deg", "rad"):
        return await ctx.send("❌ Use `deg` or `rad`.")
    angle_mode[ctx.author.id] = m
    data["angle"][str(ctx.author.id)] = m
    save_data()
    label = "Degrees 🔺" if m == "deg" else "Radians 〰️"
    await ctx.send(f"✅ Angle mode set to **{label}**")

@bot.command()
async def noprefix(ctx, member: discord.Member):
    if not is_owner(ctx.author.id):
        return await ctx.send("❌ Only the bot owner can use this command.")
    if member.id in no_prefix_users:
        no_prefix_users.discard(member.id)
        data["noprefix"] = list(no_prefix_users)
        save_data()
        await ctx.send(f"✅ Removed no-prefix from {member.mention}.")
    else:
        no_prefix_users.add(member.id)
        data["noprefix"] = list(no_prefix_users)
        save_data()
        await ctx.send(f"✅ {member.mention} can now use commands without a prefix.")

# ── Counting ───────────────────────────────────────────────────────
@bot.command()
@commands.has_permissions(administrator=True)
async def setcount(ctx):
    gid = str(ctx.guild.id)
    data["counting"][gid] = {"channel": ctx.channel.id, "current": 0, "last_user": None}
    save_data()
    await ctx.send(f"✅ Counting channel set to {ctx.channel.mention}. Start from **1**!")

@bot.command()
@commands.has_permissions(administrator=True)
async def resetcount(ctx):
    gid = str(ctx.guild.id)
    if gid in data["counting"]:
        data["counting"][gid]["current"]   = 0
        data["counting"][gid]["last_user"] = None
        save_data()
        await ctx.send("🔄 Count reset. Start again from **1**!")
    else:
        await ctx.send("❌ No counting channel set.")

# ── Utility ────────────────────────────────────────────────────────
@bot.command()
async def ping(ctx):
    e = numexa_embed("🏓 Pong!")
    e.add_field(name="Latency", value=f"`{round(bot.latency*1000)}ms`")
    await ctx.send(embed=e)

@bot.command()
async def stats(ctx):
    e = numexa_embed("📊 Numexa Stats")
    e.add_field(name="Servers",  value=f"`{len(bot.guilds)}`",                    inline=True)
    e.add_field(name="Users",    value=f"`{len(set(bot.get_all_members()))}`",     inline=True)
    e.add_field(name="Latency",  value=f"`{round(bot.latency*1000)}ms`",           inline=True)
    e.add_field(name="Uptime",   value=f"`{uptime_str()}`",                        inline=True)
    e.add_field(name="Library",  value=f"`discord.py {discord.__version__}`",      inline=True)
    await ctx.send(embed=e)

@bot.command()
async def serverinfo(ctx):
    g = ctx.guild
    e = numexa_embed(f"🏠 {g.name}")
    if g.icon: e.set_thumbnail(url=g.icon.url)
    e.add_field(name="Owner",    value=g.owner.mention,          inline=True)
    e.add_field(name="Members",  value=f"`{g.member_count}`",    inline=True)
    e.add_field(name="Channels", value=f"`{len(g.channels)}`",   inline=True)
    e.add_field(name="Roles",    value=f"`{len(g.roles)}`",      inline=True)
    e.add_field(name="Created",  value=f"<t:{int(g.created_at.timestamp())}:R>", inline=True)
    await ctx.send(embed=e)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = numexa_embed(f"👤 {member}")
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="ID",       value=f"`{member.id}`",   inline=True)
    e.add_field(name="Nickname", value=member.display_name, inline=True)
    e.add_field(name="Bot",      value="Yes" if member.bot else "No", inline=True)
    e.add_field(name="Joined",   value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    e.add_field(name="Created",  value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    e.add_field(name="Top Role", value=member.top_role.mention, inline=True)
    await ctx.send(embed=e)

# ── Links ──────────────────────────────────────────────────────────
@bot.command(name="help")
async def help_cmd(ctx):
    await ctx.send(embed=help_embed())

@bot.command()
async def support(ctx):
    e = numexa_embed("💬 Support Server")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Join Devzone", style=discord.ButtonStyle.link, url=DEVZONE_INVITE))
    await ctx.send(embed=e, view=v)

@bot.command()
async def dashboard(ctx):
    e = numexa_embed("🧠 Numexa Dashboard")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Open Dashboard", style=discord.ButtonStyle.link, url=DASHBOARD_URL))
    await ctx.send(embed=e, view=v)

@bot.command(name="invite")
async def invite_cmd(ctx):
    e = numexa_embed("👋 Invite Numexa")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Add Numexa", style=discord.ButtonStyle.link, url=INVITE_URL))
    await ctx.send(embed=e, view=v)


# ═══════════════════════ SLASH COMMANDS ═══════════════════════════

@bot.tree.command(name="calc",      description="Evaluate a math expression")
async def slash_calc(i: discord.Interaction, expr: str):
    try:
        result = safe_eval(expr, i.user.id)
        await i.response.send_message(embed=fmt_result(expr, result))
    except Exception as err:
        await i.response.send_message(f"❌ `{err}`", ephemeral=True)

@bot.tree.command(name="ui",        description="Open the interactive button calculator")
async def slash_ui(i: discord.Interaction):
    mode = angle_mode.get(i.user.id, "rad").upper()
    await i.response.send_message(f"```\n0\n```*Mode: **{mode}***", view=CalculatorView(i.user.id))

@bot.tree.command(name="diff",      description="Differentiate an expression w.r.t. x")
async def slash_diff(i: discord.Interaction, expr: str):
    try:
        result = sp.diff(sp.sympify(expr), x)
        e = numexa_embed("📐 Derivative")
        e.add_field(name="f(x)",  value=f"```{expr}```",   inline=False)
        e.add_field(name="f′(x)", value=f"```{result}```", inline=False)
        await i.response.send_message(embed=e)
    except Exception as err:
        await i.response.send_message(f"❌ `{err}`", ephemeral=True)

@bot.tree.command(name="integrate", description="Integrate an expression w.r.t. x")
async def slash_integrate(i: discord.Interaction, expr: str):
    try:
        result = sp.integrate(sp.sympify(expr), x)
        e = numexa_embed("∫ Integral")
        e.add_field(name="f(x)",    value=f"```{expr}```",        inline=False)
        e.add_field(name="∫f(x)dx", value=f"```{result} + C```",  inline=False)
        await i.response.send_message(embed=e)
    except Exception as err:
        await i.response.send_message(f"❌ `{err}`", ephemeral=True)

@bot.tree.command(name="dsolve",    description="Solve a differential equation")
async def slash_dsolve(i: discord.Interaction, eq: str):
    try:
        result = sp.dsolve(sp.sympify(eq))
        e = numexa_embed("🔬 ODE Solution")
        e.add_field(name="Equation", value=f"```{eq}```",      inline=False)
        e.add_field(name="Solution", value=f"```{result}```",  inline=False)
        await i.response.send_message(embed=e)
    except Exception as err:
        await i.response.send_message(f"❌ `{err}`", ephemeral=True)

@bot.tree.command(name="limit",     description="Compute a limit as x approaches a point")
async def slash_limit(i: discord.Interaction, expr: str, point: str = "0"):
    try:
        result = sp.limit(sp.sympify(expr), x, sp.sympify(point))
        e = numexa_embed("🔢 Limit")
        e.add_field(name="Expression",   value=f"```{expr}```",   inline=False)
        e.add_field(name=f"lim x→{point}", value=f"```{result}```", inline=False)
        await i.response.send_message(embed=e)
    except Exception as err:
        await i.response.send_message(f"❌ `{err}`", ephemeral=True)

@bot.tree.command(name="taylor",    description="Compute Taylor series expansion")
async def slash_taylor(i: discord.Interaction, expr: str, n: int = 5):
    try:
        result = sp.series(sp.sympify(expr), x, 0, n)
        e = numexa_embed("📈 Taylor Series")
        e.add_field(name="f(x)", value=f"```{expr}```",                    inline=False)
        e.add_field(name=f"{n} terms", value=f"```{result}```",            inline=False)
        await i.response.send_message(embed=e)
    except Exception as err:
        await i.response.send_message(f"❌ `{err}`", ephemeral=True)

@bot.tree.command(name="simplify",  description="Simplify a mathematical expression")
async def slash_simplify(i: discord.Interaction, expr: str):
    try:
        result = sp.simplify(sp.sympify(expr))
        await i.response.send_message(embed=fmt_result(expr, result, "✏️ Simplified"))
    except Exception as err:
        await i.response.send_message(f"❌ `{err}`", ephemeral=True)

@bot.tree.command(name="expand",    description="Expand a mathematical expression")
async def slash_expand(i: discord.Interaction, expr: str):
    try:
        result = sp.expand(sp.sympify(expr))
        await i.response.send_message(embed=fmt_result(expr, result, "📤 Expanded"))
    except Exception as err:
        await i.response.send_message(f"❌ `{err}`", ephemeral=True)

@bot.tree.command(name="solve",     description="Solve equation = 0 for x")
async def slash_solve(i: discord.Interaction, expr: str):
    try:
        result = sp.solve(sp.sympify(expr), x)
        e = numexa_embed("🔍 Solve for x")
        e.add_field(name="Equation",  value=f"```{expr} = 0```", inline=False)
        e.add_field(name="Solutions", value=f"```{result}```",    inline=False)
        await i.response.send_message(embed=e)
    except Exception as err:
        await i.response.send_message(f"❌ `{err}`", ephemeral=True)

@bot.tree.command(name="factor",    description="Prime factorisation of an integer")
async def slash_factor(i: discord.Interaction, n: int):
    try:
        result = sp.factorint(n)
        formatted = " × ".join([f"{p}^{e}" if e > 1 else str(p) for p, e in result.items()])
        e = numexa_embed("🔳 Prime Factorisation")
        e.add_field(name="Number", value=f"`{n}`",           inline=True)
        e.add_field(name="Result", value=f"`{formatted}`",   inline=True)
        await i.response.send_message(embed=e)
    except Exception as err:
        await i.response.send_message(f"❌ `{err}`", ephemeral=True)

@bot.tree.command(name="gcd",       description="Greatest common divisor of two numbers")
async def slash_gcd(i: discord.Interaction, a: int, b: int):
    await i.response.send_message(embed=fmt_result(f"gcd({a},{b})", str(math.gcd(a,b)), "🔢 GCD"))

@bot.tree.command(name="lcm",       description="Least common multiple of two numbers")
async def slash_lcm(i: discord.Interaction, a: int, b: int):
    await i.response.send_message(embed=fmt_result(f"lcm({a},{b})", str(math.lcm(a,b)), "🔢 LCM"))

@bot.tree.command(name="ncr",       description="Combinations: C(n, r)")
async def slash_ncr(i: discord.Interaction, n: int, r: int):
    await i.response.send_message(embed=fmt_result(f"C({n},{r})", str(math.comb(n,r)), "🎲 Combinations"))

@bot.tree.command(name="npr",       description="Permutations: P(n, r)")
async def slash_npr(i: discord.Interaction, n: int, r: int):
    await i.response.send_message(embed=fmt_result(f"P({n},{r})", str(math.perm(n,r)), "🎲 Permutations"))

@bot.tree.command(name="factorial", description="Factorial: n!")
async def slash_factorial(i: discord.Interaction, n: int):
    if n > 1000:
        return await i.response.send_message("❌ Too large (max 1000).", ephemeral=True)
    await i.response.send_message(embed=fmt_result(f"{n}!", str(math.factorial(n)), "❗ Factorial"))

@bot.tree.command(name="conv",      description="Unit conversion (e.g. 5 km m)")
async def slash_conv(i: discord.Interaction, value: float, from_unit: str, to_unit: str):
    ctx_like = type('', (), {'send': i.response.send_message, 'author': i.user})()
    fu, tu = from_unit.lower(), to_unit.lower()
    if fu == "c" and tu == "f":   result = value * 9/5 + 32
    elif fu == "f" and tu == "c": result = (value - 32) * 5/9
    elif fu == "c" and tu == "k": result = value + 273.15
    elif fu == "k" and tu == "c": result = value - 273.15
    elif (fu, tu) in CONVERSIONS:
        factor = CONVERSIONS[(fu, tu)]
        if factor is None:
            return await i.response.send_message(f"❌ Unsupported conversion.", ephemeral=True)
        result = value * factor
    else:
        return await i.response.send_message(f"❌ Unknown conversion `{from_unit}` → `{to_unit}`", ephemeral=True)
    e = numexa_embed("🔄 Unit Conversion")
    e.add_field(name="Input",  value=f"`{value} {from_unit}`",        inline=True)
    e.add_field(name="Output", value=f"`{round(result,6)} {to_unit}`", inline=True)
    await i.response.send_message(embed=e)

@bot.tree.command(name="ping",       description="Check latency")
async def slash_ping(i: discord.Interaction):
    e = numexa_embed("🏓 Pong!")
    e.add_field(name="Latency", value=f"`{round(bot.latency*1000)}ms`")
    await i.response.send_message(embed=e)

@bot.tree.command(name="stats",      description="Bot statistics")
async def slash_stats(i: discord.Interaction):
    e = numexa_embed("📊 Numexa Stats")
    e.add_field(name="Servers",  value=f"`{len(bot.guilds)}`",                inline=True)
    e.add_field(name="Users",    value=f"`{len(set(bot.get_all_members()))}`", inline=True)
    e.add_field(name="Latency",  value=f"`{round(bot.latency*1000)}ms`",       inline=True)
    e.add_field(name="Uptime",   value=f"`{uptime_str()}`",                    inline=True)
    await i.response.send_message(embed=e)

@bot.tree.command(name="serverinfo", description="Server information")
async def slash_serverinfo(i: discord.Interaction):
    g = i.guild
    e = numexa_embed(f"🏠 {g.name}")
    if g.icon: e.set_thumbnail(url=g.icon.url)
    e.add_field(name="Owner",    value=g.owner.mention,          inline=True)
    e.add_field(name="Members",  value=f"`{g.member_count}`",    inline=True)
    e.add_field(name="Channels", value=f"`{len(g.channels)}`",   inline=True)
    e.add_field(name="Created",  value=f"<t:{int(g.created_at.timestamp())}:R>", inline=True)
    await i.response.send_message(embed=e)

@bot.tree.command(name="userinfo",   description="User information")
async def slash_userinfo(i: discord.Interaction, member: discord.Member = None):
    member = member or i.user
    e = numexa_embed(f"👤 {member}")
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="ID",       value=f"`{member.id}`",   inline=True)
    e.add_field(name="Nickname", value=member.display_name, inline=True)
    e.add_field(name="Top Role", value=member.top_role.mention, inline=True)
    await i.response.send_message(embed=e)

@bot.tree.command(name="setprefix",  description="Change server prefix (admin)")
async def slash_setprefix(i: discord.Interaction, prefix: str):
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message("❌ Administrator only.", ephemeral=True)
    if len(prefix) > 5:
        return await i.response.send_message("❌ Max 5 characters.", ephemeral=True)
    custom_prefixes[i.guild.id] = prefix
    data["prefixes"][str(i.guild.id)] = prefix
    save_data()
    await i.response.send_message(f"✅ Prefix set to `{prefix}`", ephemeral=True)

@bot.tree.command(name="anglemode",  description="Set trig angle unit (deg or rad)")
async def slash_anglemode(i: discord.Interaction, mode: str):
    m = mode.lower()
    if m not in ("deg", "rad"):
        return await i.response.send_message("❌ Use `deg` or `rad`.", ephemeral=True)
    angle_mode[i.user.id] = m
    data["angle"][str(i.user.id)] = m
    save_data()
    await i.response.send_message(f"✅ Angle mode: **{'Degrees' if m=='deg' else 'Radians'}**", ephemeral=True)

@bot.tree.command(name="noprefix",   description="Toggle no-prefix for a user (owner only)")
async def slash_noprefix(i: discord.Interaction, member: discord.Member):
    if not is_owner(i.user.id):
        return await i.response.send_message("❌ Owner only.", ephemeral=True)
    if member.id in no_prefix_users:
        no_prefix_users.discard(member.id)
        data["noprefix"] = list(no_prefix_users)
        save_data()
        await i.response.send_message(f"✅ Removed no-prefix from {member.mention}.", ephemeral=True)
    else:
        no_prefix_users.add(member.id)
        data["noprefix"] = list(no_prefix_users)
        save_data()
        await i.response.send_message(f"✅ {member.mention} can now use commands without prefix.", ephemeral=True)

@bot.tree.command(name="setcount",   description="Set counting channel (admin)")
async def slash_setcount(i: discord.Interaction):
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message("❌ Administrator only.", ephemeral=True)
    gid = str(i.guild.id)
    data["counting"][gid] = {"channel": i.channel.id, "current": 0, "last_user": None}
    save_data()
    await i.response.send_message(f"✅ Counting set to {i.channel.mention}. Start from **1**!", ephemeral=True)

@bot.tree.command(name="resetcount", description="Reset counting game (admin)")
async def slash_resetcount(i: discord.Interaction):
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message("❌ Administrator only.", ephemeral=True)
    gid = str(i.guild.id)
    if gid in data["counting"]:
        data["counting"][gid]["current"]   = 0
        data["counting"][gid]["last_user"] = None
        save_data()
        await i.response.send_message("🔄 Count reset. Start from **1**!", ephemeral=True)
    else:
        await i.response.send_message("❌ No counting channel set.", ephemeral=True)

@bot.tree.command(name="help",       description="Show all commands")
async def slash_help(i: discord.Interaction):
    await i.response.send_message(embed=help_embed(), ephemeral=True)

@bot.tree.command(name="invite",     description="Get the invite link")
async def slash_invite(i: discord.Interaction):
    e = numexa_embed("👋 Invite Numexa")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Add Numexa", style=discord.ButtonStyle.link, url=INVITE_URL))
    await i.response.send_message(embed=e, view=v, ephemeral=True)

@bot.tree.command(name="support",    description="Support server link")
async def slash_support(i: discord.Interaction):
    e = numexa_embed("💬 Support Server")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Join Devzone", style=discord.ButtonStyle.link, url=DEVZONE_INVITE))
    await i.response.send_message(embed=e, view=v, ephemeral=True)

@bot.tree.command(name="dashboard",  description="Open the web dashboard")
async def slash_dashboard(i: discord.Interaction):
    e = numexa_embed("🧠 Dashboard")
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Open Dashboard", style=discord.ButtonStyle.link, url=DASHBOARD_URL))
    await i.response.send_message(embed=e, view=v, ephemeral=True)


# ═════════════════════════ BOT EVENTS ═════════════════════════════

@bot.event
async def on_guild_join(guild):
    try:
        owner = guild.owner
        if not owner: return
        e = numexa_embed(
            "👋 Thanks for adding Numexa!",
            "🧮 Calculus · Matrix ops · Statistics · Counting game · Unit conversion\n"
            "⚙️ Use `!help` or `/help` to get started."
        )
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
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Bad argument: {error}")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        raise error

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    gid      = str(message.guild.id)
    counting = data["counting"].get(gid)

    if counting and message.channel.id == counting["channel"]:
        content     = message.content.strip()
        check_emoji = f"<:checkmark:{CHECK_EMOJI_ID}>"
        cross_emoji = f"<:wrong:{CROSS_EMOJI_ID}>"

        if not content.isdigit():
            counting["current"] = 0; counting["last_user"] = None; save_data()
            await message.add_reaction(cross_emoji)
            await message.channel.send(f"❌ {message.author.mention} broke the count! Only numbers. Start from **1**.", delete_after=8)
            await bot.process_commands(message); return

        number   = int(content)
        expected = counting["current"] + 1

        if counting.get("last_user") == message.author.id:
            counting["current"] = 0; counting["last_user"] = None; save_data()
            await message.add_reaction(cross_emoji)
            await message.channel.send(f"❌ {message.author.mention} can't count twice in a row! Start from **1**.", delete_after=8)
            await bot.process_commands(message); return

        if number != expected:
            counting["current"] = 0; counting["last_user"] = None; save_data()
            await message.add_reaction(cross_emoji)
            await message.channel.send(f"❌ {message.author.mention} said **{number}** but expected **{expected}**! Start from **1**.", delete_after=8)
            await bot.process_commands(message); return

        counting["current"] = number; counting["last_user"] = message.author.id; save_data()
        await message.add_reaction(check_emoji)

    await bot.process_commands(message)

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
    bot.loop.create_task(status_loop())
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    print(f"   Guilds: {len(bot.guilds)}")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set.")

bot.run(TOKEN)
