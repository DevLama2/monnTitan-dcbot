from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ui import Button, View
import json
import os

# Token und IDs test
with open("token.txt", "r") as file:
    TOKEN = file.read().strip()

# Server IDs
MAIN_GUILD_ID = 1320473550259228682  # Hauptserver für alle anderen Befehle
TEAM_GUILD_ID = 1324015440749395978  # Team Server für Hostplan

# Channel IDs auf dem Hauptserver
BUGS_CHANNEL_ID = 1364221539179958374
EVENTS_CHANNEL_ID = 1320473550720860221
ANMELDEN_CHANNEL_ID = 1353064842088419398
TEAMS_CHANNEL_ID = 1353064996925345852
STATISTICS_CHANNEL_ID = 1323272606001922078
HOSTVORSCHLAG_CHANNEL_ID = 1320487357719384088

# Host Statistik Konstanten
HOST_STATS_FILE = "host_statistics.json"

# Message Logging Channels
MESSAGE_LOG_CHANNEL = 1322550417988522014
TRACKED_CHANNELS = [
    1323444738585530368,  # Channel IDs die überwacht werden sollen
    1325207150825570336,
    1325207150825570336,
    1320475784955166730,
    1320479622411849848,
    1352983672797663282,
    1353301055001202768,
    1353064842088419398,
    1353064996925345852
]

# Channel IDs auf dem Team Server
HOSTPLAN_CHANNEL_ID = 1324060331978526720
TEAM_VORSCHLAG_CHANNEL_ID = 1324059244387106849  # Neuer Channel für Team-Benachrichtigungen

# Rollen IDs
TEAM_ROLE_ID = 1321603815237091388
HOST_ROLE_ID = 1324079407828303996

# Ticket Konstanten 
TICKET_CREATE_CHANNEL = 1320477845184839764
TICKET_SETTINGS_CHANNEL = 1365427778249560174
TICKET_LOG_CHANNEL = 1365429053787734218

# Hilfsfunktion zur Rollenüberprüfung je nach Server
def has_required_role(member: discord.Member) -> bool:
    # Prüfe zuerst ob wir auf dem Team-Server sind
    if member.guild and member.guild.id == TEAM_GUILD_ID:
        return True
        
    # Auf dem Hauptserver wird die Team-Rolle benötigt
    if member.guild and member.guild.id == MAIN_GUILD_ID:
        return any(role.id == TEAM_ROLE_ID for role in member.roles)
        
    return False

