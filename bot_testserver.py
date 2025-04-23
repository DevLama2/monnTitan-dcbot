from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ui import Button, View

# Token und IDs
with open("token.txt", "r") as file:
    TOKEN = file.read().strip()

BUGS_CHANNEL_ID = 1364221910254358593
GUILD_ID = 834345976420106261
EVENTS_CHANNEL_ID = 1353804755914326137
ANMELDEN_CHANNEL_ID = 1353070994230870027
TEAMS_CHANNEL_ID = 1353804818078236805
STATISTICS_CHANNEL_ID = 1353804588372983830
TEAM_ROLE_ID = 1353817126737281035

# Bot-Klasse
class MyBot(commands.Bot):
    def __init__(self, **kwargs):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, **kwargs)

    async def setup_hook(self):
        print("Bot wird vorbereitet.")

# Bot starten
bot = MyBot()

@bot.event
async def on_ready():
    if GUILD_ID == 834345976420106261:
        guildname = "LamaTestserver"
    elif GUILD_ID == 1320473550259228682:
        guildname = "Moon-Titan"
    else:
        guildname = f"Unbekannte GUILD_ID({GUILD_ID})"
    synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Synced {len(synced)} command(s) in {guildname}:")
    for i in synced:
        print(f"/{i.name} | {i.description}")
    print(f'✅ Bot ist eingeloggt als {bot.user}')

