import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import os
import asyncio

# ============================================================
#  KONFIGURATION – Railway Variables:
#  BOT_TOKEN        = dein Bot Token
#  LOG_CHANNEL      = ID des öffentlichen Sicherheitskanals
#  IGNORE_CHANNEL   = ID des Bot-Kanals der NICHT gesperrt wird
# ============================================================

TOKEN             = os.environ.get("BOT_TOKEN")
LOG_CHANNEL_ID    = int(os.environ.get("LOG_CHANNEL", "0"))
IGNORE_CHANNEL_ID = int(os.environ.get("IGNORE_CHANNEL", "0"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="$", intents=intents)

saved_permissions = {}
warns = {}
safe_message_id = {}


# ════════════════════════════════════════════════════════════
#  HILFSFUNKTIONEN
# ════════════════════════════════════════════════════════════

async def send_log(guild, title, description, color=0xFF0000):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel is None:
        for ch in guild.text_channels:
            if "log" in ch.name.lower() or "sicher" in ch.name.lower():
                log_channel = ch
                break
    if log_channel is None:
        return None
    embed = discord.Embed(title=title, description=description, color=color)
    embed.timestamp = datetime.now(timezone.utc)
    embed.set_footer(text="Zero.Trust")
    msg = await log_channel.send(embed=embed)
    return msg


# ════════════════════════════════════════════════════════════
#  EVENTS
# ════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    print(f"✅ Zero.Trust ist online als {bot.user}")
    print(f"   Prefix: $")
    print(f"   Log-Kanal ID: {LOG_CHANNEL_ID}")
    print(f"   Ignorierter Kanal: {IGNORE_CHANNEL_ID}")


# ════════════════════════════════════════════════════════════
#  🔒 SAFE MODE
# ════════════════════════════════════════════════════════════

@bot.command(name="Safe")
@commands.has_permissions(administrator=True)
async def safe_mode(ctx, *, reason: str = "Kein Grund angegeben"):
    await ctx.message.delete()
    msg = await ctx.send("🔒 Aktiviere Sicherheitsmodus...")

    guild = ctx.guild

    for channel in guild.channels:
        if channel.id == IGNORE_CHANNEL_ID:
            continue
        overwrite = discord.PermissionOverwrite(
            send_messages=False,
            connect=False,
            speak=False,
            create_instant_invite=False,
            add_reactions=False
        )
        try:
            await channel.set_permissions(guild.default_role, overwrite=overwrite)
        except Exception:
            pass

    try:
        invites = await guild.invites()
        for invite in invites:
            await invite.delete()
    except Exception:
        pass

    await msg.delete()

    embed = discord.Embed(
        title="🚨 SICHERHEITSMODUS AKTIVIERT",
        description=(
            f"**Grund:** **{reason}**\n\n"
            f"**Was gesperrt wurde:**\n"
            f"> 🔇 Alle Textkanäle gesperrt\n"
            f"> 🔕 Alle Voice-Kanäle gesperrt\n"
            f"> 🚫 Alle Einladungen gelöscht\n"
            f"> ❌ Reaktionen deaktiviert\n\n"
            f"**Aktiviert von:** {ctx.author.mention}\n"
            f"**Um:** <t:{int(datetime.now().timestamp())}:F>"
        ),
        color=0xFF0000
    )
    embed.set_footer(text="Zero.Trust")
    embed.timestamp = datetime.now(timezone.utc)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        safe_msg = await log_channel.send(embed=embed)
        safe_message_id[guild.id] = (log_channel.id, safe_msg.id)
    else:
        safe_msg = await ctx.channel.send(embed=embed)
        safe_message_id[guild.id] = (ctx.channel.id, safe_msg.id)


# ════════════════════════════════════════════════════════════
#  🔓 UNSAVE
# ════════════════════════════════════════════════════════════

@bot.command(name="Unsave")
@commands.has_permissions(administrator=True)
async def unsave(ctx, *, reason: str = "Sicherheitsmodus beendet"):
    await ctx.message.delete()
    guild = ctx.guild
    msg = await ctx.send("🔓 Hebe Sicherheitsmodus auf...")

    for channel in guild.channels:
        if channel.id == IGNORE_CHANNEL_ID:
            continue
        try:
            await channel.set_permissions(guild.default_role, overwrite=None)
        except Exception:
            pass

    # Sicherheitsmeldung löschen
    if guild.id in safe_message_id:
        ch_id, msg_id = safe_message_id[guild.id]
        try:
            ch = bot.get_channel(ch_id)
            if ch:
                old_msg = await ch.fetch_message(msg_id)
                await old_msg.delete()
        except Exception:
            pass
        safe_message_id.pop(guild.id)

    await msg.delete()

    embed = discord.Embed(
        title="✅ SICHERHEITSMODUS AUFGEHOBEN",
        description=(
            f"**Grund:** **{reason}**\n\n"
            f"**Aufgehoben von:** {ctx.author.mention}\n"
            f"**Um:** <t:{int(datetime.now().timestamp())}:F>"
        ),
        color=0x00FF00
    )
    embed.set_footer(text="Zero.Trust")
    embed.timestamp = datetime.now(timezone.utc)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        unsave_msg = await log_channel.send(embed=embed)
        await asyncio.sleep(5)
        try:
            await unsave_msg.delete()
        except Exception:
            pass
    else:
        unsave_msg = await ctx.channel.send(embed=embed)
        await asyncio.sleep(5)
        try:
            await unsave_msg.delete()
        except Exception:
            pass


# ════════════════════════════════════════════════════════════
#  🔒 KANAL SPERREN / ENTSPERREN
# ════════════════════════════════════════════════════════════

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx, *, reason: str = "Kein Grund angegeben"):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    embed = discord.Embed(
        title="🔒 Kanal gesperrt",
        description=f"**Kanal:** {ctx.channel.mention}\n**Grund:** **{reason}**\n**Von:** {ctx.author.mention}",
        color=0xFF0000
    )
    embed.set_footer(text="Zero.Trust")
    await ctx.send(embed=embed)
    await send_log(ctx.guild, "🔒 Kanal gesperrt", f"{ctx.channel.mention} gesperrt.\n**Grund:** **{reason}**\nVon: {ctx.author.mention}", 0xFF0000)


