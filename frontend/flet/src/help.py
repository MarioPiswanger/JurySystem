import flet as ft
from view import View, go, open_url


class HelpView(View):
    def __init__(self, page: ft.Page, db, redis):
        super().__init__(page, db, redis)
        self.route = '/help'
        self.scroll = ft.ScrollMode.AUTO
        
        last_route = self.page.session.store.get('last_route') or '/'
        help_text = "Allgemeine Hilfe zum Jury System."

        if last_route == '/':
            help_text = "Startseite / Hauptmenü:\nHier finden Sie alle verfügbaren Module entsprechend Ihrer Berechtigungen."
        elif last_route == '/users':
            help_text = "Benutzerverwaltung:\nHier können Administratoren Benutzerkonten erstellen, bearbeiten und löschen.\nNutzen Sie die Icons in der Tabelle für Aktionen."
        elif last_route.startswith('/userEdit'):
            help_text = "Benutzer bearbeiten:\nFüllen Sie die Pflichtfelder (Name, Passwort, Team) aus.\n'Restrictions' legt die Rolle fest (z.B. Trainer, Admin)."
        elif last_route == '/athletes':
            help_text = "Athletenübersicht:\nVerwalten Sie hier die Stammdaten Ihrer Athleten.\nNeue Athleten können über das '+' Symbol hinzugefügt werden."
        elif last_route.startswith('/athleteEdit'):
            help_text = "Athlet bearbeiten:\nErfassen Sie Vorname, Nachname, Geburtsdatum und Geschlecht des Sportlers."
        elif last_route == '/attendances':
            help_text = "Anwesenheitskontrolle:\n1. Wählen Sie oben ein Event aus.\n2. Setzen Sie den Haken bei anwesenden Athleten.\n3. Ordnen Sie die Athleten einer Kategorie und Riege (Group) zu."
        elif last_route == '/events':
            help_text = "Event-Management:\nErstellen und verwalten Sie Wettkämpfe.\nÜber das 'Category'-Icon können Sie Altersklassen definieren."
        elif last_route.startswith('/eventEdit'):
            help_text = "Eventdaten:\nLegen Sie den Namen und das Datum des Wettkampfs fest."
        elif last_route.startswith('/categories'):
            help_text = "Kategorien-Konfiguration:\nDefinieren Sie Wettkampfklassen (z.B. AK 12-14).\nLegen Sie Geschlecht, Jahrgangsbereich und Berechnungsmethode fest."
        elif last_route == '/rating':
            help_text = "Wettkampfauswahl:\nBitte wählen Sie den Wettkampf, für den Sie Wertungen eingeben möchten."
        elif last_route.startswith('/rating/'):
            help_text = "Wertungseingabe:\n1. Wählen Sie oben Disziplin und Riege.\n2. Klicken Sie auf den Stift bei einem Athleten.\n3. Geben Sie D-Note (Schwierigkeit) und E-Note (Ausführung) ein."
        elif last_route.startswith('/public/ranking'):
            help_text = "Ergebnisliste:\nZeigt die aktuellen Platzierungen.\nFiltern Sie die Ansicht über das Dropdown-Menü nach Kategorien."
        elif last_route.startswith('/public/liveEvent'):
            help_text = "Live-Monitor:\nDiese Ansicht aktualisiert sich automatisch und zeigt die zuletzt eingegangenen Wertungen."

        self.controls = [
            ft.AppBar(title=ft.Text('Help'), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            ft.Container(content=ft.Text(help_text, size=16), padding=20),
            ft.Container(content=ft.Button('Back', on_click=lambda _: go(self.page, last_route)), padding=ft.Padding.only(left=20)),
        ]
