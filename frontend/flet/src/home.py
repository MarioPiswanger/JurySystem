import os
import sys
import flet as ft
import secrets
from view import View, go, open_url
from translate import tr

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase, Athlete, Gender, Event, Progress, Restrictions
from shared.rights import Route, allowedRoutes

def TextButton(text, on_click=None):
    return ft.TextButton(
        content=text,
        on_click=on_click,
        width=144,
        height=48,
        style=ft.ButtonStyle(text_style=ft.TextStyle(size=16), side=ft.BorderSide(1, ft.Colors.OUTLINE)),
    )

class HomeView(View):
    def __init__(self, page: ft.Page, db, redis):
        super().__init__(page, db, redis)
        self.route = '/'
        user = page.session.store.get('user')
        events = sorted(
            self.db.getAllEvents(),
            key=lambda event: (event.date, event.name.casefold()),
        )
        event_picker = ft.Dropdown(
            label="Event auswählen",
            options=[
                ft.DropdownOption(key=str(event.id), text=event.descr())
                for event in events
            ],
            value=str(events[0].id) if events else None,
            disabled=not events,
        )
        event_details = ft.Column(spacing=10)

        def show_selected_event(_, update_page=True):
            event = next(
                (
                    item for item in events
                    if str(item.id) == event_picker.value
                ),
                None,
            )
            event_details.controls.clear()
            if event is None:
                event_details.controls.append(
                    ft.Text("Zurzeit sind keine Events verfügbar.")
                )
            else:
                progress = event.progress()
                status = {
                    Progress.PLANNED: "Anmeldung offen",
                    Progress.ACTIVE: "Event läuft",
                    Progress.FINISHED: "Abgeschlossen",
                }[progress]
                event_details.controls.extend(
                    [
                        ft.Text(event.name, size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Datum: {event.dateFormated()}"),
                        ft.Text(status),
                    ]
                )
                if progress == Progress.PLANNED:
                    event_details.controls.append(
                        ft.Button(
                            "Für dieses Event anmelden",
                            icon=ft.Icons.PERSON_ADD_ALT_1,
                            on_click=lambda _, event_id=event.id: go(self.page, 
                                f"/anmeldung/{event_id}"
                            ),
                        )
                    )
                elif progress == Progress.ACTIVE:
                    event_details.controls.append(
                        ft.Button(
                            "Live-Ergebnisse ansehen",
                            icon=ft.Icons.LIVE_TV,
                            on_click=lambda _, event_id=event.id: go(self.page, 
                                f"/public/liveEvent/{event_id}"
                            ),
                        )
                    )
                else:
                    event_details.controls.extend(
                        [
                            ft.Button(
                                "Ergebnisse (PDF)",
                                on_click=lambda _, event_id=event.id: open_url(self.page, 
                                    f"https://{View.api()}/results/{event_id}"
                                ),
                            ),
                            ft.Button(
                                "Ergebnisse (XLSX)",
                                on_click=lambda _, event_id=event.id: open_url(self.page, 
                                    f"https://{View.api()}/results_xlsx/{event_id}"
                                ),
                            ),
                        ]
                    )
            if update_page:
                self.page.update()

        event_picker.on_select = show_selected_event
        show_selected_event(None, update_page=False)

        def loginbtn(_):
            user_id = self.db.validateUser(
                (userEdit.value or "").strip(),
                passEdit.value or "",
            )
            if user_id is None:
                self.page.show_dialog(
                    ft.SnackBar(
                        ft.Text("Falscher Benutzername oder falsches Passwort."),
                        bgcolor="red",
                    )
                )
                return

            self.page.session.store.set("user", self.db.getUser(user_id))
            self.setToken(secrets.token_urlsafe())
            if self.page.session.store.contains_key("target"):
                target = self.page.session.store.get("target")
                self.page.session.store.remove("target")
                go(self.page, target)
            else:
                go(self.page, "/")

        userEdit = ft.TextField(label="Benutzername", width=320)
        passEdit = ft.TextField(
            label="Passwort",
            password=True,
            can_reveal_password=True,
            width=320,
            on_submit=loginbtn,
        )

        left_panel = ft.Column(
            controls=[
                ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.EMOJI_EVENTS, size=44, color=ft.Colors.BLUE_300),
                        ft.Text("Jury System", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("Wettkämpfe und Ergebnisse auf einen Blick."),
                    ],
                    spacing=10,
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.PHOTO_LIBRARY_OUTLINED, size=34),
                            ft.Text("Bilder finden", size=20, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Suche Wettkampffotos über deine Startnummer."
                            ),
                            ft.Button(
                                "Zum Bilderbereich",
                                icon=ft.Icons.ARROW_FORWARD,
                                on_click=lambda _: go(self.page, "/bilder"),
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=18,
                    border=ft.Border.all(1, ft.Colors.OUTLINE),
                    border_radius=12,
                ),
            ],
            spacing=20,
            expand=True,
        )

        if user is None:
            center_panel = ft.Column(
                controls=[
                    ft.Icon(ft.Icons.ACCOUNT_CIRCLE_OUTLINED, size=48),
                    ft.Text("Willkommen zurück", size=26, weight=ft.FontWeight.BOLD),
                    ft.Text("Melde dich beim Jurysystem an."),
                    userEdit,
                    passEdit,
                    ft.Button(
                        "Login",
                        icon=ft.Icons.LOGIN,
                        width=320,
                        on_click=loginbtn,
                    ),
                    ft.Text("Noch kein Konto? Wähle links ein Event zur Anmeldung."),
                ],
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        else:
            center_panel = ft.Column(
                controls=[
                    ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=48),
                    ft.Text("Angemeldet", size=26, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Hallo, {user.username}"),
                    ft.Button("Logout", on_click=self.logout),
                    ft.Divider(),
                    ft.Text("Verwaltung", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        controls=[
                            TextButton(
                                self.tr.tr(allowed.name),
                                on_click=lambda _, route=allowed.route: go(self.page, route),
                            )
                            for allowed in allowedRoutes(user)
                        ],
                        wrap=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )

        right_panel = ft.Column(
            controls=[
                ft.Icon(ft.Icons.EVENT_AVAILABLE, size=40, color=ft.Colors.BLUE_300),
                ft.Text("Events", size=26, weight=ft.FontWeight.BOLD),
                ft.Text("Wähle eine Veranstaltung aus."),
                event_picker,
                event_details,
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        card_style = {
            "padding": 24,
            "border": ft.Border.all(1, ft.Colors.OUTLINE),
            "border_radius": 16,
            "bgcolor": ft.Colors.SURFACE_CONTAINER_HIGHEST,
        }
        self.controls = [
            ft.AppBar(
                title=ft.Text("Jury System"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            ),
            ft.Container(
                content=ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            content=left_panel,
                            col={"xs": 12, "md": 4},
                            **card_style,
                        ),
                        ft.Container(
                            content=right_panel,
                            col={"xs": 12, "md": 4},
                            **card_style,
                        ),
                        ft.Container(
                            content=center_panel,
                            col={"xs": 12, "md": 4},
                            alignment=ft.Alignment.CENTER,
                            **card_style,
                        ),
                    ],
                    spacing=18,
                    run_spacing=18,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                    expand=True,
                ),
                expand=True,
                padding=24,
            ),
        ]

    def logout(self, e):
        self.page.session.store.clear()
        go(self.page, '/')


class LoginView(View):
    def __init__(self, page: ft.Page, db, redis):
        super().__init__(page, db, redis)
        self.route = '/login'
        self.scroll = None

        def loginbtn(e):
            userId = self.db.validateUser(userEdit.value, passEdit.value)
            if userId is not None:
                print("Redirecting...")
                self.page.session.store.set('user', self.db.getUser(userId))
                self.setToken(secrets.token_urlsafe())
                if self.page.session.store.contains_key('target'):
                    target = self.page.session.store.get('target')
                    self.page.session.store.remove('target')
                    go(self.page, target)
                else:
                    go(self.page, '/')
            else:
                print("Login failed !!!")
                self.page.show_dialog(ft.SnackBar(
                    ft.Text("wrong login, user expired or locked", size=30),
                    bgcolor="red"
                ))

        userEdit = ft.TextField(label="User name", width=400, border_color= "white")
        passEdit = ft.TextField(label="Password", password=True, border_color= "white", can_reveal_password=True, on_submit=loginbtn, width=400)
        login_button = ft.Button(
            "Login",
            on_click=loginbtn,
            color="black", 
            width= 80,
            height= 30,

            style=ft.ButtonStyle(
                bgcolor = {
                    ft.ControlState.DEFAULT: "lightblue",
                    ft.ControlState.HOVERED: "#FFFFFFFF",
                },
                text_style=ft.TextStyle(size=16),
            )
        )

        controls = [
            ft.Text("Anmeldung zum Jurysystem",size = 40, weight="bold"),
            userEdit, passEdit,login_button
        ]

        self.controls = [
            ft.Container(
                content=ft.Column(
                    controls=controls,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=15,
                    scroll=ft.ScrollMode.AUTO
                ),
                expand=True,
                alignment=ft.Alignment.CENTER
            )
        ]