@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await ctx.send(f"🔓 **{ctx.channel.name}** wurde entsperrt.")
    await send_log(ctx.guild, "🔓 Kanal entsperrt", f"{ctx.channel.mention} entsperrt von {ctx.author.mention}", 0x00FF00)


# ════════════════════════════════════════════════════════════
#  🔇 QUIT – Nur Text sperren
# ════════════════════════════════════════════════════════════

@bot.command(name="quit")
@commands.has_permissions(manage_roles=True)
async def quit_cmd(ctx, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if role is None:
        role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            if isinstance(channel, discord.TextChannel):
                await channel.set_permissions(role, send_messages=False, add_reactions=False)

    await member.add_roles(role, reason=reason)

    embed = discord.Embed(
        title="🔇 Text gesperrt",
        description=(
            f"**User:** {member.mention}\n"
            f"**Grund:** **{reason}**\n"
            f"**Von:** {ctx.author.mention}\n\n"
            f"ℹ️ Der User kann noch Voice-Kanäle benutzen."
        ),
        color=0xFFA500
    )
    embed.set_footer(text="Zero.Trust")
    await ctx.send(embed=embed)
    await send_log(ctx.guild, "🔇 Text-Mute", f"{member.mention} stummgeschaltet (Text).\n**Grund:** **{reason}**\nVon: {ctx.author.mention}", 0xFFA500)

    try:
        await member.send(f"🔇 Du wurdest auf **{ctx.guild.name}** stummgeschaltet (Text).\nGrund: {reason}")
    except Exception:
        pass


@bot.command(name="unquit")
@commands.has_permissions(manage_roles=True)
async def unquit(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"✅ **{member.display_name}** kann wieder schreiben.")
        await send_log(ctx.guild, "🔊 Text-Unmute", f"{member.mention} kann wieder schreiben.\nVon: {ctx.author.mention}", 0x00FF00)
    else:
        await ctx.send("❌ User ist nicht stummgeschaltet.")


# ════════════════════════════════════════════════════════════
#  🔇 FULLMUTE – Text & Voice sperren
# ════════════════════════════════════════════════════════════

@bot.command(name="fullmute")
@commands.has_permissions(manage_roles=True)
async def fullmute(ctx, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
    role = discord.utils.get(ctx.guild.roles, name="FullMuted")
    if role is None:
        role = await ctx.guild.create_role(name="FullMuted")
        for channel in ctx.guild.channels:
            if isinstance(channel, discord.TextChannel):
                await channel.set_permissions(role, send_messages=False, add_reactions=False)
            elif isinstance(channel, discord.VoiceChannel):
                await channel.set_permissions(role, speak=False, connect=False)

    await member.add_roles(role, reason=reason)

    embed = discord.Embed(
        title="🔇 Vollständig stummgeschaltet",
        description=(
            f"**User:** {member.mention}\n"
            f"**Grund:** **{reason}**\n"
            f"**Von:** {ctx.author.mention}\n\n"
            f"❌ Kein Text, kein Voice."
        ),
        color=0xFF0000
    )
    embed.set_footer(text="Zero.Trust")
    await ctx.send(embed=embed)
    await send_log(ctx.guild, "🔇 Full-Mute", f"{member.mention} vollständig stummgeschaltet.\n**Grund:** **{reason}**\nVon: {ctx.author.mention}", 0xFF0000)

    try:
        await member.send(f"🔇 Du wurdest auf **{ctx.guild.name}** vollständig stummgeschaltet.\nGrund: {reason}")
    except Exception:
        pass


@bot.command(name="unfullmute")
@commands.has_permissions(manage_roles=True)
async def unfullmute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="FullMuted")
    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"✅ **{member.display_name}** ist nicht mehr vollständig stummgeschaltet.")
        await send_log(ctx.guild, "🔊 Full-Unmute", f"{member.mention} vollständig freigegeben.\nVon: {ctx.author.mention}", 0x00FF00)
    else:
        await ctx.send("❌ User ist nicht vollständig stummgeschaltet.")