# Host Statistiken laden/speichern
def load_host_statistics():
    try:
        with open(HOST_STATS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        default_stats = {
            "hosts": {}  # Dictionary mit Host-Namen als Keys
        }
        save_host_statistics(default_stats)
        return default_stats

def save_host_statistics(stats):
    with open(HOST_STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=4)

def update_host_statistics(host_name: str, event_type: str):
    stats = load_host_statistics()
    
    # Erstelle einen neuen Eintrag für den Host falls noch nicht vorhanden
    if host_name not in stats["hosts"]:
        stats["hosts"][host_name] = {
            "OneDayTitan": 0,
            "Meetup": 0,
            "total_events": 0
        }
    
    # Aktualisiere die Statistiken
    stats["hosts"][host_name][event_type] += 1
    stats["hosts"][host_name]["total_events"] += 1
    
    # Speichere die aktualisierten Statistiken
    save_host_statistics(stats)
    
    return stats

def format_host_statistics():
    stats = load_host_statistics()
    
    # Sortiere Hosts nach Gesamtanzahl der Events
    sorted_hosts = sorted(
        stats["hosts"].items(),
        key=lambda x: x[1]["total_events"],
        reverse=True
    )
    
    # Erstelle die formatierte Nachricht
    message = "```\n📊 Host Statistiken 📊\n"
    message += "═══════════════════════\n\n"
    
    for host_name, host_stats in sorted_hosts:
        message += f"👤 {host_name}:\n"
        message += f"  ├ OneDayTitan: {host_stats['OneDayTitan']}\n"
        message += f"  ├ Meetup: {host_stats['Meetup']}\n"
        message += f"  └ Gesamt: {host_stats['total_events']}\n\n"
    
    message += "```"
    return message

# Ticket Einstellungen laden/speichern
def load_ticket_settings():
    try:
        with open('ticket_settings.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        default_settings = {
            "default_users": [],
            "default_roles": [],
            "category_id": None,
            "ticket_counter": 0,
            "log_channel_id": TICKET_LOG_CHANNEL,
            "ticket_create_channel_id": TICKET_CREATE_CHANNEL,
            "settings_channel_id": TICKET_SETTINGS_CHANNEL,
            "archive_directory": "ticket_archives"
        }
        save_ticket_settings(default_settings)
        return default_settings

def save_ticket_settings(settings):
    with open('ticket_settings.json', 'w') as f:
        json.dump(settings, f, indent=4)

# Stelle sicher, dass der Archive-Ordner existiert
if not os.path.exists('ticket_archives'):
    os.makedirs('ticket_archives')

# Hostplan Button Klassen - außerhalb der Bot-Klasse definiert
class HostButton(Button):
    def __init__(self, datum: str):
        super().__init__(
            label="Als Host eintragen",
            style=discord.ButtonStyle.primary,
            custom_id=f"host_{datum}"
        )
        self.datum = datum

    async def callback(self, interaction: discord.Interaction):
        # Button deaktivieren
        self.disabled = True
        self.label = f"Host: {interaction.user.name}"
        self.style = discord.ButtonStyle.success
        
        # Aktiviere den Austragen-Button
        for item in self.view.children:
            if isinstance(item, UnregisterButton):
                item.disabled = False
        
        # View aktualisieren
        await interaction.message.edit(view=self.view)
        await interaction.response.send_message(
            f"✅ Du hast dich erfolgreich als Host für den {self.datum} eingetragen!", 
            ephemeral=True
        )

class UnregisterButton(Button):
    def __init__(self, datum: str):
        super().__init__(
            label="Austragen",
            style=discord.ButtonStyle.danger,
            custom_id=f"unregister_{datum}",
            disabled=True
        )
        self.datum = datum

    async def callback(self, interaction: discord.Interaction):
        # Finde den Host-Button
        host_button = None
        for item in self.view.children:
            if isinstance(item, HostButton):
                host_button = item
                break
        
        if host_button:
            # Prüfe ob der Benutzer der eingetragene Host ist
            current_host = host_button.label.replace("Host: ", "")
            if current_host == interaction.user.name:
                # Reset Host-Button
                host_button.disabled = False
                host_button.label = "Als Host eintragen"
                host_button.style = discord.ButtonStyle.primary
                
                # Deaktiviere Austragen-Button
                self.disabled = True
                
                # View aktualisieren
                await interaction.message.edit(view=self.view)
                await interaction.response.send_message(
                    f"✅ Du hast dich erfolgreich als Host für den {self.datum} ausgetragen!", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Du kannst dich nur austragen, wenn du der eingetragene Host bist!", 
                    ephemeral=True
                )

class HostplanView(View):
    def __init__(self, datum: str):
        super().__init__(timeout=None)
        self.add_item(HostButton(datum))
        self.add_item(UnregisterButton(datum))

class CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ticket schließen",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Sammle alle Nachrichten für das Log und Statistiken
            messages = []
            message_counts = {}  # Dictionary für Nachrichten pro Benutzer
            total_messages = 0
            first_message = True

            async for message in interaction.channel.history(limit=None, oldest_first=True):
                timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                content = message.content if message.content else "[Embed/Attachment]"
                messages.append(f"[{timestamp}] {message.author}: {content}")

                if first_message:
                    first_message = False
                    continue

                # Zähle Nachrichten pro Benutzer
                author_name = str(message.author)
                message_counts[author_name] = message_counts.get(author_name, 0) + 1
                total_messages += 1

            # Hole die Ticket-Nummer aus dem Kanalnamen
            ticket_number = interaction.channel.name.split('-')[1]

            # Speichere den Chat-Verlauf
            filename = f"ticket_archives/ticket-{ticket_number}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(messages))

            # Sende Log-Nachricht
            log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL)
            if log_channel:
                # Formatiere die Nachrichtenstatistik
                stats_text = f"Gesamt: {total_messages} Nachrichten\n"
                for author, count in message_counts.items():
                    stats_text += f"{author}: {count} Nachrichten\n"

                embed = discord.Embed(
                    title=f"Ticket geschlossen: #{ticket_number}",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Geschlossen von", value=interaction.user.mention, inline=True)
                embed.add_field(name="Kanal", value=f"#{interaction.channel.name}", inline=True)
                embed.add_field(name="Nachrichtenstatistik", value=stats_text, inline=False)
                
                file = discord.File(filename, filename=f"ticket-{ticket_number}.txt")
                await log_channel.send(embed=embed, file=file)

            # Sende Bestätigung und lösche den Kanal
            await interaction.response.send_message("🔒 Ticket wird in 5 Sekunden geschlossen...")
            await asyncio.sleep(5)
            await interaction.channel.delete()

        except Exception as e:
            await interaction.response.send_message(f"❌ Fehler beim Schließen des Tickets: {str(e)}", ephemeral=True)

# Bot-Klasse
class MyBot(commands.Bot):
    def __init__(self, **kwargs):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents, **kwargs)

    async def reload_hostplan_views(self):
        """Lädt die Views für existierende Hostplan-Nachrichten neu"""
        # Warte bis der Bot bereit ist
        await self.wait_until_ready()
        
        # Hole den Team Server
        team_guild = self.get_guild(TEAM_GUILD_ID)
        if not team_guild:
            print(f"❌ Fehler: Team Server (ID: {TEAM_GUILD_ID}) nicht gefunden!")
            return

        # Hole den Hostplan Channel
        hostplan_channel = team_guild.get_channel(HOSTPLAN_CHANNEL_ID)
        if not hostplan_channel:
            print(f"❌ Fehler: Hostplan-Kanal (ID: {HOSTPLAN_CHANNEL_ID}) nicht gefunden!")
            return

        async for message in hostplan_channel.history(limit=100):
            if ":calendar: **Hostplan für" in message.content:
                try:
                    # Extrahiere das Datum aus der Nachricht
                    content_parts = message.content.split(",")
                    if len(content_parts) > 1:
                        weekday = content_parts[0].split("für")[1].strip()
                        date_str = content_parts[1].split("**")[0].strip()
                        datum = f"{weekday}, {date_str}"
                        
                        # Erstelle neue View
                        view = HostplanView(datum)
                        
                        # Überprüfe ob bereits ein Host eingetragen ist
                        if len(message.components) > 0:
                            for component in message.components[0].children:
                                if component.custom_id.startswith("host_") and component.disabled:
                                    # Host ist eingetragen, aktualisiere die View
                                    for item in view.children:
                                        if isinstance(item, HostButton):
                                            item.disabled = True
                                            item.label = component.label
                                            item.style = discord.ButtonStyle.success
                                        elif isinstance(item, UnregisterButton):
                                            item.disabled = False
                        
                        try:
                            # Aktualisiere die Nachricht mit der neuen View
                            await message.edit(view=view)
                            # Erhöhte Verzögerung auf 7 Sekunden
                            await asyncio.sleep(7.0)
                        except discord.errors.HTTPException as e:
                            if e.status == 429:  # Rate limit error
                                retry_after = e.retry_after
                                print(f"Rate limited. Warte {retry_after} Sekunden...")
                                await asyncio.sleep(retry_after + 1)
                                await message.edit(view=view)
                            else:
                                raise e
                        
                except Exception as e:
                    print(f"Fehler beim Laden einer Hostplan-Nachricht: {e}")
        
    async def maintain_hostplan_guide(self):
        """Stellt sicher, dass die Info-Nachricht immer als unterste Nachricht im Channel steht"""
        await self.wait_until_ready()
        
        # Hole den Hostplan-Channel
        hostplan_channel = self.get_channel(HOSTPLAN_CHANNEL_ID)
        if not hostplan_channel:
            print("❌ Hostplan-Channel nicht gefunden!")
            return

        guide_message = """
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
📝 **INFO** 📝
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

Bitte schaut die jeweiligen Tage an, an denen ein ODT gehostet wird.
Überprüfe vorher, ob jemand den Tag schon geclaimt hat.
Wenn nein, trage dich über den Button ein.
Immer zwischen 17:00 Uhr und 20:30 Uhr hosten.
Solltest du dich wieder austragen müssen, nutze den Button daneben.

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"""

        # Hole die letzte Nachricht im Channel
        last_messages = [msg async for msg in hostplan_channel.history(limit=1)]
        last_message = last_messages[0] if last_messages else None

        # Prüfe ob die letzte Nachricht die Info ist
        is_guide_last = last_message and "INFO" in last_message.content

        # Wenn die Info nicht die letzte Nachricht ist
        if not is_guide_last:
            # Lösche alte Info-Nachrichten
            async for message in hostplan_channel.history(limit=100):
                if message.author == self.user and "INFO" in message.content:
                    await message.delete()
                    break

            # Sende neue Info-Nachricht
            try:
                await hostplan_channel.send(guide_message)
            except Exception as e:
                print(f"❌ Fehler beim Senden der Info-Nachricht: {e}")

    async def setup_hook(self):
        print("Bot wird vorbereitet...")
        # Registriere die Views für persistente Buttons
        self.add_view(TicketView())
        self.add_view(CloseView())  # Füge CloseView für persistente Schließen-Buttons hinzu
        
        # Prüfe/erstelle die Ticket-Erstellungsnachricht
        create_channel = self.get_channel(TICKET_CREATE_CHANNEL)
        if create_channel:
            create_message_exists = False
            async for message in create_channel.history(limit=100):
                if (message.author == self.user and 
                    message.embeds and 
                    "🎫 Ticket erstellen" in message.embeds[0].title):
                    create_message_exists = True
                    break

            if not create_message_exists:
                embed = discord.Embed(
                    title="🎫 Ticket erstellen",
                    description="Klicke auf den Button unten, um ein neues Ticket zu erstellen.",
                    color=discord.Color.blue()
                )
                await create_channel.send(embed=embed, view=TicketView())

        # Prüfe/aktualisiere die Settings-Nachricht
        settings_channel = self.get_channel(TICKET_SETTINGS_CHANNEL)
        if settings_channel:
            settings = load_ticket_settings()
            await check_and_update_settings_message(settings_channel, settings, settings_channel.guild)
            
        self.auto_hostplan.start()
        self.loop.create_task(self.reload_hostplan_views())
        self.maintain_hostplan_guide_loop.start()
        print("Bot ist bereit.")

    @tasks.loop(minutes=1)  # Änderung von minutes=10 auf minutes=1
    async def maintain_hostanfrage_guide_loop(self):
        """Überprüft jede Minute die Anleitung zur Hostanfrage"""
        await self.maintain_hostanfrage_guide()

    @maintain_hostanfrage_guide_loop.before_loop
    async def before_maintain_hostanfrage_guide_loop(self):
        """Warte bis der Bot bereit ist"""
        await self.wait_until_ready()

    @tasks.loop(seconds=20)  # Überprüfe alle 20 Sekunden
    async def maintain_hostplan_guide_loop(self):
        """Überprüft alle 20 Sekunden die Info-Nachricht"""
        await self.maintain_hostplan_guide()

    @maintain_hostplan_guide_loop.before_loop
    async def before_maintain_hostplan_guide_loop(self):
        """Warte bis der Bot bereit ist"""
        await self.wait_until_ready()

    @tasks.loop(minutes=1)
    async def auto_hostplan(self):
        try:
            hostplan_channel = self.get_channel(HOSTPLAN_CHANNEL_ID)
            if not hostplan_channel:
                print(f"❌ Fehler: Hostplan-Kanal nicht gefunden!")
                return

            # Sammle existierende Daten mit genauem Datum
            existing_dates = {}
            async for message in hostplan_channel.history(limit=100):
                if ":calendar: **Hostplan für" in message.content:
                    try:
                        # Extrahiere das Datum im Format dd.mm.yyyy
                        content_parts = message.content.split(", ")
                        if len(content_parts) > 1:
                            date_str = content_parts[1].split("**")[0].strip()
                            if "." in date_str:  # Überprüfe ob es ein gültiges Datum ist
                                existing_dates[date_str] = True
                    except:
                        continue

            # Generiere die nächsten 7 Tage
            today = datetime.now().date()
            highlighted_days = ["Montag", "Mittwoch", "Freitag", "Samstag"]
            
            for i in range(8):  # Ändere von range(6) zu range(7)
                date = today + timedelta(days=i)
                date_str = date.strftime("%d.%m.%Y")
                
                # Überprüfe ob dieser Tag bereits existiert
                if date_str not in existing_dates:
                    weekday = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"][date.weekday()]
                    
                    if weekday in highlighted_days:
                        weekday_display = f"**__{weekday}__**"
                        important_note = "\n⭐ **Wichtiger Tag für ODT!**"
                    else:
                        weekday_display = weekday
                        important_note = ""
                    
                    message = f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:calendar: **Hostplan für {weekday_display}, {date_str}** :calendar:{important_note}
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
Klicke auf den Button unter dieser Nachricht, um dich als Host für diesen Tag einzutragen!
"""
                    view = View(timeout=None)
                    view.add_item(HostButton(f"{weekday}, {date_str}"))
                    view.add_item(UnregisterButton(f"{weekday}, {date_str}"))
                    
                    try:
                        await hostplan_channel.send(message, view=view)
                        await asyncio.sleep(8.0)
                    except discord.errors.HTTPException as e:
                        if e.status == 429:  # Rate limit error
                            retry_after = e.retry_after
                            print(f"Rate limited. Warte {retry_after} Sekunden...")
                            await asyncio.sleep(retry_after + 1)
                            await hostplan_channel.send(message, view=view)
                        else:
                            raise e
                    
        except Exception as e:
            print(f"Fehler im Auto-Hostplan: {e}")

    @auto_hostplan.before_loop
    async def before_auto_hostplan(self):
        await self.wait_until_ready()
        # Keine Verzögerung zum Start zu Testzwecken
        # await asyncio.sleep(1)

# Bot starten
bot = MyBot()

async def send_ticket_status(channel, settings, guild):
    # Lösche alte Status-Nachrichten
    async for message in channel.history(limit=100):
        if "🎫 Ticket-System Einstellungen" in message.embeds[0].title if message.embeds else False:
            await message.delete()
            break

    # Formatiere die Benutzer-Liste
    users = []
    for user_id in settings["default_users"]:
        user = guild.get_member(user_id)
        users.append(f"- {user.mention if user else f'<@{user_id}>'}")
    users_text = "\n".join(users) if users else "Keine Standard-Benutzer konfiguriert"

    # Formatiere die Rollen-Liste
    roles = []
    for role_id in settings["default_roles"]:
        role = guild.get_role(role_id)
        roles.append(f"- {role.mention if role else f'<@&{role_id}>'}")
    roles_text = "\n".join(roles) if roles else "Keine Standard-Rollen konfiguriert"

    # Hole die Kategorie
    category = guild.get_channel(settings["category_id"]) if settings["category_id"] else None
    category_text = f"#{category.name}" if category else "Keine Kategorie konfiguriert"

    embed = discord.Embed(
        title="🎫 Ticket-System Einstellungen",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )

    embed.add_field(
        name="📊 Statistiken",
        value=f"Bisher erstellte Tickets: {settings['ticket_counter']}",
        inline=False
    )

    embed.add_field(
        name="👥 Standard-Benutzer",
        value=users_text,
        inline=False
    )

    embed.add_field(
        name="🎭 Standard-Rollen",
        value=roles_text,
        inline=False
    )

    embed.add_field(
        name="📁 Ticket-Kategorie",
        value=category_text,
        inline=False
    )

    embed.add_field(
        name="📝 Log-Kanal",
        value=f"<#{settings['log_channel_id']}>",
        inline=True
    )

    embed.add_field(
        name="📨 Erstellungs-Kanal",
        value=f"<#{settings['ticket_create_channel_id']}>",
        inline=True
    )

    await channel.send(embed=embed)

async def check_and_update_settings_message(channel, settings, guild):
    # Suche nach existierender Settings-Nachricht
    existing_settings = None
    async for message in channel.history(limit=100):
        if message.author == bot.user and message.embeds and "🎫 Ticket-System Einstellungen" in message.embeds[0].title:
            existing_settings = message
            break

    # Erstelle neues Embed mit aktuellen Einstellungen
    new_embed = discord.Embed(
        title="🎫 Ticket-System Einstellungen",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )

    # Formatiere die Benutzer-Liste
    users = []
    for user_id in settings["default_users"]:
        user = guild.get_member(user_id)
        users.append(f"- {user.mention if user else f'<@{user_id}>'}")
    users_text = "\n".join(users) if users else "Keine Standard-Benutzer konfiguriert"

    # Formatiere die Rollen-Liste
    roles = []
    for role_id in settings["default_roles"]:
        role = guild.get_role(role_id)
        roles.append(f"- {role.mention if role else f'<@&{role_id}>'}")
    roles_text = "\n".join(roles) if roles else "Keine Standard-Rollen konfiguriert"

    # Hole die Kategorie
    category = guild.get_channel(settings["category_id"]) if settings["category_id"] else None
    category_text = f"#{category.name}" if category else "Keine Kategorie konfiguriert"

    new_embed.add_field(
        name="📊 Statistiken",
        value=f"Bisher erstellte Tickets: {settings['ticket_counter']}",
        inline=False
    )
    new_embed.add_field(
        name="👥 Standard-Benutzer",
        value=users_text,
        inline=False
    )
    new_embed.add_field(
        name="🎭 Standard-Rollen",
        value=roles_text,
        inline=False
    )
    new_embed.add_field(
        name="📁 Ticket-Kategorie",
        value=category_text,
        inline=False
    )
    new_embed.add_field(
        name="📝 Log-Kanal",
        value=f"<#{settings['log_channel_id']}>",
        inline=True
    )
    new_embed.add_field(
        name="📨 Erstellungs-Kanal",
        value=f"<#{settings['ticket_create_channel_id']}>",
        inline=True
    )

    if existing_settings:
        # Vergleiche ob sich etwas geändert hat
        old_embed = existing_settings.embeds[0]
        if (len(old_embed.fields) != len(new_embed.fields) or
            any(old_embed.fields[i].value != new_embed.fields[i].value 
                for i in range(len(new_embed.fields)))):
            # Aktualisiere die existierende Nachricht
            await existing_settings.edit(embed=new_embed)
    else:
        # Keine existierende Nachricht gefunden, sende eine neue
        await channel.send(embed=new_embed)

# Modifiziere die on_ready Funktion
@bot.event
async def on_ready():
    try:
        print("Bot wird vorbereitet...")
        print(f'Eingeloggt als {bot.user}')
        print("\nSynchronisiere Commands...")
        
        # Sync commands für den Hauptserver
        synced_main = await bot.tree.sync(guild=discord.Object(id=MAIN_GUILD_ID))
        
        # Sync commands für den Team Server
        synced_team = await bot.tree.sync(guild=discord.Object(id=TEAM_GUILD_ID))
        
        # Detaillierte Auflistung der Commands
        print("\n🔄 Synchronisierte Commands für Hauptserver:")
        for cmd in synced_main:
            print(f"  ✓ /{cmd.name} - {cmd.description}")
        
        print(f"\n✅ {len(synced_main)} Befehle für Hauptserver synchronisiert\n")
        
        print("🔄 Synchronisierte Commands für Team Server:")
        for cmd in synced_team:
            print(f"  ✓ /{cmd.name} - {cmd.description}")
        
        print(f"\n✅ {len(synced_team)} Befehle für Team Server synchronisiert")

        # Überprüfe und aktualisiere die Settings-Nachricht
        settings_channel = bot.get_channel(TICKET_SETTINGS_CHANNEL)
        if settings_channel:
            settings = load_ticket_settings()
            await check_and_update_settings_message(settings_channel, settings, settings_channel.guild)

        # Registriere die Ticket-View für persistente Buttons
        bot.add_view(TicketView())

        print(f'\n🚀 Bot ist vollständig initialisiert und einsatzbereit!')
    except Exception as e:
        print(f"❌ Fehler beim Synchronisieren der Commands: {e}")

@bot.event
async def on_member_join(member: discord.Member):
    try:
        # Prüfe ob es der Hauptserver ist
        if member.guild.id != MAIN_GUILD_ID:
            return

        # Channel-ID für Willkommensnachricht
        WELCOME_CHANNEL_ID = 1320474004770918452
        MEMBER_ROLE_ID = 1320475936721862792

        # Willkommensnachricht senden
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            welcome_message = f"""
Ein wildes {member.mention} ist erschienen! :llama:
Wir freuen uns, dich bei uns zu haben. Schau dich gerne um und hab viel Spaß! :star2:
"""
            try:
                await channel.send(welcome_message)
                print(f"✅ Willkommensnachricht für {member.name} wurde gesendet")
            except Exception as e:
                print(f"❌ Fehler beim Senden der Willkommensnachricht für {member.name}: {str(e)}")
        else:
            print(f"❌ Willkommens-Channel (ID: {WELCOME_CHANNEL_ID}) nicht gefunden!")

        # Rolle zuweisen
        role = member.guild.get_role(MEMBER_ROLE_ID)
        if role:
            try:
                await member.add_roles(role, reason="Automatische Zuweisung bei Beitritt")
                print(f"✅ Rolle {role.name} wurde {member.name} zugewiesen")
            except discord.Forbidden:
                print(f"❌ Keine Berechtigung, um die Rolle {role.name} an {member.name} zu vergeben")
            except Exception as e:
                print(f"❌ Fehler beim Zuweisen der Rolle {role.name} an {member.name}: {str(e)}")
        else:
            print(f"❌ Mitglieder-Rolle (ID: {MEMBER_ROLE_ID}) nicht gefunden!")

    except Exception as e:
        print(f"❌ Unerwarteter Fehler in on_member_join für {member.name}: {str(e)}")

# Eventankündigung
@bot.tree.command(name="eventankündigung", description="Erstellt eine Event-Ankündigung", guild=discord.Object(id=MAIN_GUILD_ID))
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
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:milky_way: **Moon-Titan-{spielmodus}** ({eventnummer}) :milky_way:
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

:earth_africa: 》**Server-IP:** Titan-Event.de
:alarm_clock: 》**Start:** {time_info}
:busts_in_silhouette: 》**Teams of:** {teamgröße}
:shirt: 》**Kit:** {kit} :llama:
:bust_in_silhouette: 》**Host:** {host}

:bow_and_arrow: 》**Mods:** https://discord.com/channels/1320473550259228682/1320476122843971624
:scroll: 》**Regeln:** ⁠https://discord.com/channels/1320473550259228682/1320475971442311248
:warning: 》**Discord:** [**Hier klicken!**](https://discord.gg/8nYke2CBTR)
:exclamation: 》**Der Server öffnet 15 Minuten vor Start!**

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
||@everyone|| 
-# https://spexhosting.de/
"""

    def reminder_15min_message():
        return f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:milky_way: **Moon-Titan-{spielmodus}** ({eventnummer}) :milky_way:
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

