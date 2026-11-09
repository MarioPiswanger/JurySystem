import datetime
import secrets
import os
import sys

import flet as ft
import httpx
import pymysql

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from view import View
from shared.database import Athlete, Gender, Progress, allowedCategories


class PublicSignupView(View):
    def __init__(self, page: ft.Page, db, redis, eventId: int):
        super().__init__(page, db, redis)
        self.route = f"/anmeldung/{eventId}"
        self.scroll = ft.ScrollMode.AUTO
        event = next(
            (item for item in self.db.getAllEvents() if item.id == eventId),
            None,
        )
        if event is None or event.progress() != Progress.PLANNED:
            self.controls = [
                ft.AppBar(title=ft.Text("Event-Anmeldung")),
                ft.Text("Für dieses Event ist keine Anmeldung mehr möglich."),
                ft.ElevatedButton("Zur Startseite", on_click=lambda _: self.page.go("/")),
            ]
            return

        givenname = ft.TextField(label="Vorname", max_length=50)
        surname = ft.TextField(label="Nachname", max_length=50)
        birth = ft.TextField(label="Geburtsdatum", read_only=True, width=180)
        gender = ft.Dropdown(
            label="Geschlecht",
            value=Gender.FEMALE.name,
            options=[
                ft.dropdown.Option(key=Gender.FEMALE.name, text="Weiblich"),
                ft.dropdown.Option(key=Gender.MALE.name, text="Männlich"),
            ],
            width=240,
        )
        team = ft.TextField(label="Verein / Team (optional)", max_length=50)
        email = ft.TextField(label="E-Mail", max_length=50, keyboard_type=ft.KeyboardType.EMAIL)
        username = ft.TextField(label="Benutzername", max_length=50)
        password = ft.TextField(
            label="Passwort",
            password=True,
            can_reveal_password=True,
            min_lines=1,
            max_length=72,
        )
        password_confirm = ft.TextField(
            label="Passwort wiederholen",
            password=True,
            can_reveal_password=True,
        )
        categories = self.db.getEventCategories(event.id)
        category = ft.Dropdown(label="Wettkampfklasse", options=[], width=300)

        def updateCategories(_=None):
            if not birth.value:
                category.options = []
                category.value = None
                self.page.update()
                return
            try:
                birthDate = Athlete.birthFromString(birth.value)
            except ValueError:
                category.options = []
                category.value = None
                self.page.update()
                return

            athlete = Athlete(
                id=0,
                givenname=givenname.value or "",
                surname=surname.value or "",
                userId=0,
                birth=birthDate,
                gender=Gender[gender.value],
                hidden=False,
            )
            matches = allowedCategories(categories, athlete)
            category.options = [ft.dropdown.Option(c.name) for c in matches]
            category.value = matches[0].name if len(matches) == 1 else None
            self.page.update()

        def onBirthChange(e):
            if e.control.value:
                birth.value = e.control.value.strftime("%d.%m.%Y")
                updateCategories()

        birth_picker = ft.ElevatedButton(
            "Geburtsdatum wählen",
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=lambda _: self.page.open(
                ft.DatePicker(
                    first_date=datetime.datetime(1920, 1, 1),
                    last_date=datetime.datetime.now(),
                    on_change=onBirthChange,
                )
            ),
        )

        gender.on_change = updateCategories

        def submit(_):
            values = {
                "Vorname": (givenname.value or "").strip(),
                "Nachname": (surname.value or "").strip(),
                "E-Mail": (email.value or "").strip(),
                "Benutzername": (username.value or "").strip(),
            }
            missing = [label for label, value in values.items() if not value]
            if missing or not birth.value or not category.value:
                self._show_message(
                    "Bitte alle Felder ausfüllen und eine passende Wettkampfklasse auswählen."
                )
                return
            if "@" not in values["E-Mail"]:
                self._show_message("Bitte eine gültige E-Mail-Adresse eingeben.")
                return
            password_bytes = (password.value or "").encode()
            if len(password_bytes) < 8 or len(password_bytes) > 72:
                self._show_message("Das Passwort muss zwischen 8 und 72 Byte lang sein.")
                return
            if password.value != password_confirm.value:
                self._show_message("Die Passwörter stimmen nicht überein.")
                return

            athlete = Athlete(
                id=0,
                givenname=values["Vorname"],
                surname=values["Nachname"],
                userId=0,
                birth=Athlete.birthFromString(birth.value),
                gender=Gender[gender.value],
                hidden=False,
            )
            matching_categories = allowedCategories(categories, athlete)
            if category.value not in {item.name for item in matching_categories}:
                self._show_message("Die gewählte Wettkampfklasse passt nicht zu den Teilnehmerdaten.")
                return

            try:
                user_id = self.db.createPublicRegistration(
                    values["Benutzername"],
                    password.value,
                    values["E-Mail"],
                    (team.value or "").strip(),
                    values["Vorname"],
                    values["Nachname"],
                    athlete.birth,
                    athlete.gender,
                    event.id,
                    category.value,
                )
            except ValueError as error:
                self._show_message(str(error))
                return
            except pymysql.err.IntegrityError:
                self._show_message("Dieser Benutzername ist bereits vergeben.")
                return
            except pymysql.MySQLError as error:
                self._show_message(
                    f"Die Anmeldung konnte nicht gespeichert werden ({type(error).__name__})."
                )
                return

            self.page.session.set("user", self.db.getUser(user_id))
            self.setToken(secrets.token_urlsafe())
            self.page.go("/")
            self._show_message(f"Du bist für {event.name} angemeldet.")

        password_confirm.on_submit = submit
        self.controls = [
            ft.AppBar(
                title=ft.Text(f"Anmeldung zu {event.name}"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(event.descr(), size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Erstelle dein Konto und melde dich direkt für dieses Event an."
                        ),
                        givenname,
                        surname,
                        team,
                        email,
                        username,
                        password,
                        password_confirm,
                        ft.Row([birth, birth_picker], wrap=True),
                        gender,
                        category,
                        ft.ElevatedButton("Konto erstellen und anmelden", on_click=submit),
                        ft.TextButton("Zurück zur Startseite", on_click=lambda _: self.page.go("/")),
                    ],
                    width=480,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                alignment=ft.alignment.top_center,
                padding=24,
            ),
        ]

    def _show_message(self, message: str):
        self.page.open(ft.SnackBar(ft.Text(message)))