# ════════════════════════════════════════════════════════════
#  ⏱️ TIMEOUT
# ════════════════════════════════════════════════════════════

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout_cmd(ctx, member: discord.Member, duration: str, *, reason: str = "Kein Grund angegeben"):
    if not duration[:-1].isdigit() or duration[-1] not in ("m", "h", "d"):
        return await ctx.send("❌ Beispiel: `$timeout @User 10m Spam`")

    value = int(duration[:-1])
    unit = duration[-1]

    if unit == "m":
        delta, label = timedelta(minutes=value), f"{value} Minute(n)"
    elif unit == "h":
        delta, label = timedelta(hours=value), f"{value} Stunde(n)"
    elif unit == "d":
        delta, label = timedelta(days=value), f"{value} Tag(e)"

    until = datetime.now(timezone.utc) + delta
    await member.timeout(until, reason=reason)

    embed = discord.Embed(
        title="⏱️ Timeout",
        description=f"**User:** {member.mention}\n**Dauer:** {label}\n**Grund:** **{reason}**\n**Von:** {ctx.author.mention}",
        color=0xFFA500
    )
    embed.set_footer(text="Zero.Trust")
    await ctx.send(embed=embed)
    await send_log(ctx.guild, "⏱️ Timeout", f"{member.mention} für {label} getimeouted.\n**Grund:** **{reason}**\nVon: {ctx.author.mention}", 0xFFA500)


@bot.command(name="untimeout")
@commands.has_permissions(moderate_members=True)
async def untimeout_cmd(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"✅ Timeout von **{member.display_name}** aufgehoben.")
    await send_log(ctx.guild, "✅ Timeout aufgehoben", f"{member.mention} freigegeben von {ctx.author.mention}", 0x00FF00)