# Eventankündigung
@bot.tree.command(name="eventankündigung", description="Erstellt eine Event-Ankündigung", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    spielmodus="Wähle den Spielmodus (nur OneDayTitan oder Meetup)",
    uhrzeit="Startzeit im Format HH:MM",
    host="Name des Hosts",
    eventnummer="Event-Nummer",
    teamgröße="Größe der Teams",
    kit="Verwendetes Kit"
)
@app_commands.choices(
    spielmodus=[
        app_commands.Choice(name="OneDayTitan", value="OneDayTitan"),
        app_commands.Choice(name="Meetup", value="Meetup")
    ]
)
async def eventankündigung(
        interaction: discord.Interaction,
        spielmodus: app_commands.Choice[str],
        uhrzeit: str,
        host: str,
        eventnummer: str,
        teamgröße: str,
        kit: str
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: Eventankündigung für Event #{eventnummer}")

    if interaction.channel.id != EVENTS_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ **Fehler:** Dieser Befehl kann nur im Event-Kanal verwendet werden!", ephemeral=True
        )
        return

    events_channel = bot.get_channel(EVENTS_CHANNEL_ID)
    if not events_channel:
        await interaction.response.send_message("❌ **Fehler:** Event-Kanal nicht gefunden!", ephemeral=True)
        return

    spielmodus = spielmodus.value

    def event_message(time_info):
        return f"""
:milky_way: **Moon-Titan-{spielmodus}** ({eventnummer}) :milky_way:
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:earth_africa: 》**Server-IP: Titan-Event.de** 
:alarm_clock: 》**Start: {time_info}** 
:busts_in_silhouette: 》Teams of: {teamgröße}
:shirt: 》Kit: {kit} :llama:
:bust_in_silhouette: 》Host: {host}
:bow_and_arrow: 》Mods: https://discord.com/channels/1320473550259228682/1320476122843971624
:scroll: 》Regeln: ⁠https://discord.com/channels/1320473550259228682/1320475971442311248
:warning: 》Discord: [**Hier klicken!**](https://discord.gg/8nYke2CBTR)
:exclamation: 》Der Server öffnet 15 Minuten vor Start!
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
||@everyone|| 
-# https://spexhosting.de/
"""

    def reminder_15min_message():
        return f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:milky_way: **Moon-Titan-{spielmodus}** ({eventnummer}) :milky_way:
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:earth_africa: 》**Server-IP: Titan-Event.de** 
:alarm_clock: 》**Start: {uhrzeit} Uhr (in 15 Minuten)** 
:busts_in_silhouette: 》Teams of: {teamgröße}
:shirt: 》Kit: {kit} :llama:
:warning: 》Discord:  [**Hier klicken!**](https://discord.gg/8nYke2CBTR)
:exclamation: 》Der Server ist geöffnet. Start in 15 Minuten!
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
||@everyone|| 
-# https://spexhosting.de/
"""

    def reminder_5min_message():
        return f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:milky_way: **Moon-Titan-{spielmodus}** ({eventnummer}) :milky_way:
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
### :earth_africa: 》**Server-IP: Titan-Event.de** 
### :alarm_clock: 》**Start: in 5 Minuten!** 
### :warning: 》**Discord: [Hier klicken!](https://discord.gg/8nYke2CBTR)**
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
||@everyone|| 
-# https://spexhosting.de/
"""

    event_msg = await events_channel.send(event_message(f"{uhrzeit} Uhr"))
    await event_msg.publish()

    await interaction.response.send_message("✅ **Das Event wurde angekündigt und veröffentlicht!**", ephemeral=True)

    try:
        event_time = datetime.strptime(uhrzeit, "%H:%M")
        now = datetime.now()
        event_datetime = datetime.combine(now.date(), event_time.time())

        if event_datetime < now:
            event_datetime += timedelta(days=1)

        time_until_event = (event_datetime - now).total_seconds()

        reminder_sent_15min = False
        reminder_sent_5min = False

        while time_until_event > 0:
            remaining_minutes = int(time_until_event // 60)

            if remaining_minutes <= 14 and not reminder_sent_15min:
                reminder_msg_15min = await events_channel.send(reminder_15min_message())
                await reminder_msg_15min.publish()
                reminder_sent_15min = True

            if remaining_minutes <= 4 and not reminder_sent_5min:
                reminder_msg_5min = await events_channel.send(reminder_5min_message())
                await reminder_msg_5min.publish()
                reminder_sent_5min = True

            await asyncio.sleep(10)
            time_until_event -= 10

        print(f"\rDas Event {eventnummer} ({spielmodus}) hat um {uhrzeit} gestartet!")

    except ValueError:
        await interaction.followup.send("❌ **Fehler:** Ungültiges Uhrzeit-Format! Verwende HH:MM (z. B. 18:30).", ephemeral=True)


@bot.tree.command(name="anmelden", description="Melde dein Team für das Event an!", guild=discord.Object(id=GUILD_ID))
async def anmelden(
        interaction: discord.Interaction,
        teamname: str,
        ingame1: str,
        ingame2: str,
        ingame3: str,
        discord1: str,
        discord2: str,
        discord3: str,
        yt1: str,
        yt2: str,
        yt3: str
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: Team Anmeldung für {teamname}")
    if interaction.channel.id != ANMELDEN_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ **Fehler:** Dieser Befehl kann nur im richtigen Kanal verwendet werden!", ephemeral=True
        )
        return

    teams_channel = bot.get_channel(TEAMS_CHANNEL_ID)
    if not teams_channel:
        await interaction.response.send_message(
            "❌ **Fehler:** Zielkanal nicht gefunden!", ephemeral=True
        )
        return

    message = (
        f"🏷 **Teamname:** {teamname}\n\n"
        f"🎭 **Ingame-Namen:**\n"
        f"- {ingame1}\n"
        f"- {ingame2}\n"
        f"- {ingame3}\n\n"
        f"👥 **Discord-User:**\n"
        f"- {discord1}\n"
        f"- {discord2}\n"
        f"- {discord3}\n\n"
        f"📺 **YouTube-Links:**\n"
        f"- 🔗 [Kanal von {ingame1}]({yt1})\n"
        f"- 🔗 [Kanal von {ingame2}]({yt2})\n"
        f"- 🔗 [Kanal von {ingame3}]({yt3})\n\n"
        f"🚀 Viel Erfolg im Turnier!:llama:"
    )

    await teams_channel.send(message)

    await interaction.response.send_message("✅ **Dein Team wurde erfolgreich angemeldet!**", ephemeral=True)


@bot.tree.command(name="winner",
                  description="Erstellt eine Nachricht für den Gewinner eines Events und eine Statistik-Nachricht",
                  guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    eventnummer="Die Eventnummer",
    teamname="Der Name des Teams",
    kills="Anzahl der Kills des Teams",
    spieler="Die Spieler im Team (Trenne sie mit Kommas)",
    host="Name des Hosts"
)
async def winner(
        interaction: discord.Interaction,
        eventnummer: str,
        teamname: str,
        kills: int,
        spieler: str,
        host: str
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: Winner Nachricht für Event #{eventnummer}")
    if interaction.channel.id != EVENTS_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ **Fehler:** Dieser Befehl kann nur im Event-Kanal verwendet werden!", ephemeral=True
        )
        return

    events_channel = bot.get_channel(EVENTS_CHANNEL_ID)
    statistics_channel = bot.get_channel(STATISTICS_CHANNEL_ID)
    if not events_channel or not statistics_channel:
        await interaction.response.send_message("❌ **Fehler:** Event- oder Statistik-Kanal nicht gefunden!",
                                                ephemeral=True)
        return

    spieler_liste = spieler.split(",")  # Spieler durch Komma trennen
    if len(spieler_liste) > 4:
        await interaction.response.send_message("❌ **Fehler:** Maximal 4 Spieler sind erlaubt!", ephemeral=True)
        return

    # Formatieren der Spielernamen
    spieler_message = "\n".join([f"- {spieler.strip()}" for spieler in spieler_liste])

    # Nachrichtenvorlage für den Gewinner
    winner_message = f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
🌌 Moon-Titan Event #{eventnummer} | Winner 🌌
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
👑 #{teamname}
Spieler:
{spieler_message}

Kills: {kills}:llama:

Herzlichen Glückwunsch und viel Erfolg beim nächsten Event!
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
"""

    # Nachrichtenvorlage für Statistiken
    statistics_message = f"""
**Host vorbei**

Event: {eventnummer}
Host: {host}
"""

    # Sende die Gewinner-Nachricht im Event-Channel
    await events_channel.send(winner_message)

    # Sende die Statistiken im Statistik-Kanal
    await statistics_channel.send(statistics_message)

    # Bestätigungsnachricht an den Benutzer
    await interaction.response.send_message(
        f"✅ **Der Gewinner für Event #{eventnummer} und die Statistiken wurden gepostet!**", ephemeral=True)


@bot.tree.command(name="ticket", description="Erstellt interaktiven Knöpfe zum antworten auf Ticket-Anfragen",
                  guild=discord.Object(id=GUILD_ID))
@app_commands.describe(ticket_user="Der Benutzer des Tickets")
async def ticket(interaction: discord.Interaction, ticket_user: discord.User):
    # Uhrzeit und Kanalinfos
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    # Print-Anweisung für Debugging
    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: Ticket-Befehl angefordert")
    # Erlaubte Rollen (Team)
    allowed_roles = [TEAM_ROLE_ID]  # Ersetze mit den richtigen IDs

    # Prüfen, ob der Nutzer ein Member-Objekt ist (um Rollen zu lesen)
    if isinstance(interaction.user, discord.Member):
        user_roles = [role.id for role in interaction.user.roles]
    else:
        await interaction.response.send_message("❌ Fehler: Konnte deine Rollen nicht abrufen.", ephemeral=True)
        return

    # Berechtigungsprüfung
    if not any(role in allowed_roles for role in user_roles):
        await interaction.response.send_message("❌ Du hast nicht die benötigte Rolle, um diesen Befehl auszuführen!",
                                                ephemeral=True)
        return

    # Erstelle eine View mit Knöpfen
    view = View()

    # Knöpfe für die Interaktionen
    begruessung_button = Button(label="Begrüßung", style=discord.ButtonStyle.primary, custom_id="begruessung")
    nachricht_button = Button(label="Nachricht erhalten", style=discord.ButtonStyle.primary,
                              custom_id="nachricht_erhalten")
    geduld_button = Button(label="Bitte noch Geduld", style=discord.ButtonStyle.primary, custom_id="geduld")
    team_button = Button(label="Teammitglied angenommen", style=discord.ButtonStyle.primary,
                         custom_id="team_angenommen")

    async def begruessung_button_callback(interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Lieber {ticket_user.mention},\ndu hast ein Ticket geöffnet. **Teile uns gerne dein Anliegen mit.**\nWir werden uns dann **so schnell wie möglich** bei dir melden!\n*Moon-Titan* | {interaction.user.mention}:llama:")

    async def nachricht_button_callback(interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Lieber {ticket_user.mention},\nwir haben deine Nachricht erhalten.\n**Wir werden uns nun im Team beraten und dann so schnell wie möglich bei dir melden!**\n*Moon-Titan* | {interaction.user.mention}:llama:")

    async def geduld_button_callback(interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Lieber {ticket_user.mention}!\n\nWir möchten dich darüber informieren, dass die Bearbeitung deines Anliegens etwas mehr Zeit in Anspruch nimmt. Bitte habe noch ein wenig Geduld – wir arbeiten bereits daran, dir schnellstmöglich zu helfen.\n\nVielen Dank für dein Verständnis!\n*Moon-Titan* | {interaction.user.mention}:llama:")

    async def team_button_callback(interaction: discord.Interaction):
        await interaction.response.send_message(
            f":tada: **Herzlichen Glückwunsch und willkommen im Team!** :tada:\n\nHey {ticket_user.mention}, du wurdest erfolgreich ins Moon-Titan-Team aufgenommen! :rocket:\nUm direkt loszulegen, gib bitte den Befehl `/leitfaden` ein. Dort findest du alle wichtigen Informationen und Anleitungen für deinen Start bei uns.\n\nWir freuen uns auf die Zusammenarbeit mit dir – auf eine großartige Zeit! :milky_way::llama:")

    # Setze die Callback-Funktionen der Knöpfe
    begruessung_button.callback = begruessung_button_callback
    nachricht_button.callback = nachricht_button_callback
    geduld_button.callback = geduld_button_callback
    team_button.callback = team_button_callback

    # Füge die Knöpfe der View hinzu
    view.add_item(begruessung_button)
    view.add_item(nachricht_button)
    view.add_item(geduld_button)
    view.add_item(team_button)

    # Sende eine Nachricht mit den Knöpfen
    await interaction.response.send_message(f"Hallo {interaction.user}, bitte wähle eine der folgenden Optionen aus:",
                                            ephemeral=True, view=view)


@bot.tree.command(name="leitfaden", description="Sendet Info Nachricht", guild=discord.Object(id=GUILD_ID))
@app_commands.describe()
async def leitfaden(interaction: discord.Interaction):
    allowed_roles = [TEAM_ROLE_ID]
    # Prüfen, ob der Nutzer ein Member-Objekt ist (um Rollen zu lesen)
    if isinstance(interaction.user, discord.Member):
        user_roles = [role.id for role in interaction.user.roles]
    else:
        await interaction.response.send_message("❌ Fehler: Konnte deine Rollen nicht abrufen.", ephemeral=True)
        return

    # Berechtigungsprüfung
    if not any(role in allowed_roles for role in user_roles):
        await interaction.response.send_message("❌ Du hast nicht die benötigte Rolle, um diesen Befehl auszuführen!",
                                                ephemeral=True)
        return

    # Uhrzeit und Kanalinfos
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    # Print-Anweisung für Debugging
    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: Leitfaden angefordert")
    # message deklareiren
    leitfade_message = f"""
    :milky_way: **Moon-Titan - Leitfaden für Teammitglieder** :milky_way:  
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬  

Willkommen im Team {interaction.user} ! Hier findest du eine Übersicht über die wichtigsten Funktionen und Abläufe, um die Zusammenarbeit reibungslos zu gestalten.  

**:clipboard: Bot-Befehle**  
- `/tickets` – Zur Bearbeitung von Tickets.  
  *(Hinweis: Bitte führe diesen Befehl direkt im entsprechenden Ticket-Kanal aus.)*  
- `/danke` – Nutze diesen Befehl, um Justin für seine Unterstützung zu danken.  
- `/eventankündigung` – Für das Hosting von Events.  

**:tools: Team-Chats**  :llama:
- Wir haben einen eigenen **Team-Discord-Server**, auf dem wir uns austauschen, koordinieren und gemeinsam an Projekten arbeiten können. Du bist herzlich eingeladen, diesem Server beizutreten: https://discord.gg/tcQryrGQ9S . Wir freuen uns, dich dort zu sehen!
- **Teamchat** (#💬┆teamchat)  
  Hier findet die gesamte Teamkommunikation statt – alles Wichtige wird hier besprochen.  
- **Off-Topic Teamchat** (#💬┆off-topic)  
  Dieser Kanal ist für lockere Gespräche oder Bot-Befehle gedacht.  
- **To-Do-Kanal** (#🔴┆to-do)  
  Eine Übersicht über Aufgaben, die du mit deiner Rolle übernehmen musst.  
- Außerdem gibt es einen Kanal für alle anstehenden Aufgaben: **#📌┆aufgaben**. Hier kannst du sehen, welche Aufgaben noch erledigt werden müssen.
- Außerdem gibt es eine Hostanleitung in **#📌┆hostanleitung**

**:video_game: Hostanfragen verwalten**  
- `/hostanfrage` – Spieler können hier Hostanfragen stellen.  
  - Sobald eine Anfrage gestellt wird, werden alle Teammitglieder gepingt.  
  - Überprüfe im Host-Anfragen-Kanal (#📝┆hostanfrage), ob bereits ein anderer Teamkollege die Anfrage übernommen hat.  
  - **Wenn du den Host übernehmen kannst:** Reagiere auf die Nachricht im Kanal, um zu signalisieren, dass du die Anfrage übernimmst.  

Vielen Dank für deinen Einsatz – gemeinsam machen wir Moon-Titan großartig! :rocket:


    """

    # Sende eine Nachricht
    await interaction.response.send_message(leitfade_message)


@bot.tree.command(name="hallo", description="Sagt hallo", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="Der Benutzer, dem du hallo sagen willst")
async def hallo(interaction: discord.Interaction, user: str):
    # Uhrzeit und Kanalinfos
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    # Print-Anweisung für Debugging
    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: Hallo an {user} gesendet")
    # message deklareieren
    hallo_message = f"""
    Hallo {user}! :llama:
    """

    # Sende eine Nachricht
    await interaction.response.send_message(hallo_message)

@bot.tree.command(name="message", description="Sendet Nachricht", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(nachricht = "Nachricht die gesendet werden soll")
async def hallo(interaction: discord.Interaction, nachricht: str):
    allowed_roles = [TEAM_ROLE_ID]
    # Prüfen, ob der Nutzer ein Member-Objekt ist (um Rollen zu lesen)
    if isinstance(interaction.user, discord.Member):
        user_roles = [role.id for role in interaction.user.roles]
    else:
        await interaction.response.send_message("❌ Fehler: Konnte deine Rollen nicht abrufen.", ephemeral=True)
        return

    # Berechtigungsprüfung
    if not any(role in allowed_roles for role in user_roles):
        await interaction.response.send_message("❌ Du hast nicht die benötigte Rolle, um diesen Befehl auszuführen!",
                                                ephemeral=True)
        return
    # Uhrzeit und Kanalinfos
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    # Print-Anweisung für Debugging
    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: Lässt lama_bot {nachricht} senden")


    # Sende eine Nachricht
    await interaction.response.send_message("Nachricht gesendet", ephemeral=True)
    await interaction.channel.send(nachricht)


@bot.tree.command(name="bug", description="meldet einen Bug", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(nachricht = "Bug der gemeldet werden soll")
async def bug(interaction: discord.Interaction, nachricht: str):
    

    # Uhrzeit und Kanalinfos
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    # Print-Anweisung für Debugging
    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: meldet '{nachricht}' als bug")


    # Sende eine Nachricht
    await interaction.response.send_message("Vielen Dank für deine Meldung. Das Team wird sich so schnell wie möglich um den bug kümmern!", ephemeral=True)
    await BUGS_CHANNEL_ID.send(f"""User: {interaction.user}
                               Bug: {nachricht}""")

bot.run(TOKEN)
