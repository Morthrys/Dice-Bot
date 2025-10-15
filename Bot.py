import asyncio
import discord
from discord.ext import commands
from discord import Colour, Embed
import random
import re
from dicestyle import (
    setup as setup_styles,
    get_user_style,
    get_user_range_style
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

RANGE_STYLES = {
    'Lcritical': {'color': Colour.dark_blue(),  'emoji': '💀', 'thumb': None},
    'low':       {'color': Colour.dark_red(),   'emoji': '😞', 'thumb': None},
    'medium':    {'color': Colour.orange(),     'emoji': '🙂', 'thumb': None},
    'high':      {'color': Colour.green(),      'emoji': '😃', 'thumb': None},
    'critical':  {'color': Colour.gold(),       'emoji': '💥', 'thumb': None},
}

def roll_dice_term(term: str):
    num_str, die_str = term.split('d')
    num = int(num_str) if num_str else 1
    die = int(die_str)
    rolls = [random.randint(1, die) for _ in range(num)]
    subtotal = sum(rolls)
    return subtotal, rolls, num, die

def parse_complex_expression(expr: str):
    expr = expr.lower().replace(' ', '').replace(',', '.')
    dice_repls = {}
    all_rolls = []

    def dice_repl(m):
        term = m.group(0)
        subtotal, rolls, num, die = roll_dice_term(term)
        dice_repls[term] = (rolls, num, die, subtotal)
        all_rolls.append((rolls, num, die))
        return str(subtotal)

    expr_sub = re.sub(r'\d*d\d+', dice_repl, expr)

    try:
        total = eval(expr_sub, {"__builtins__": None}, {})
    except Exception:
        total = None

    # Reconstruir expressão com rolagens + modificadores
    desc_parts = []
    i = 0
    while i < len(expr):
        m = re.match(r'\d*d\d+', expr[i:])
        if m:
            term = m.group(0)
            rolls, num, die, subtotal = dice_repls[term]
            rolls_fmt = ', '.join(
                f"**{r}**" if r == 1 or r == die else str(r)
                for r in rolls
            )
            # colchetes grudados no dado
            desc_parts.append(f"[{rolls_fmt}] {num}d{die}")
            i += len(term)
        else:
            ch = expr[i]
            # operadores com espaçamento
            if ch in "+-*/":
                desc_parts.append(f" {ch} ")
            else:
                desc_parts.append(ch)
            i += 1

    desc = f"`{total}` ⟵ " + "".join(desc_parts)

    return total, desc, all_rolls

def get_range_name(pure_roll: int, min_possible: int, max_possible: int):
    if pure_roll == min_possible:
        return 'Lcritical'
    if pure_roll == max_possible:
        return 'critical'
    if max_possible == min_possible:
        percent = 100
    else:
        percent = (pure_roll - min_possible) / (max_possible - min_possible) * 100
    if percent >= 61:
        return 'high'
    if percent >= 40:
        return 'medium'
    return 'low'

def is_valid_dice_expr(content: str):
    # Aceita a/A prefixo e termos dados + operadores e parênteses
    pattern = re.compile(r"^[aA]?[\d\s+#d\+\-\*/().]+$")
    # Deve conter pelo menos um dado válido
    if not re.search(r'\d*d\d+', content.lower()):
        return False
    return bool(pattern.fullmatch(content.strip()))

def is_math_expression(content: str):
    pattern = re.compile(r'^[\d\s+\-*/().]+$')
    if not pattern.fullmatch(content.strip()):
        return False
    if not re.search(r'[+\-*/]', content):
        return False
    return True

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip().replace(',', '.')
    if content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    ctx = await bot.get_context(message)
    if ctx.command:
        await bot.process_commands(message)
        return

    expr = content.lower()
    rolls = 1

    # Extrair prefixo múltiplas rolagens: a3# ou 3#
    m_prefix = re.match(r'^(a?\d+)#(.+)', expr)
    if m_prefix:
        prefix = m_prefix.group(1)
        expr = m_prefix.group(2).strip()
        if prefix.startswith('a'):
            prefix = prefix[1:]
        if prefix.isdigit():
            rolls = int(prefix)

    # Se o expr ainda começar com 'a' removemos só uma vez (ex: a3d20)
    if expr.startswith('a'):
        expr = expr[1:]

    if is_valid_dice_expr(expr):
        all_totals = []
        all_descs = []
        all_dice_rolls = []

        for _ in range(rolls):
            total, desc, dice_rolls = parse_complex_expression(expr)
            if total is None:
                return
            all_totals.append(total)
            all_descs.append(desc)
            all_dice_rolls.append(dice_rolls)

        first_rolls = all_dice_rolls[0] if all_dice_rolls else []

        min_possible = sum(num for _, num, _ in first_rolls)
        max_possible = sum(num * die for _, num, die in first_rolls)

        pure_total = 0
        for rolls_, num_, die_ in first_rolls:
            pure_total += sum(rolls_)

        rn = get_range_name(pure_total, min_possible, max_possible)

        custom = get_user_range_style(message.guild.id, message.author.id, rn)
        if custom:
            col_text, emo = custom
            color = Colour(int(col_text, 16))
            if emo.startswith("url:"):
                emoji = None
                thumb = emo[4:]
            else:
                emoji = emo
                thumb = None
        else:
            style = RANGE_STYLES[rn]
            color, emoji, thumb = style['color'], style['emoji'], style['thumb']

        title = f"{(emoji + ' ') if emoji else ''}{message.author.display_name} rolou"
        description = "\n".join(all_descs)
        embed = Embed(title=title, description=description, color=color)
        if thumb:
            embed.set_thumbnail(url=thumb)

        await message.reply(embed=embed)
        return

    if is_math_expression(content):
        try:
            total = eval(content, {"__builtins__": None}, {})
        except Exception:
            return

        row = get_user_style(message.guild.id, message.author.id)
        if row:
            col_text, raw = row
            color = Colour(int(col_text, 16))
            if raw.startswith("url:"):
                emoji = None
                thumb = raw[4:]
            else:
                emoji = raw
                thumb = None
        else:
            color, emoji, thumb = Colour.dark_blue(), "🧮", None

        formatted_expr = re.sub(r'(?<=[^\s])([+\-*/])(?=[^\s])', r' \1 ', content)
        desc = f"`{total}` ⟵ {formatted_expr}"

        title = f"{(emoji + ' ') if emoji else ''}{message.author.display_name}"
        embed = Embed(title=title, description=desc, color=color)
        if thumb:
            embed.set_thumbnail(url=thumb)

        await message.reply(embed=embed)
        return

    await bot.process_commands(message)

async def main():
    async with bot:
        await bot.load_extension('dicestyle')
        await bot.start('TOKEN BOT') # Substitua pelo Token do seu Bot

if __name__ == "__main__":
    asyncio.run(main())