# ════════════════════════════════════════════════════════════
#  👢 KICK & 🔨 BAN
# ════════════════════════════════════════════════════════════

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
    await member.kick(reason=reason)
    embed = discord.Embed(
        title="👢 Kick",
        description=f"**User:** {member.mention}\n**Grund:** **{reason}**\n**Von:** {ctx.author.mention}",
        color=0xFFA500
    )
    embed.set_footer(text="Zero.Trust")
    await ctx.send(embed=embed)
    await send_log(ctx.guild, "👢 Kick", f"{member} gekickt.\n**Grund:** **{reason}**\nVon: {ctx.author.mention}", 0xFFA500)


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
    await member.ban(reason=reason)
    embed = discord.Embed(
        title="🔨 Ban",
        description=f"**User:** {member.mention}\n**Grund:** **{reason}**\n**Von:** {ctx.author.mention}",
        color=0xFF0000
    )
    embed.set_footer(text="Zero.Trust")
    await ctx.send(embed=embed)
    await send_log(ctx.guild, "🔨 Ban", f"{member} gebannt.\n**Grund:** **{reason}**\nVon: {ctx.author.mention}", 0xFF0000)


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, username: str):
    banned = [entry async for entry in ctx.guild.bans()]
    for entry in banned:
        if str(entry.user) == username:
            await ctx.guild.unban(entry.user)
            await ctx.send(f"✅ **{username}** wurde entbannt.")
            return await send_log(ctx.guild, "✅ Unban", f"{username} entbannt von {ctx.author.mention}", 0x00FF00)
    await ctx.send(f"❌ **{username}** nicht gefunden.")


# ════════════════════════════════════════════════════════════
#  ⚠️ WARN SYSTEM
# ════════════════════════════════════════════════════════════

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    if guild_id not in warns:
        warns[guild_id] = {}
    if user_id not in warns[guild_id]:
        warns[guild_id][user_id] = []
    warns[guild_id][user_id].append(reason)
    count = len(warns[guild_id][user_id])

    embed = discord.Embed(
        title="⚠️ Verwarnung",
        description=f"**User:** {member.mention}\n**Grund:** **{reason}**\n**Von:** {ctx.author.mention}\n**Verwarnungen gesamt:** {count}",
        color=0xFFFF00
    )
    embed.set_footer(text="Zero.Trust")
    await ctx.send(embed=embed)
    await send_log(ctx.guild, "⚠️ Warn", f"{member.mention} verwarnt ({count}x).\n**Grund:** **{reason}**\nVon: {ctx.author.mention}", 0xFFFF00)

    try:
        await member.send(f"⚠️ Du wurdest auf **{ctx.guild.name}** verwarnt!\nGrund: {reason}\nVerwarnungen: {count}")
    except Exception:
        pass


@bot.command(name="warnings")
@commands.has_permissions(manage_messages=True)
async def warnings(ctx, member: discord.Member):
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    user_warns = warns.get(guild_id, {}).get(user_id, [])
    if not user_warns:
        return await ctx.send(f"✅ **{member.display_name}** hat keine Verwarnungen.")
    msg = f"⚠️ Verwarnungen von **{member.display_name}** ({len(user_warns)}):\n"
    for i, reason in enumerate(user_warns, 1):
        msg += f"`{i}.` {reason}\n"
    await ctx.send(msg)


@bot.command(name="clearwarns")
@commands.has_permissions(administrator=True)
async def clearwarns(ctx, member: discord.Member):
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    if guild_id in warns and user_id in warns[guild_id]:
        warns[guild_id][user_id] = []
    await ctx.send(f"✅ Alle Verwarnungen von **{member.display_name}** gelöscht.")


# ════════════════════════════════════════════════════════════
#  🧹 CLEAR CHAT
# ════════════════════════════════════════════════════════════

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: str):
    await ctx.message.delete()
    now = datetime.now(timezone.utc)

    if amount[-1] in ("h", "m", "d") and amount[:-1].isdigit():
        value = int(amount[:-1])
        unit = amount[-1]
        if unit == "m":
            delta, label = timedelta(minutes=value), f"{value} Minute(n)"
        elif unit == "h":
            delta, label = timedelta(hours=value), f"{value} Stunde(n)"
        elif unit == "d":
            delta, label = timedelta(days=value), f"{value} Tag(e)"
        cutoff = now - delta
        deleted = await ctx.channel.purge(limit=1000, check=lambda m: m.created_at >= cutoff)
        msg = await ctx.send(f"🗑️ {len(deleted)} Nachrichten der letzten {label} gelöscht.")
    elif amount.isdigit():
        deleted = await ctx.channel.purge(limit=int(amount))
        msg = await ctx.send(f"🗑️ {len(deleted)} Nachrichten gelöscht.")
    else:
        msg = await ctx.send("❌ Beispiele: `$clear 2h` `$clear 30m` `$clear 50`")
    await msg.delete(delay=5)