class ImagesView(View):
    def __init__(self, page: ft.Page, db, redis):
        super().__init__(page, db, redis)
        self.route = "/bilder"
        self.scroll = ft.ScrollMode.AUTO
        self.results = ft.Column(spacing=12)
        self.status = ft.Text()
        events = self.db.getAllEvents()
        self.event_picker = ft.Dropdown(
            label="Event",
            options=[
                ft.dropdown.Option(key=event.id, text=event.descr())
                for event in events
            ],
            value=events[0].id if events else None,
            width=360,
        )
        self.bib_number = ft.TextField(
            label="Startnummer",
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=4,
            width=240,
            on_submit=self.search,
        )
        self.file_picker = ft.FilePicker(
            on_result=self.files_picked,
            on_upload=self.upload_progress,
        )
        self.page.overlay.append(self.file_picker)
        self.upload_count = 0
        self.uploaded_count = 0

        controls = [
            ft.AppBar(
                title=ft.Text("Bilder"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Bilder zu deiner Startnummer", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Gib deine Startnummer ein. Die Bilder werden anhand der "
                            "automatisch erkannten Nummern gefunden."
                        ),
                        ft.Row(
                            [
                                self.event_picker,
                                self.bib_number,
                                ft.ElevatedButton("Bilder suchen", on_click=self.search),
                            ],
                            wrap=True,
                        ),
                        self.status,
                        self.results,
                    ],
                    spacing=12,
                ),
                padding=24,
            ),
        ]

        user = self.page.session.get("user")
        if user is not None and user.isHost():
            controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Divider(),
                            ft.Text("Bilder hochladen", size=22, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Wähle das Event aus und lade JPEG- oder PNG-Bilder hoch. "
                                "Die Startnummern werden beim Upload erkannt."
                            ),
                            ft.ElevatedButton(
                                "Bilder auswählen",
                                icon=ft.Icons.UPLOAD_FILE,
                                on_click=self.upload,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=24,
                )
            )
        controls.append(
            ft.ElevatedButton("Zur Startseite", on_click=lambda _: self.page.go("/"))
        )
        self.controls = controls

    async def search(self, _):
        number = (self.bib_number.value or "").strip()
        event_id = self.event_picker.value
        if not number.isdigit() or not 1 <= len(number) <= 4:
            self.status.value = "Bitte eine gültige Startnummer eingeben."
            self.results.controls.clear()
            self.page.update()
            return
        if event_id is None:
            self.status.value = "Zurzeit sind keine Events für die Bildsuche verfügbar."
            self.page.update()
            return

        self.status.value = "Suche läuft …"
        self.results.controls.clear()
        self.page.update()
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    f"https://{View.api()}/images/search/{event_id}/{number}"
                )
            response.raise_for_status()
            images = response.json()["images"]
        except (httpx.HTTPError, ValueError, KeyError) as error:
            self.status.value = f"Die Bildsuche ist fehlgeschlagen ({type(error).__name__})."
            self.page.update()
            return

        if not images:
            self.status.value = f"Keine Bilder für Startnummer {number} gefunden."
        else:
            self.status.value = f"{len(images)} Bild(er) für Startnummer {number}:"
            self.results.controls = [
                ft.Image(
                    src=f"https://{View.api()}{image['url']}",
                    width=360,
                    fit=ft.ImageFit.CONTAIN,
                )
                for image in images
            ]
        self.page.update()

    def upload(self, _):
        user = self.page.session.get("user")
        if user is None or not user.isHost():
            self.status.value = "Nur Hosts und Administratoren dürfen Bilder hochladen."
            self.page.update()
            return

        self.file_picker.pick_files(
            dialog_title="Bilder auswählen",
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["jpg", "jpeg", "png"],
        )

    def files_picked(self, e):
        files = e.files or []
        if not files:
            return
        if self.event_picker.value is None:
            self.status.value = "Bitte zuerst ein Event auswählen."
            self.page.update()
            return
        user = self.page.session.get("user")
        if user is None or not user.isHost():
            self.status.value = "Nur Hosts und Administratoren dürfen Bilder hochladen."
            self.page.update()
            return

        self.upload_count = len(files)
        self.uploaded_count = 0
        self.status.value = "Bilder werden hochgeladen und ausgewertet …"
        self.page.update()

        upload_url = (
            f"https://{View.api()}/images/upload/"
            f"{self.event_picker.value}/{user.id}/{self.token()}"
        )
        self.file_picker.upload(
            [
                ft.FilePickerUploadFile(
                    name=file.name,
                    upload_url=upload_url,
                    method="POST",
                )
                for file in files
            ]
        )

    def upload_progress(self, e):
        if e.error:
            self.status.value = f"Upload von {e.file_name} fehlgeschlagen: {e.error}"
            self.page.update()
            return
        if e.progress == 1:
            self.uploaded_count += 1
            if self.uploaded_count == self.upload_count:
                self.status.value = (
                    f"{self.uploaded_count} Bild(er) hochgeladen und auf Startnummern geprüft."
                )
        self.page.update()
