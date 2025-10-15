import os
import sqlite3
from discord.ext import commands

# Diretório persistente para banco de dados
BASE_DIR = os.path.expanduser("~/.dicebot_data")
os.makedirs(BASE_DIR, exist_ok=True)
DB_PATH = os.path.join(BASE_DIR, "dice_styles.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_styles (
    guild_id    INTEGER,
    user_id     INTEGER,
    color       TEXT,
    emoji       TEXT,
    PRIMARY KEY (guild_id, user_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_range_styles (
    guild_id    INTEGER,
    user_id     INTEGER,
    range_name  TEXT,
    color       TEXT,
    emoji       TEXT,
    PRIMARY KEY (guild_id, user_id, range_name)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_range_mode (
    guild_id    INTEGER,
    user_id     INTEGER,
    use_range   INTEGER DEFAULT 1,
    PRIMARY KEY (guild_id, user_id)
)
''')

conn.commit()

def get_user_style(guild_id, user_id):
    cursor.execute('''
        SELECT color, emoji
        FROM user_styles
        WHERE guild_id = ? AND user_id = ?
    ''', (guild_id, user_id))
    return cursor.fetchone()


def set_user_style(guild_id, user_id, color, emoji):
    cursor.execute('''
    INSERT INTO user_styles (guild_id, user_id, color, emoji)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(guild_id,user_id) DO UPDATE SET
        color = excluded.color,
        emoji = excluded.emoji
    ''', (guild_id, user_id, color, emoji))
    conn.commit()

def get_user_range_style(guild_id, user_id, range_name):
    cursor.execute('''
        SELECT color, emoji
        FROM user_range_styles
        WHERE guild_id = ? AND user_id = ? AND range_name = ?
    ''', (guild_id, user_id, range_name))
    return cursor.fetchone()

def set_user_range_style(guild_id, user_id, range_name, color, emoji):
    cursor.execute('''
    INSERT INTO user_range_styles (guild_id, user_id, range_name, color, emoji)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(guild_id,user_id,range_name) DO UPDATE SET
        color = excluded.color,
        emoji = excluded.emoji
    ''', (guild_id, user_id, range_name, color, emoji))
    conn.commit()

def get_user_range_mode(guild_id, user_id):
    cursor.execute('''
        SELECT use_range
        FROM user_range_mode
        WHERE guild_id = ? AND user_id = ?
    ''', (guild_id, user_id))
    row = cursor.fetchone()
    if row is None:
        # padrão True (usa range)
        return True
    return bool(row[0])

def set_user_range_mode(guild_id, user_id, use_range: bool):
    val = 1 if use_range else 0
    cursor.execute('''
    INSERT INTO user_range_mode (guild_id, user_id, use_range)
    VALUES (?, ?, ?)
    ON CONFLICT(guild_id,user_id) DO UPDATE SET
        use_range = excluded.use_range
    ''', (guild_id, user_id, val))
    conn.commit()

class DiceStyle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='setdice', invoke_without_command=True)
    async def setdice(self, ctx, color: str = None, emoji: str = None):
        # Se chamado sem argumentos, mostra ajuda ou erro
        if color is None or emoji is None:
            return await ctx.send("Use !setdice <hex> <emoji|url> para definir cor e emoji padrão.", delete_after=15)

        guild_id = ctx.guild.id
        user_id = ctx.author.id

        if len(color) != 6 or any(c not in "0123456789abcdefABCDEF" for c in color):
            return await ctx.send("Hex inválido. Use 6 dígitos, ex: FF00AA.", delete_after=15)

        store = f"url:{emoji}" if emoji.startswith(("http://", "https://")) else emoji
        set_user_style(guild_id, user_id, color.upper(), store)
        await ctx.send(f"Estilo padrão salvo: `#{color.upper()}` {emoji}", delete_after=15)

    @setdice.command(name='color')
    async def setdice_color(self, ctx, color: str):
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        if len(color) != 6 or any(c not in "0123456789abcdefABCDEF" for c in color):
            return await ctx.send("Hex inválido. Use 6 dígitos, ex: 00FF00.", delete_after=15)
        row = get_user_style(guild_id, user_id)
        raw = row[1] if row else "🎲"
        set_user_style(guild_id, user_id, color.upper(), raw)
        await ctx.send(f"Cor padrão salva: `#{color.upper()}`", delete_after=15)

    @setdice.command(name='emoji')
    async def setdice_emoji(self, ctx, emoji: str):
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        row = get_user_style(guild_id, user_id)
        color = row[0] if row else "FFD700"
        store = f"url:{emoji}" if emoji.startswith(("http://", "https://")) else emoji
        set_user_style(guild_id, user_id, color, store)
        await ctx.send(f"Emoji/url padrão salvo: {emoji}", delete_after=15)

    @setdice.group(name='range', invoke_without_command=True)
    async def setdice_range(self, ctx, range_name: str = None, color: str = None, emoji: str = None):
        if range_name is None or color is None or emoji is None:
            return await ctx.send("Use: !setdice range <low|medium|high|critical|Lcritical> <hex> <emoji|url>", delete_after=15)

        guild_id = ctx.guild.id
        user_id = ctx.author.id
        valid = ['Lcritical', 'low', 'medium', 'high', 'critical']
        if range_name not in valid:
            return await ctx.send(f"Ranges válidas: {', '.join(valid)}", delete_after=15)
        if len(color) != 6 or any(c not in "0123456789abcdefABCDEF" for c in color):
            return await ctx.send("Hex inválido. Use 6 dígitos, ex: 00FF00.", delete_after=15)

        store = f"url:{emoji}" if emoji.startswith(("http://", "https://")) else emoji
        set_user_range_style(guild_id, user_id, range_name, color.upper(), store)
        await ctx.send(f"Estilo `{range_name}` salvo: `#{color.upper()}` {emoji}", delete_after=15)

    @setdice_range.command(name='color')
    async def range_color(self, ctx, range_name: str, color: str):
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        valid = ['Lcritical', 'low', 'medium', 'high', 'critical']
        if range_name not in valid:
            return await ctx.send(f"Ranges válidas: {', '.join(valid)}", delete_after=15)
        if len(color) != 6 or any(c not in "0123456789abcdefABCDEF" for c in color):
            return await ctx.send("Hex inválido. Use 6 dígitos, ex: 440000.", delete_after=15)
        row = get_user_range_style(guild_id, user_id, range_name)
        raw = row[1] if row else None
        if raw is None:
            return await ctx.send(f"Nenhum estilo definido ainda para `{range_name}`.", delete_after=15)
        set_user_range_style(guild_id, user_id, range_name, color.upper(), raw)
        await ctx.send(f"Cor do range `{range_name}` salva: `#{color.upper()}`", delete_after=15)

    @setdice_range.command(name='emoji')
    async def range_emoji(self, ctx, range_name: str, emoji: str):
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        valid = ['Lcritical', 'low', 'medium', 'high', 'critical']
        if range_name not in valid:
            return await ctx.send(f"Ranges válidas: {', '.join(valid)}", delete_after=15)
        row = get_user_range_style(guild_id, user_id, range_name)
        color = row[0] if row else None
        if color is None:
            return await ctx.send(f"Nenhum estilo definido ainda para `{range_name}`.", delete_after=15)
        store = f"url:{emoji}" if emoji.startswith(("http://", "https://")) else emoji
        set_user_range_style(guild_id, user_id, range_name, color, store)
        await ctx.send(f"Emoji/url do range `{range_name}` salvo: {emoji}", delete_after=15)

    @setdice.command(name='mode')
    async def setdice_mode(self, ctx, mode: str = None):
        """!setdice mode [range|default] - Consulta ou altera modo de estilo"""
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        if mode is None:
            use_range = get_user_range_mode(guild_id, user_id)
            await ctx.send(f"Modo atual: {'range (estilo por faixa)' if use_range else 'default (estilo fixo)'}.", delete_after=30)
            return

        mode = mode.lower()
        if mode not in ['range', 'default']:
            return await ctx.send("Modo inválido. Use 'range' ou 'default'.", delete_after=15)

        use_range = (mode == 'range')
        set_user_range_mode(guild_id, user_id, use_range)
        await ctx.send(f"Modo alterado para: {'range (estilo por faixa)' if use_range else 'default (estilo fixo)'}", delete_after=15)
    @setdice.command(name='import')
    async def setdice_import(self, ctx, guild_id: str = None):
        """!setdice import [guild_id] - Importa tabela existente de outro serviidor"""
        user_id = ctx.author.id
        current_guild_id = ctx.guild.id
        if guild_id is None:
            await ctx.send("ID inválido.", delete_after=15)
            return 
        try:
            style = get_user_style(guild_id, user_id)
            color, emoji = style
            set_user_style(current_guild_id, user_id, color, emoji)
            range_valid = ['Lcritical', 'low', 'medium', 'high', 'critical']
            for range_name in range_valid:
                range = get_user_range_style(guild_id, user_id, range_name)
                color, emoji = range
                set_user_range_style(current_guild_id, user_id, range_name, color, emoji)
            await ctx.send(f"Tabelas Importadas", delete_after=15)
        except Exception:
            return await ctx.send(f"Não existem tabelas", delete_after=15) 


async def setup(bot):
    await bot.add_cog(DiceStyle(bot))