# ════════════════════════════════════════════════════════════
#  👤 USER INFO & 📊 SERVER INFO
# ════════════════════════════════════════════════════════════

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    user_warns = warns.get(guild_id, {}).get(user_id, [])

    embed = discord.Embed(title=f"👤 {member.display_name}", color=0x5865F2)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Erstellt", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Beigetreten", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Rollen", value=", ".join([r.mention for r in member.roles[1:]]) or "Keine", inline=False)
    embed.add_field(name="Verwarnungen", value=len(user_warns), inline=True)
    embed.add_field(name="Bot?", value="✅" if member.bot else "❌", inline=True)
    embed.set_footer(text="Zero.Trust")
    await ctx.send(embed=embed)


@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=0x5865F2)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="ID", value=guild.id, inline=True)
    embed.add_field(name="Mitglieder", value=guild.member_count, inline=True)
    embed.add_field(name="Kanäle", value=len(guild.channels), inline=True)
    embed.add_field(name="Rollen", value=len(guild.roles), inline=True)
    embed.add_field(name="Erstellt", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.set_footer(text="Zero.Trust")
    await ctx.send(embed=embed)


# ════════════════════════════════════════════════════════════
#  🎭 ROLLEN MANAGEMENT
# ════════════════════════════════════════════════════════════

@bot.command(name="addrole")
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role is None:
        return await ctx.send(f"❌ Rolle **{role_name}** nicht gefunden!")
    await member.add_roles(role)
    await ctx.send(f"✅ Rolle **{role.name}** → **{member.display_name}**")


@bot.command(name="removerole")
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role is None:
        return await ctx.send(f"❌ Rolle **{role_name}** nicht gefunden!")
    await member.remove_roles(role)
    await ctx.send(f"✅ Rolle **{role.name}** von **{member.display_name}** entfernt.")


# ════════════════════════════════════════════════════════════
#  📢 ANNOUNCE & DM
# ════════════════════════════════════════════════════════════

@bot.command(name="announce")
@commands.has_permissions(manage_messages=True)
async def announce(ctx, *, text: str):
    await ctx.message.delete()
    embed = discord.Embed(title="📢 Ankündigung", description=text, color=0x5865F2)
    embed.set_footer(text=f"Von {ctx.author.display_name} • Zero.Trust")
    embed.timestamp = datetime.now(timezone.utc)
    await ctx.send(embed=embed)


@bot.command(name="dm")
@commands.has_permissions(manage_messages=True)
async def dm(ctx, member: discord.Member, *, message: str):
    await ctx.message.delete()
    try:
        embed = discord.Embed(
            title=f"📩 Nachricht von {ctx.guild.name}",
            description=message,
            color=0x5865F2
        )
        embed.set_footer(text="Zero.Trust")
        await member.send(embed=embed)
        await ctx.send(f"✅ DM an **{member.display_name}** gesendet.", delete_after=5)
    except Exception:
        await ctx.send(f"❌ Konnte **{member.display_name}** keine DM senden.", delete_after=5)


# ════════════════════════════════════════════════════════════
#  🔊 VOICE KICK
# ════════════════════════════════════════════════════════════

@bot.command(name="vckick")
@commands.has_permissions(move_members=True)
async def vckick(ctx, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
    if member.voice is None:
        return await ctx.send("❌ User ist in keinem Voice-Channel.")
    await member.move_to(None, reason=reason)
    await ctx.send(f"🔊 **{member.display_name}** wurde aus dem Voice-Channel gekickt.\n📝 **Grund:** **{reason}**")
    await send_log(ctx.guild, "🔊 VC-Kick", f"{member.mention} aus VC gekickt.\n**Grund:** **{reason}**\nVon: {ctx.author.mention}", 0xFFA500)


# ════════════════════════════════════════════════════════════
#  🧹 NICK ÄNDERN
# ════════════════════════════════════════════════════════════

@bot.command(name="nick")
@commands.has_permissions(manage_nicknames=True)
async def nick(ctx, member: discord.Member, *, nickname: str = None):
    old_nick = member.display_name
    await member.edit(nick=nickname)
    if nickname:
        await ctx.send(f"✅ Nickname von **{old_nick}** → **{nickname}**")
    else:
        await ctx.send(f"✅ Nickname von **{old_nick}** zurückgesetzt.")


# ════════════════════════════════════════════════════════════
#  ℹ️ INFO
# ════════════════════════════════════════════════════════════

@bot.command(name="info")
@commands.has_permissions(administrator=True)
async def info(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="Zero.Trust",
        description=(
            "**Kein Vertrauen. Keine Ausnahmen. Keine Kompromisse.**\n\n"
            "Ein kompromissloser Sicherheits- und Moderations-Bot der nach einem einzigen Prinzip handelt: "
            "Vertraue niemandem. Egal ob Raid, Spam oder Regelverstöße — Zero.Trust reagiert sofort, "
            "protokolliert alles öffentlich und gibt Admins die volle Kontrolle über ihren Server. "
            "Jede Aktion wird mit Grund dokumentiert, damit die gesamte Community informiert bleibt.\n\n"
            "**Kernfunktionen:**\n"
            "> 🔒 Raid Protection — Server auf Knopfdruck komplett sperren\n"
            "> 🔇 Moderation — Warn, Mute, Timeout, Kick, Ban\n"
            "> 🎙️ Voice Control — Text & Voice separat sperren\n"
            "> 📋 Public Log — Jede Aktion öffentlich dokumentiert\n\n"
            "Prefix: `$` • Nutze `$hilfe` für alle Befehle"
        ),
        color=0x2B2D31
    )
    embed.set_footer(text="Built by Code-byMalik • Zero.Trust v1.0")
    embed.timestamp = datetime.now(timezone.utc)
    await ctx.send(embed=embed)


# ════════════════════════════════════════════════════════════
#  📋 HILFE
# ════════════════════════════════════════════════════════════

@bot.command(name="hilfe")
async def hilfe(ctx):
    embed = discord.Embed(title="📋 Zero.Trust Befehle", description="Prefix: `$`", color=0x2B2D31)
    embed.add_field(name="🔒 Sicherheit", value="""
`$Safe <Grund>` – Server komplett sperren
`$Unsave <Grund>` – Server entsperren
`$lock <Grund>` – Kanal sperren
`$unlock` – Kanal entsperren
""", inline=False)
    embed.add_field(name="🔇 Stummschalten", value="""
`$quit @User <Grund>` – Nur Text sperren (VC erlaubt)
`$unquit @User` – Text freigeben
`$fullmute @User <Grund>` – Text & Voice sperren
`$unfullmute @User` – Vollständig freigeben
`$timeout @User 10m <Grund>` – Timeout
`$untimeout @User` – Timeout aufheben
`$vckick @User <Grund>` – Aus Voice-Channel kicken
""", inline=False)
    embed.add_field(name="👮 Moderation", value="""
`$warn @User <Grund>` – Verwarnen
`$warnings @User` – Verwarnungen anzeigen
`$clearwarns @User` – Verwarnungen löschen
`$kick @User <Grund>` – Kicken
`$ban @User <Grund>` – Bannen
`$unban User#1234` – Entbannen
`$clear 50` – Chat löschen
""", inline=False)
    embed.add_field(name="🎭 Verwaltung", value="""
`$addrole @User Rollenname` – Rolle geben
`$removerole @User Rollenname` – Rolle entfernen
`$nick @User Nickname` – Nickname ändern
`$dm @User Nachricht` – DM senden
`$announce <Text>` – Ankündigung
`$userinfo @User` – User Info
`$serverinfo` – Server Info
`$info` – Bot Info (nur Admins)
""", inline=False)
    embed.set_footer(text="Zero.Trust • Built by Code-byMalik")
    await ctx.send(embed=embed)


# ── Error Handler ────────────────────────────────────────────
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Du hast keine Berechtigung!", delete_after=5)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Mitglied nicht gefunden!", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Fehlende Argumente! Nutze `$hilfe`", delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        pass


bot.run(TOKEN)