:earth_africa: 》**Server-IP:** Titan-Event.de
:alarm_clock: 》**Start:** {uhrzeit} Uhr (in 15 Minuten)
:busts_in_silhouette: 》**Teams of:** {teamgröße}
:shirt: 》**Kit:** {kit} :llama:

:warning: 》**Discord:** [**Hier klicken!**](https://discord.gg/8nYke2CBTR)
:white_check_mark: 》**Der Server ist jetzt geöffnet!**

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
||@everyone|| 
-# https://spexhosting.de/
"""

    def reminder_5min_message():
        return f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:milky_way: **Moon-Titan-{spielmodus}** ({eventnummer}) :milky_way:
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

:rotating_light: **Event startet in 5 Minuten!** :rotating_light:

:earth_africa: 》**Server-IP:** Titan-Event.de
:warning: 》**Discord:** [**Hier klicken!**](https://discord.gg/8nYke2CBTR)

:arrow_right: Macht euch bereit! Viel Erfolg allen Teams! :trophy:

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


@bot.tree.command(name="anmelden", description="Melde dein Team für das Event an!", guild=discord.Object(id=MAIN_GUILD_ID))
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
                  guild=discord.Object(id=MAIN_GUILD_ID))
@app_commands.describe(
    eventnummer="Die Eventnummer",
    teamname="Der Name des Teams",
    kills="Anzahl der Kills des Teams",
    spieler="Die Spieler im Team (Trenne sie mit Kommas)",
    host="Name des Hosts",
    eventart="Art des Events (OneDayTitan oder Meetup)"
)
@app_commands.choices(
    eventart=[
        app_commands.Choice(name="OneDayTitan", value="OneDayTitan"),
        app_commands.Choice(name="Meetup", value="Meetup")
    ]
)
async def winner(
        interaction: discord.Interaction,
        eventnummer: str,
        teamname: str,
        kills: int,
        spieler: str,
        host: str,
        eventart: app_commands.Choice[str]
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: Winner Nachricht für Event #{eventnummer}")
    if interaction.channel.id != EVENTS_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ **Fehler:** Dieser Befehl kann nur im Event-Kanal verwendet werden!", 
            ephemeral=True
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

    # Aktualisiere die Host-Statistiken
    stats = update_host_statistics(host, eventart.value)
    
    # Format statistics message
    stats_message = format_host_statistics()

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

{stats_message}
"""

    # Sende die Gewinner-Nachricht im Event-Channel
    await events_channel.send(winner_message)

    # Sende die Statistiken im Statistik-Kanal
    await statistics_channel.send(statistics_message)

    # Bestätigungsnachricht an den Benutzer
    await interaction.response.send_message(
        f"✅ **Der Gewinner für Event #{eventnummer} und die Statistiken wurden gepostet!**", ephemeral=True)


@bot.tree.command(name="ticket", description="Erstellt interaktiven Knöpfe zum antworten auf Ticket-Anfragen",
                  guild=discord.Object(id=MAIN_GUILD_ID))
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


@bot.tree.command(name="leitfaden", description="Sendet Info Nachricht", guild=discord.Object(id=MAIN_GUILD_ID))
@app_commands.describe()
async def leitfaden(interaction: discord.Interaction):
    allowed_roles = [TEAM_ROLE_ID]
    if isinstance(interaction.user, discord.Member):
        user_roles = [role.id for role in interaction.user.roles]
    else:
        await interaction.response.send_message("❌ Fehler: Konnte deine Rollen nicht abrufen.", ephemeral=True)
        return

    if not any(role in allowed_roles for role in user_roles):
        await interaction.response.send_message("❌ Du hast nicht die benötigte Rolle, um diesen Befehl auszuführen!", ephemeral=True)
        return

    leitfade_message = f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:milky_way: **Moon-Titan Bot - Befehle & Funktionen** :milky_way:
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

:robot: **Event-Management**
• `/eventankündigung` - Erstellt eine Event-Ankündigung mit Countdown
• `/winner` - Verkündet den Gewinner eines Events
• `/hostvorschlag` - Schlägt ein Event vor
• `/hostplan` - Erstellt einen 7-Tage-Hostplan (Team-Server)

:ticket: **Ticket-System**
• `/ticket` - Erstellt Interaktions-Buttons für Tickets
• `/ticketsetup` - Richtet das Ticket-System ein
• `/ticketsettings` - Konfiguriert das Ticket-System
• `/ticketsetupstatus` - Zeigt aktuelle Ticket-Einstellungen

:pencil: **Team-Tools**
• `/message` - Sendet eine formatierte Nachricht als Bot
• `/delete` - Löscht Nachrichten (mit Filtern für Zeit/Benutzer)

:clipboard: **Event-Organisation**
• `/anmelden` - Meldet ein Team für ein Event an
• `/bug` - Meldet einen Bug
• `/hallo` - Sendet eine Begrüßung
• `/danke` - Zeigt Credits für den Bot

:information_source: **Wichtige Links**
• Team-Discord: https://discord.gg/tcQryrGQ9S
• Hostanleitung: Siehe #📌┆hostanleitung

:warning: **Hinweise**
• Ticketbefehle nur in den dafür vorgesehenen Kanälen
• Event-Ankündigungen nur im Events-Kanal
• Bei Fragen: Team-Chat oder Support-Ticket nutzen

:link: **Arbeitsabläufe**
1. Events werden im Hostplan eingetragen
2. Ankündigungen erfolgen über /eventankündigung
3. Teams melden sich über /anmelden an
4. Nach Event: Gewinner mit /winner verkünden

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
"""

    # Sende eine Nachricht
    await interaction.response.send_message(leitfade_message)


@bot.tree.command(name="hallo", description="Sagt hallo", guild=discord.Object(id=MAIN_GUILD_ID))
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

# Neue Modal-Klasse für Nachrichten
class MessageModal(discord.ui.Modal, title="Nachricht senden"):
    message_content = discord.ui.TextInput(
        label="Deine Nachricht",
        style=discord.TextStyle.paragraph,
        placeholder="Gib hier die Nachricht ein, die der Bot senden soll...",
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Deine Nachricht wurde erfolgreich gesendet!", ephemeral=True)
        await interaction.channel.send(self.message_content.value)

@bot.tree.command(name="message", 
                  description="Ein Formular öffnet sich, in dem du deine Nachricht eingeben kannst, die dann vom Bot gesendet wird.",
                  guilds=[discord.Object(id=MAIN_GUILD_ID), discord.Object(id=TEAM_GUILD_ID)])
async def message(interaction: discord.Interaction):
    allowed_roles = [TEAM_ROLE_ID]
    if isinstance(interaction.user, discord.Member):
        user_roles = [role.id for role in interaction.user.roles]
    else:
        await interaction.response.send_message("❌ Fehler: Konnte deine Rollen nicht abrufen.", ephemeral=True)
        return

    if not any(role in allowed_roles for role in user_roles):
        await interaction.response.send_message("❌ Du hast nicht die benötigte Rolle, um diesen Befehl auszuführen!", 
                                              ephemeral=True)
        return

    # Uhrzeit und Kanalinfos für Logging
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    # Print-Anweisung für Debugging
    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: Lässt lama_bot eine Nachricht senden")

    # Modal-Formular anzeigen
    await interaction.response.send_modal(MessageModal())

@bot.tree.command(name="bug", description="meldet einen Bug", guild=discord.Object(id=MAIN_GUILD_ID))
@app_commands.describe(nachricht = "Bug der gemeldet werden soll")
async def bug(interaction: discord.Interaction, nachricht: str):
    bugs_channel = bot.get_channel(BUGS_CHANNEL_ID)
    if not bugs_channel:
        await interaction.response.send_message("❌ **Fehler:** Bug-Report-Kanal nicht gefunden!", ephemeral=True)
        return
    
    # Uhrzeit und Kanalinfos
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    # Print-Anweisung für Debugging
    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: meldet '{nachricht}' als Bug")

    # Formatierte Bug-Meldung
    bug_message = f"""🐛 **Neue Bug-Meldung**
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
👤 **Gemeldet von:** {interaction.user}
📝 **Beschreibung:** {nachricht}
⏰ **Zeitpunkt:** {now}
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"""

    # Sende eine Nachricht
    await interaction.response.send_message("✅ Vielen Dank für deine Meldung. Das Team wird sich so schnell wie möglich um den Bug kümmern!", ephemeral=True)
    await bugs_channel.send(bug_message)

@bot.tree.command(name="danke", description="Danke an die Ersteller sagen", guild=discord.Object(id=MAIN_GUILD_ID))
async def danke(interaction: discord.Interaction):
    # Uhrzeit und Kanalinfos
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = interaction.channel.id if interaction.channel else "Unbekannt"
    user_name = interaction.user.name

    # Print-Anweisung für Debugging
    print(f"Wann: {now}, Wo: Kanal-ID: {channel_id}, Wer: {user_name}, Was: sendet Dank an die Ersteller")

    # Danksagung formatieren
    danke_message = f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:star: **Danke an die Ersteller** :star:
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

:wave: Ein großes Dankeschön an die Entwickler des Bots:

:computer: **Lama** & **Clazy**
Für ihre unermüdliche Arbeit und ihr Engagement!

:gift: Falls ihr ihre Arbeit unterstützen möchtet:
:moneybag: Sendet Clazy per DM Paysafekarten

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:heart: Danke für eure Unterstützung! :llama:
"""

    # Sende die Danksagung
    await interaction.response.send_message(danke_message)

@bot.tree.command(name="hostplan", description="Erstellt den Hostplan für die nächsten 7 Tage", guild=discord.Object(id=TEAM_GUILD_ID))
async def hostplan(interaction: discord.Interaction):
    # Nur Team-Mitglieder dürfen den Command ausführen
    allowed_roles = [TEAM_ROLE_ID]
    if isinstance(interaction.user, discord.Member):
        user_roles = [role.id for role in interaction.user.roles]
    else:
        await interaction.response.send_message("❌ Fehler: Konnte deine Rollen nicht abrufen.", ephemeral=True)
        return

    if not any(role in allowed_roles for role in user_roles):
        await interaction.response.send_message("❌ Du hast nicht die benötigte Rolle, um diesen Befehl auszuführen!", ephemeral=True)
        return

    # Zuerst die Interaction beantworten
    await interaction.response.send_message("⏳ Erstelle den Hostplan für die nächsten 7 Tage...", ephemeral=True)

    # Hole den Team Server
    team_guild = bot.get_guild(TEAM_GUILD_ID)
    if not team_guild:
        await interaction.followup.send("❌ Fehler: Team Server nicht gefunden!", ephemeral=True)
        return

    # Channel ID für den Hostplan
    hostplan_channel = team_guild.get_channel(HOSTPLAN_CHANNEL_ID)
    if not hostplan_channel:
        await interaction.followup.send("❌ Fehler: Hostplan-Kanal nicht gefunden!", ephemeral=True)
        return

    # Nächsten 7 Tage generieren
    today = datetime.now().date()
    dates = [today + timedelta(days=i) for i in range(7)]
    
    try:
        # Für jeden Tag eine Nachricht mit Button erstellen
        for date in dates:
            try:
                # Formatiere das Datum
                date_str = date.strftime("%d.%m.%Y")
                weekday = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"][date.weekday()]
                
                # Erstelle die Nachricht
                message = f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:calendar: **Hostplan für {weekday}, {date_str}** :calendar:
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
Klicke auf den Button unter dieser Nachricht, um dich als Host für diesen Tag einzutragen!
"""
                view = View(timeout=None)
                view.add_item(HostButton(f"{weekday}, {date_str}"))
                view.add_item(UnregisterButton(f"{weekday}, {date_str}"))
                
                try:
                    # Sende die Nachricht
                    await hostplan_channel.send(message, view=view)
                    # Erhöhe die Wartezeit zwischen den Nachrichten auf 8 Sekunden
                    await asyncio.sleep(8.0)
                except discord.errors.HTTPException as e:
                    if e.status == 429:  # Rate limit error
                        retry_after = e.retry_after
                        print(f"Rate limited. Warte {retry_after} Sekunden...")
                        await asyncio.sleep(retry_after + 1)
                        await hostplan_channel.send(message, view=view)
                    else:
                        raise e
                
            except Exception as e:
                print(f"Fehler beim Erstellen des Hostplans für {date_str}: {e}")
                continue
        
        # Sende Erfolgsmeldung
        await interaction.followup.send("✅ Der Hostplan für die nächsten 7 Tage wurde erfolgreich erstellt!", ephemeral=True)
        
    except Exception as e:
        # Bei einem Fehler informiere den Benutzer
        error_message = f"❌ Fehler beim Erstellen des Hostplans: {str(e)}"
        await interaction.followup.send(error_message, ephemeral=True)

@bot.tree.command(name="hostvorschlag", description="Schlage ein Event vor", guild=discord.Object(id=MAIN_GUILD_ID))
@app_commands.describe(
    eventart="Wähle die Art des Events",
    uhrzeit="Startzeit im Format HH:MM",
    teamgroesse="Wähle die Teamgröße",
    kit="Wähle das Kit für das Event"
)
@app_commands.choices(
    eventart=[
        app_commands.Choice(name="OneDayTitan", value="OneDayTitan"),
        app_commands.Choice(name="Meetup", value="Meetup")
    ],
    teamgroesse=[
        app_commands.Choice(name="Solo (1)", value="1"),
        app_commands.Choice(name="Duo (2)", value="2"),
        app_commands.Choice(name="Trio (3)", value="3"),
        app_commands.Choice(name="Squad (4)", value="4")
    ]
)
async def hostvorschlag(
    interaction: discord.Interaction,
    eventart: app_commands.Choice[str],
    uhrzeit: str,
    teamgroesse: app_commands.Choice[str],
    kit: str
):
    if interaction.channel.id != HOSTVORSCHLAG_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ **Fehler:** Dieser Befehl kann nur im Host-Vorschlag-Kanal verwendet werden!", 
            ephemeral=True
        )
        return

    # Validiere das Uhrzeitformat (HH:MM)
    try:
        datetime.strptime(uhrzeit, "%H:%M")
    except ValueError:
        await interaction.response.send_message(
            "❌ **Fehler:** Bitte gib die Uhrzeit im Format HH:MM ein (z.B. 18:30)!", 
            ephemeral=True
        )
        return

    # Validiere das Kit basierend auf der Eventart
    meetup_kits = ["NoBooks", "Upgradeable", "Nether Pants", "Quick", "Cave Rush", "Midgame", 
                   "Midgame + Poison", "Stacked", "Overstacked"]
    odt_kits = ["ODT-Stacked", "ODT-Normal", "ODT-Primitive"]
    
    valid_kits = meetup_kits if eventart.value == "Meetup" else odt_kits
    if kit not in valid_kits:
        await interaction.response.send_message(
            f"❌ **Fehler:** Ungültiges Kit für {eventart.value}!\nErlaubte Kits: {', '.join(valid_kits)}", 
            ephemeral=True
        )
        return

    # Erstelle die formatierte Nachricht für den Hauptserver
    vorschlag_message = f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:scroll: **Event-Vorschlag** :scroll:
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

:game_die: **Event:** {eventart.value}
:alarm_clock: **Uhrzeit:** {uhrzeit} Uhr
:busts_in_silhouette: **Teamgröße:** {teamgroesse.value}
:shield: **Kit:** {kit}

:bust_in_silhouette: **Vorgeschlagen von:** {interaction.user.mention}

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:thumbsup: Reagiere mit 👍 wenn du dabei wärst!
"""

    # Sende die Nachricht im Hauptserver und füge die Reaktion hinzu
    message = await interaction.channel.send(vorschlag_message)
    await message.add_reaction("👍")

    # Erstelle die formatierte Nachricht für den Team Server
    team_message = f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
:bell: **Neuer Event-Vorschlag** :bell:
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

:game_die: **Event:** {eventart.value}
:alarm_clock: **Uhrzeit:** {uhrzeit} Uhr
:busts_in_silhouette: **Teamgröße:** {teamgroesse.value}
:shield: **Kit:** {kit}

:bust_in_silhouette: **Vorgeschlagen von:** {interaction.user.mention}
:link: **Link zur Vorschlagsnachricht:** {message.jump_url}

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
<@&{HOST_ROLE_ID}> :eyes: Bitte überprüft den Vorschlag!
"""

    # Sende die Nachricht im Team Discord
    team_channel = bot.get_channel(TEAM_VORSCHLAG_CHANNEL_ID)
    if team_channel:
        await team_channel.send(team_message)
    
    # Bestätige dem Benutzer
    await interaction.response.send_message(
        "✅ Dein Event-Vorschlag wurde erfolgreich erstellt!", 
        ephemeral=True
    )

@hostvorschlag.autocomplete('kit')
async def kit_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    # Bestimme die verfügbaren Kits basierend auf der ausgewählten Eventart
    eventart = None
    for option in interaction.data.get('options', []):
        if option['name'] == 'eventart':
            eventart = option['value']
            break

    if eventart == "Meetup":
        kits = ["NoBooks", "Upgradeable", "Nether Pants", "Quick", "Cave Rush", "Midgame", 
                "Midgame + Poison", "Stacked", "Overstacked"]
    else:  # OneDayTitan
        kits = ["ODT-Stacked", "ODT-Normal", "ODT-Primitive"]

    # Filtere die Kits basierend auf der aktuellen Eingabe
    return [
        app_commands.Choice(name=kit, value=kit)
        for kit in kits if current.lower() in kit.lower()
    ]

@bot.event
async def on_message_delete(message: discord.Message):
    # Prüfe ob die Nachricht aus einem der überwachten Channels kommt
    if message.channel.id in TRACKED_CHANNELS:
        # Hole den Log Channel
        log_channel = bot.get_channel(MESSAGE_LOG_CHANNEL)
        if not log_channel:
            return

        # Formatierte Nachricht erstellen
        embed = discord.Embed(
            title="Message Deleted",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # Füge die gelöschte Nachricht hinzu
        embed.add_field(name="Deleted Message", value=message.content or "Deleted Message", inline=False)
        
        # Channel Information
        embed.add_field(name="Channel", value=f"# {message.channel.name}", inline=False)
        
        # Author Information
        embed.add_field(name="Author", value=f"{message.author} ({message.author.id})", inline=True)
        embed.add_field(name="Author Type", value="Human", inline=True)

        # Sende die Log-Nachricht
        await log_channel.send(embed=embed)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    # Prüfe ob die Nachricht aus einem der überwachten Channels kommt
    if before.channel.id in TRACKED_CHANNELS:
        # Ignoriere Nachrichten die sich nicht wirklich geändert haben
        if before.content == after.content:
            return

        # Hole den Log Channel
        log_channel = bot.get_channel(MESSAGE_LOG_CHANNEL)
        if not log_channel:
            return

        # Formatierte Nachricht erstellen
        embed = discord.Embed(
            title="Message Edited",
            color=discord.Color.yellow(),
            timestamp=datetime.now()
        )
        
        # Füge die alte und neue Nachricht hinzu
        embed.add_field(name="Before", value=before.content, inline=False)
        embed.add_field(name="After", value=after.content, inline=False)
        
        # Channel Information
        embed.add_field(name="Channel", value=f"# {before.channel.name}", inline=False)
        
        # Author Information
        embed.add_field(name="Author", value=f"{before.author} ({before.author.id})", inline=True)
        embed.add_field(name="Author Type", value="Human", inline=True)

        # Link zur Nachricht
        embed.add_field(name="Message Link", value=f"[Jump to Message]({after.jump_url})", inline=False)

        # Sende die Log-Nachricht
        await log_channel.send(embed=embed)

@bot.tree.command(name="delete", description="Löscht Nachrichten im aktuellen Kanal", 
                  guilds=[discord.Object(id=MAIN_GUILD_ID), discord.Object(id=TEAM_GUILD_ID)])
@app_commands.describe(
    anzahl="Anzahl der zu löschenden Nachrichten",
    zeitspanne="Zeitspanne in Stunden (alternativ zur Anzahl)",
    benutzer="Optional: Einer oder mehrere Benutzer, deren Nachrichten gelöscht werden sollen (durch Komma getrennt)"
)
async def delete(
    interaction: discord.Interaction,
    anzahl: int = None,
    zeitspanne: float = None,
    benutzer: str = None
):
    # Erlaube alle Befehle auf dem Team-Server ohne Rollenprüfung
    if interaction.guild_id == TEAM_GUILD_ID:
        pass  # Keine Berechtigungsprüfung auf dem Team-Server
    else:
        # Auf dem Hauptserver nur mit Team-Rolle
        if not any(role.id == TEAM_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ Du hast nicht die benötigte Rolle, um diesen Befehl auszuführen!", ephemeral=True)
            return

    if anzahl is None and zeitspanne is None:
        await interaction.response.send_message("❌ Bitte gib entweder eine Anzahl oder eine Zeitspanne an!", ephemeral=True)
        return

    if anzahl is not None and zeitspanne is not None:
        await interaction.response.send_message("❌ Bitte gib entweder nur eine Anzahl oder nur eine Zeitspanne an!", ephemeral=True)
        return

    # Verarbeite Benutzer-Filter
    target_users = []
    if benutzer:
        user_names = [name.strip() for name in benutzer.split(",")]
        target_users = []
        for name in user_names:
            # Suche nach Benutzern im Server
            member = discord.utils.get(interaction.guild.members, name=name)
            if member:
                target_users.append(member)
            else:
                await interaction.response.send_message(f"❌ Benutzer '{name}' nicht gefunden!", ephemeral=True)
                return

    # Bestätige den Start des Löschvorgangs
    await interaction.response.send_message("🗑️ Lösche Nachrichten...", ephemeral=True)

    try:
        def check_message(message):
            # Wenn Benutzer angegeben wurden, prüfe ob die Nachricht von einem der Benutzer stammt
            if target_users and message.author not in target_users:
                return False
            return True

        if zeitspanne is not None:
            # Lösche Nachrichten basierend auf Zeitspanne
            time_threshold = datetime.now() - timedelta(hours=zeitspanne)
            deleted = await interaction.channel.purge(
                limit=1000,  # Sicherheitslimit
                check=check_message,
                after=time_threshold
            )
        else:
            # Lösche Nachrichten basierend auf Anzahl
            deleted = await interaction.channel.purge(
                limit=anzahl + 1,  # +1 weil die Command-Nachricht auch gelöscht wird
                check=check_message
            )

        # Sende Bestätigung
        users_str = f" von {', '.join([str(user) for user in target_users])}" if target_users else ""
        await interaction.followup.send(
            f"✅ {len(deleted)} Nachrichten{users_str} wurden erfolgreich gelöscht!", 
            ephemeral=True
        )

        # Logging der Aktion
        log_channel = bot.get_channel(MESSAGE_LOG_CHANNEL)
        if log_channel:
            embed = discord.Embed(
                title="Bulk Delete",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Moderator", value=str(interaction.user), inline=True)
            embed.add_field(name="Channel", value=f"#{interaction.channel.name}", inline=True)
            embed.add_field(name="Deleted Messages", value=str(len(deleted)), inline=True)
            if target_users:
                embed.add_field(name="Target Users", value=", ".join([str(user) for user in target_users]), inline=False)
            await log_channel.send(embed=embed)

    except discord.Forbidden:
        await interaction.followup.send("❌ Ich habe keine Berechtigung, Nachrichten zu löschen!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Fehler beim Löschen der Nachrichten: {str(e)}", ephemeral=True)

# Modifiziere die ticketsetup Funktion für die initiale Button-Nachricht
@bot.tree.command(name="ticketsetup", description="Erstellt die Ticket-Erstellungsnachricht", guild=discord.Object(id=MAIN_GUILD_ID))
async def ticketsetup(interaction: discord.Interaction):
    # Berechtigungsprüfung für Team-Mitglieder
    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("❌ Fehler: Konnte deine Rollen nicht abrufen.", ephemeral=True)
        return

    if not any(role.id == TEAM_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("❌ Du hast nicht die benötigte Rolle, um diesen Befehl auszuführen!", ephemeral=True)
        return

    channel = bot.get_channel(TICKET_CREATE_CHANNEL)
    if not channel:
        await interaction.response.send_message("❌ Ticket-Kanal nicht gefunden!", ephemeral=True)
        return

    # Erstelle das Embed für die Ticket-Erstellung
    embed = discord.Embed(
        title="🎫 Ticket erstellen",
        description="Klicke auf den Button unten, um ein neues Ticket zu erstellen.",
        color=discord.Color.blue()
    )

    # Sende die Nachricht mit den Buttons
    await channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ Ticket-System wurde eingerichtet!", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Support-Ticket",
        style=discord.ButtonStyle.primary,
        emoji="❓",
        custom_id="create_support_ticket"
    )
    async def create_support_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "support")

    @discord.ui.button(
        label="Bewerbungsticket",
        style=discord.ButtonStyle.success,
        emoji="📝",
        custom_id="create_application_ticket"
    )
    async def create_application_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "application")

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        try:
            settings = load_ticket_settings()
            settings["ticket_counter"] += 1
            ticket_number = settings["ticket_counter"]
            save_ticket_settings(settings)

            # Formatierte Ticket-Nummer (z.B. 001, 002, etc.)
            formatted_number = str(ticket_number).zfill(3)
            ticket_prefix = "support" if ticket_type == "support" else "bewerbung"
            channel_name = f"ticket-{ticket_prefix}-{formatted_number}"

            # Erstelle Kanal-Overwrites
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            # Füge Standard-Berechtigungen hinzu
            for user_id in settings["default_users"]:
                user = interaction.guild.get_member(user_id)
                if user:
                    overwrites[user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            for role_id in settings["default_roles"]:
                role = interaction.guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            # Erstelle den Ticket-Kanal
            category = None
            if settings["category_id"]:
                category = interaction.guild.get_channel(settings["category_id"])

            ticket_channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites
            )

            # Erstelle die passende Willkommensnachricht
            if ticket_type == "support":
                title = "Support-Ticket"
                description = f"Hallo {interaction.user.mention}!\nBitte beschreibe dein Anliegen. Ein Teammitglied wird sich so schnell wie möglich um dich kümmern."
            else:
                title = "Bewerbungsticket"
                description = f"Hallo {interaction.user.mention}!\nBitte stelle dich vor und beschreibe, warum du dich für das Team bewerben möchtest. Ein Teammitglied wird sich so schnell wie möglich bei dir melden."

            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"Ticket-ID: #{formatted_number}")
            
            await ticket_channel.send(embed=embed, view=CloseView())
            await interaction.response.send_message(
                f"✅ Dein {title} wurde erstellt: {ticket_channel.mention}",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich habe keine Berechtigung, Ticket-Kanäle zu erstellen!", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Fehler beim Erstellen des Tickets: {str(e)}", 
                ephemeral=True
            )

@bot.tree.command(
    name="ticketsettings",
    description="Konfiguriere das Ticket-System",
    guild=discord.Object(id=MAIN_GUILD_ID)
)
@app_commands.describe(
    action="Die Aktion die ausgeführt werden soll",
    target="@Rolle, Rollen-ID oder Rollenname für Rollen / @User oder User-ID für Benutzer"
)
@app_commands.choices(action=[
    app_commands.Choice(name="Füge Standard-User hinzu", value="add_user"),
    app_commands.Choice(name="Entferne Standard-User", value="remove_user"),
    app_commands.Choice(name="Füge Standard-Rolle hinzu", value="add_role"),
    app_commands.Choice(name="Entferne Standard-Rolle", value="remove_role"),
    app_commands.Choice(name="Setze Ticket-Kategorie", value="set_category")
])
async def ticketsettings(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    target: str
):
    if interaction.channel.id != TICKET_SETTINGS_CHANNEL:
        await interaction.response.send_message(
            "❌ Dieser Befehl kann nur im Ticket-Einstellungen Kanal verwendet werden!",
            ephemeral=True
        )
        return

    settings = load_ticket_settings()
    
    try:
        if action.value in ["add_user", "remove_user"]:
            user_id = None
            # Versuche zuerst die Mention zu extrahieren
            if interaction.data.get('resolved', {}).get('users'):
                user_id = int(list(interaction.data['resolved']['users'].keys())[0])
            else:
                # Wenn keine Mention, versuche die ID zu parsen
                try:
                    user_id = int(target)
                except ValueError:
                    # Wenn keine ID, suche nach dem Benutzernamen
                    member = discord.utils.get(interaction.guild.members, name=target)
                    if member:
                        user_id = member.id

            if not user_id:
                await interaction.response.send_message(
                    "❌ Benutzer nicht gefunden! Versuche den Benutzer zu erwähnen (@User) oder nutze die User-ID.",
                    ephemeral=True
                )
                return

            if action.value == "add_user":
                if user_id not in settings["default_users"]:
                    settings["default_users"].append(user_id)
                    message = f"✅ Benutzer <@{user_id}> wurde zu den Standard-Benutzern hinzugefügt!"
                else:
                    message = "❌ Dieser Benutzer ist bereits in der Liste!"
            else:  # remove_user
                if user_id in settings["default_users"]:
                    settings["default_users"].remove(user_id)
                    message = f"✅ Benutzer <@{user_id}> wurde von den Standard-Benutzern entfernt!"
                else:
                    message = "❌ Dieser Benutzer ist nicht in der Liste!"

        elif action.value in ["add_role", "remove_role"]:
            role = None
            # Versuche zuerst die Mention zu extrahieren
            if interaction.data.get('resolved', {}).get('roles'):
                role_id = int(list(interaction.data['resolved']['roles'].keys())[0])
                role = interaction.guild.get_role(role_id)
            else:
                # Wenn keine Mention, versuche die ID zu parsen
                try:
                    role_id = int(target)
                    role = interaction.guild.get_role(role_id)
                except ValueError:
                    # Wenn keine ID, suche nach dem Rollennamen
                    role = discord.utils.get(interaction.guild.roles, name=target)

            if not role:
                await interaction.response.send_message(
                    "❌ Rolle nicht gefunden! Versuche die Rolle zu erwähnen (@Rolle) oder nutze den exakten Rollennamen.",
                    ephemeral=True
                )
                return

            if action.value == "add_role":
                if role.id not in settings["default_roles"]:
                    settings["default_roles"].append(role.id)
                    message = f"✅ Rolle {role.mention} wurde zu den Standard-Rollen hinzugefügt!"
                else:
                    message = "❌ Diese Rolle ist bereits in der Liste!"
            else:  # remove_role
                if role.id in settings["default_roles"]:
                    settings["default_roles"].remove(role.id)
                    message = f"✅ Rolle {role.mention} wurde von den Standard-Rollen entfernt!"
                else:
                    message = "❌ Diese Rolle ist nicht in der Liste!"

        elif action.value == "set_category":
            try:
                # Versuche zuerst als ID zu parsen
                try:
                    category_id = int(target)
                    category = interaction.guild.get_channel(category_id)
                except ValueError:
                    # Wenn keine ID, suche nach dem Kategorienamen
                    category = discord.utils.get(interaction.guild.categories, name=target)

                if category and isinstance(category, discord.CategoryChannel):
                    settings["category_id"] = category.id
                    message = f"✅ Ticket-Kategorie wurde auf {category.name} gesetzt!"
                elif target.lower() in ["0", "none", "keine"]:
                    settings["category_id"] = None
                    message = "✅ Ticket-Kategorie wurde entfernt!"
                else:
                    message = "❌ Ungültige Kategorie! Nutze die Kategorie-ID oder den exakten Namen."
            except ValueError:
                message = "❌ Bitte gib eine gültige Kategorie-ID oder einen Namen an!"

        save_ticket_settings(settings)
        await send_ticket_status(interaction.channel, settings, interaction.guild)
        await interaction.response.send_message(message, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Ein Fehler ist aufgetreten: {str(e)}", ephemeral=True)

@bot.tree.command(
    name="ticketsetupstatus",
    description="Zeigt die aktuellen Ticket-System Einstellungen an",
    guild=discord.Object(id=MAIN_GUILD_ID)
)
async def ticketsetupstatus(interaction: discord.Interaction):
    # Nur Team-Mitglieder dürfen den Command ausführen
    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("❌ Fehler: Konnte deine Rollen nicht abrufen.", ephemeral=True)
        return

    if not any(role.id == TEAM_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("❌ Du hast nicht die benötigte Rolle, um diesen Befehl auszuführen!", ephemeral=True)
        return

    settings = load_ticket_settings()
    
    # Formatiere die Benutzer-Liste
    users = []
    for user_id in settings["default_users"]:
        user = interaction.guild.get_member(user_id)
        users.append(f"- {user.mention if user else f'<@{user_id}>'}")
    users_text = "\n".join(users) if users else "Keine Standard-Benutzer konfiguriert"

    # Formatiere die Rollen-Liste
    roles = []
    for role_id in settings["default_roles"]:
        role = interaction.guild.get_role(role_id)
        roles.append(f"- {role.mention if role else f'<@&{role_id}>'}")
    roles_text = "\n".join(roles) if roles else "Keine Standard-Rollen konfiguriert"

    # Hole die Kategorie
    category = interaction.guild.get_channel(settings["category_id"]) if settings["category_id"] else None
    category_text = f"#{category.name}" if category else "Keine Kategorie konfiguriert"

    embed = discord.Embed(
        title="🎫 Ticket-System Einstellungen",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )

    embed.add_field(
        name="📊 Statistiken",
        value=f"Bisher erstellte Tickets: {settings['ticket_counter']}",
        inline=False
    )

    embed.add_field(
        name="👥 Standard-Benutzer",
        value=users_text,
        inline=False
    )

    embed.add_field(
        name="🎭 Standard-Rollen",
        value=roles_text,
        inline=False
    )

    embed.add_field(
        name="📁 Ticket-Kategorie",
        value=category_text,
        inline=False
    )

    embed.add_field(
        name="📝 Log-Kanal",
        value=f"<#{settings['log_channel_id']}>",
        inline=True
    )

    embed.add_field(
        name="📨 Erstellungs-Kanal",
        value=f"<#{settings['ticket_create_channel_id']}>",
        inline=True
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="featureidee", description="Sende eine Feature-Idee ein", 
                  guilds=[discord.Object(id=MAIN_GUILD_ID), discord.Object(id=TEAM_GUILD_ID)])
@app_commands.describe(idee="Deine Idee für ein neues Feature")
async def featureidee(interaction: discord.Interaction, idee: str):
    # Hole den Feature-Ideen Channel
    feature_channel = bot.get_channel(1365698007638609920)
    if not feature_channel:
        await interaction.response.send_message("❌ **Fehler:** Feature-Ideen-Kanal nicht gefunden!", ephemeral=True)
        return
    
    # Formatierte Nachricht erstellen
    feature_message = f"""
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
💡 **Neue Feature-Idee** 💡
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

📝 **Idee:**
{idee}

👤 **Eingereicht von:** {interaction.user.mention}
⏰ **Zeitpunkt:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"""

    # Sende die Feature-Idee in den entsprechenden Channel
    await feature_channel.send(feature_message)
    
    # Bestätige dem Benutzer
    await interaction.response.send_message("✅ Vielen Dank! Deine Feature-Idee wurde erfolgreich eingereicht!", ephemeral=True)

bot.run(TOKEN)