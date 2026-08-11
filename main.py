import os
import re
import time
import sqlite3
import secrets
import asyncio

import discord
from discord import app_commands
from discord.ext import commands, tasks


TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DATABASE = "ps99reader.db"

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS mod_roles (
                guild_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                UNIQUE(guild_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS wheels (
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                option TEXT NOT NULL,
                weight REAL NOT NULL,
                UNIQUE(guild_id, name, option)
            );

            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER DEFAULT 0,
                prize TEXT NOT NULL,
                end_ts INTEGER NOT NULL,
                ended INTEGER DEFAULT 0,
                winner_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS entrants (
                giveaway_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                UNIQUE(giveaway_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_ts INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS usage (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                count INTEGER DEFAULT 0,
                UNIQUE(guild_id, user_id)
            );
            """
        )


def add_usage(interaction: discord.Interaction):
    if not interaction.guild_id:
        return

    with get_db() as db:
        db.execute(
            """
            INSERT INTO usage(guild_id, user_id, count)
            VALUES (?, ?, 1)
            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET count = count + 1
            """,
            (interaction.guild_id, interaction.user.id),
        )


def owner_or_admin(member: discord.Member):
    return (
        member.id == member.guild.owner_id
        or member.guild_permissions.administrator
    )


def staff_allowed(member: discord.Member):
    if member.id == member.guild.owner_id:
        return True

    if member.guild_permissions.administrator:
        return True

    if member.guild_permissions.manage_guild:
        return True

    with get_db() as db:
        rows = db.execute(
            "SELECT role_id FROM mod_roles WHERE guild_id = ?",
            (member.guild.id,),
        ).fetchall()

    allowed_roles = {row["role_id"] for row in rows}

    return any(role.id in allowed_roles for role in member.roles)


async def require_staff(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command can only be used inside a server.",
            ephemeral=True,
        )
        return False

    if not isinstance(interaction.user, discord.Member):
        return False

    if not staff_allowed(interaction.user):
        await interaction.response.send_message(
            "You do not have permission to use this command.",
            ephemeral=True,
        )
        return False

    return True


# PS99 LIVE DATA
# No fake prices are used.
# A real PS99 API/provider can be connected here later.

async def ps99_lookup(name: str):
    return None


async def unavailable_value(interaction: discord.Interaction, name: str):
    add_usage(interaction)

    await interaction.response.defer()

    result = await ps99_lookup(name)

    if result is None:
        await interaction.followup.send(
            "Live PS99 data is currently unavailable."
        )
        return


@bot.tree.command(name="ping", description="Check if the bot is online")
async def ping(interaction: discord.Interaction):
    add_usage(interaction)

    await interaction.response.send_message(
        f"Pong! `{round(bot.latency * 1000)} ms`"
    )


@bot.tree.command(name="help", description="Show all bot commands")
async def help_command(interaction: discord.Interaction):
    add_usage(interaction)

    embed = discord.Embed(
        title="Ps99reader Commands",
        description="Available commands",
    )

    embed.add_field(
        name="PS99",
        value=(
            "`/value`\n"
            "`/item`\n"
            "`/rap`\n"
            "`/search`\n"
            "`/trade`\n"
            "`/chance`"
        ),
        inline=True,
    )

    embed.add_field(
        name="Wheel",
        value=(
            "`/addwheel`\n"
            "`/spin`\n"
            "`/wheelshow`\n"
            "`/wheelremove`\n"
            "`/wheelreset`"
        ),
        inline=True,
    )

    embed.add_field(
        name="Giveaways",
        value=(
            "`/giveaway`\n"
            "`/reroll`"
        ),
        inline=True,
    )

    embed.add_field(
        name="Admin",
        value=(
            "`/modrole add`\n"
            "`/modrole remove`\n"
            "`/modrole list`"
        ),
        inline=True,
    )

    embed.add_field(
        name="Community",
        value=(
            "`/suggest`\n"
            "`/leaderboard`\n"
            "`/ping`"
        ),
        inline=True,
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="value", description="Check the value of a PS99 pet")
@app_commands.describe(pet="Pet name")
async def value(interaction: discord.Interaction, pet: str):
    await unavailable_value(interaction, pet)


@bot.tree.command(name="item", description="Check the value of a PS99 item")
@app_commands.describe(item="Item name")
async def item(interaction: discord.Interaction, item: str):
    await unavailable_value(interaction, item)


@bot.tree.command(name="rap", description="Check RAP for a PS99 pet or item")
@app_commands.describe(name="Pet or item name")
async def rap(interaction: discord.Interaction, name: str):
    await unavailable_value(interaction, name)


@bot.tree.command(name="search", description="Search for a PS99 pet or item")
@app_commands.describe(name="Full or partial name")
async def search(interaction: discord.Interaction, name: str):
    await unavailable_value(interaction, name)


@bot.tree.command(name="trade", description="Compare both sides of a PS99 trade")
@app_commands.describe(
    your_items="Your pets/items separated by commas",
    their_items="Their pets/items separated by commas",
)
async def trade(
    interaction: discord.Interaction,
    your_items: str,
    their_items: str,
):
    add_usage(interaction)

    await interaction.response.send_message(
        "Live PS99 data is currently unavailable. "
        "Trade results are disabled instead of using fake values.",
        ephemeral=True,
    )


@bot.tree.command(name="chance", description="Calculate a percentage chance")
@app_commands.describe(
    successful="Number of successful outcomes",
    total="Total number of outcomes",
)
async def chance(
    interaction: discord.Interaction,
    successful: int,
    total: int,
):
    add_usage(interaction)

    if total <= 0:
        await interaction.response.send_message(
            "Total must be greater than 0.",
            ephemeral=True,
        )
        return

    if successful < 0 or successful > total:
        await interaction.response.send_message(
            "Invalid numbers.",
            ephemeral=True,
        )
        return

    percentage = successful / total * 100

    await interaction.response.send_message(
        f"Chance: **{percentage:.2f}%**"
    )


modrole = app_commands.Group(
    name="modrole",
    description="Manage bot moderator roles",
)


@modrole.command(name="add", description="Add a moderator role")
async def modrole_add(
    interaction: discord.Interaction,
    role: discord.Role,
):
    if (
        not interaction.guild
        or not isinstance(interaction.user, discord.Member)
        or not owner_or_admin(interaction.user)
    ):
        await interaction.response.send_message(
            "Only the server owner or administrators can use this.",
            ephemeral=True,
        )
        return

    with get_db() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO mod_roles(guild_id, role_id)
            VALUES (?, ?)
            """,
            (interaction.guild.id, role.id),
        )

    await interaction.response.send_message(
        f"{role.mention} was added as a bot moderator role.",
        ephemeral=True,
    )


@modrole.command(name="remove", description="Remove a moderator role")
async def modrole_remove(
    interaction: discord.Interaction,
    role: discord.Role,
):
    if (
        not interaction.guild
        or not isinstance(interaction.user, discord.Member)
        or not owner_or_admin(interaction.user)
    ):
        await interaction.response.send_message(
            "Only the server owner or administrators can use this.",
            ephemeral=True,
        )
        return

    with get_db() as db:
        db.execute(
            """
            DELETE FROM mod_roles
            WHERE guild_id = ? AND role_id = ?
            """,
            (interaction.guild.id, role.id),
        )

    await interaction.response.send_message(
        f"{role.mention} was removed.",
        ephemeral=True,
    )


@modrole.command(name="list", description="Show configured moderator roles")
async def modrole_list(interaction: discord.Interaction):
    if (
        not interaction.guild
        or not isinstance(interaction.user, discord.Member)
        or not owner_or_admin(interaction.user)
    ):
        await interaction.response.send_message(
            "Only the server owner or administrators can use this.",
            ephemeral=True,
        )
        return

    with get_db() as db:
        rows = db.execute(
            """
            SELECT role_id
            FROM mod_roles
            WHERE guild_id = ?
            """,
            (interaction.guild.id,),
        ).fetchall()

    if not rows:
        text = "No moderator roles configured."
    else:
        text = "\n".join(
            f"<@&{row['role_id']}>"
            for row in rows
        )

    await interaction.response.send_message(
        text,
        ephemeral=True,
    )


bot.tree.add_command(modrole)


@bot.tree.command(name="addwheel", description="Add an option to a prize wheel")
@app_commands.describe(
    name="Wheel name",
    option="Prize or option",
    weight="Chance weight",
)
async def addwheel(
    interaction: discord.Interaction,
    name: str,
    option: str,
    weight: float,
):
    if not await require_staff(interaction):
        return

    if weight <= 0:
        await interaction.response.send_message(
            "Weight must be greater than 0.",
            ephemeral=True,
        )
        return

    with get_db() as db:
        db.execute(
            """
            INSERT INTO wheels(guild_id, name, option, weight)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, name, option)
            DO UPDATE SET weight = excluded.weight
            """,
            (
                interaction.guild.id,
                name.lower(),
                option,
                weight,
            ),
        )

    await interaction.response.send_message(
        f"Added **{option}** to wheel **{name}**.",
        ephemeral=True,
    )


@bot.tree.command(name="wheelshow", description="Show a saved wheel")
async def wheelshow(
    interaction: discord.Interaction,
    name: str,
):
    if not await require_staff(interaction):
        return

    with get_db() as db:
        rows = db.execute(
            """
            SELECT option, weight
            FROM wheels
            WHERE guild_id = ? AND name = ?
            """,
            (
                interaction.guild.id,
                name.lower(),
            ),
        ).fetchall()

    if not rows:
        await interaction.response.send_message(
            "Wheel not found.",
            ephemeral=True,
        )
        return

    total = sum(float(row["weight"]) for row in rows)

    lines = []

    for row in rows:
        percentage = float(row["weight"]) / total * 100

        lines.append(
            f"**{row['option']}** | "
            f"Weight: `{row['weight']:g}` | "
            f"Chance: `{percentage:.2f}%`"
        )

    embed = discord.Embed(
        title=f"Wheel: {name}",
        description="\n".join(lines),
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="spin", description="Spin a saved prize wheel")
async def spin(
    interaction: discord.Interaction,
    name: str,
):
    if not await require_staff(interaction):
        return

    with get_db() as db:
        rows = db.execute(
            """
            SELECT option, weight
            FROM wheels
            WHERE guild_id = ? AND name = ?
            """,
            (
                interaction.guild.id,
                name.lower(),
            ),
        ).fetchall()

    if not rows:
        await interaction.response.send_message(
            "Wheel not found.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        "Spinning the wheel..."
    )

    await asyncio.sleep(1)

    await interaction.edit_original_response(
        content="3..."
    )

    await asyncio.sleep(0.7)

    await interaction.edit_original_response(
        content="2..."
    )

    await asyncio.sleep(0.7)

    await interaction.edit_original_response(
        content="1..."
    )

    await asyncio.sleep(0.7)

    total_weight = sum(
        float(row["weight"])
        for row in rows
    )

    random_number = (
        secrets.SystemRandom().random()
        * total_weight
    )

    current = 0
    winner = rows[-1]["option"]

    for row in rows:
        current += float(row["weight"])

        if random_number < current:
            winner = row["option"]
            break

    embed = discord.Embed(
        title="Wheel Result",
        description=f"Winner: **{winner}**",
    )

    await interaction.edit_original_response(
        content=None,
        embed=embed,
    )


@bot.tree.command(name="wheelremove", description="Remove an option from a wheel")
async def wheelremove(
    interaction: discord.Interaction,
    name: str,
    option: str,
):
    if not await require_staff(interaction):
        return

    with get_db() as db:
        cursor = db.execute(
            """
            DELETE FROM wheels
            WHERE guild_id = ?
            AND name = ?
            AND option = ?
            """,
            (
                interaction.guild.id,
                name.lower(),
                option,
            ),
        )

    if cursor.rowcount == 0:
        await interaction.response.send_message(
            "Wheel option not found.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"Removed **{option}** from **{name}**.",
        ephemeral=True,
    )


@bot.tree.command(name="wheelreset", description="Delete an entire wheel")
async def wheelreset(
    interaction: discord.Interaction,
    name: str,
):
    if not await require_staff(interaction):
        return

    with get_db() as db:
        cursor = db.execute(
            """
            DELETE FROM wheels
            WHERE guild_id = ? AND name = ?
            """,
            (
                interaction.guild.id,
                name.lower(),
            ),
        )

    if cursor.rowcount == 0:
        await interaction.response.send_message(
            "Wheel not found.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"Wheel **{name}** was deleted.",
        ephemeral=True,
    )


def parse_duration(duration: str):
    match = re.fullmatch(
        r"([1-9]\d*)([smhd])",
        duration.lower().strip(),
    )

    if not match:
        return None

    number = int(match.group(1))
    unit = match.group(2)

    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }

    return number * multipliers[unit]


class GiveawayJoinView(discord.ui.View):
    def __init__(self, giveaway_id: int):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

        self.join_button.custom_id = (
            f"ps99_giveaway_join_{giveaway_id}"
        )

    @discord.ui.button(
        label="Join Giveaway",
        style=discord.ButtonStyle.success,
        custom_id="ps99_giveaway_join",
    )
    async def join_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        with get_db() as db:
            giveaway = db.execute(
                """
                SELECT ended
                FROM giveaways
                WHERE id = ?
                """,
                (self.giveaway_id,),
            ).fetchone()

            if not giveaway or giveaway["ended"]:
                await interaction.response.send_message(
                    "This giveaway has already ended.",
                    ephemeral=True,
                )
                return

            cursor = db.execute(
                """
                INSERT OR IGNORE INTO entrants(
                    giveaway_id,
                    user_id
                )
                VALUES (?, ?)
                """,
                (
                    self.giveaway_id,
                    interaction.user.id,
                ),
            )

        if cursor.rowcount == 0:
            await interaction.response.send_message(
                "You are already entered in this giveaway.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "You joined the giveaway!",
            ephemeral=True,
        )


async def finish_giveaway(giveaway_id: int):
    with get_db() as db:
        giveaway = db.execute(
            """
            SELECT *
            FROM giveaways
            WHERE id = ?
            """,
            (giveaway_id,),
        ).fetchone()

        if not giveaway:
            return

        if giveaway["ended"]:
            return

        entrants = db.execute(
            """
            SELECT user_id
            FROM entrants
            WHERE giveaway_id = ?
            """,
            (giveaway_id,),
        ).fetchall()

        user_ids = [
            row["user_id"]
            for row in entrants
        ]

        winner_id = (
            secrets.choice(user_ids)
            if user_ids
            else None
        )

        db.execute(
            """
            UPDATE giveaways
            SET ended = 1,
                winner_id = ?
            WHERE id = ?
            """,
            (
                winner_id,
                giveaway_id,
            ),
        )

    channel = bot.get_channel(
        giveaway["channel_id"]
    )

    if not channel:
        try:
            channel = await bot.fetch_channel(
                giveaway["channel_id"]
            )
        except Exception:
            return

    if winner_id:
        await channel.send(
            f"Giveaway **#{giveaway_id}** ended!\n"
            f"Prize: **{giveaway['prize']}**\n"
   
