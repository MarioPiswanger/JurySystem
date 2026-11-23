import os
import sys
import flet as ft
from view import View, go, open_url

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import Progress

class RankingHomeView(View):
    def __init__(self, page: ft.Page, db, redis):
        super().__init__(page, db, redis)
        self.route = '/ranking_home'
        self.scroll = None

        controls = [
            ft.Text("Events", size=40, weight="bold"),
        ]
        user = self.page.session.store.get("user")
        is_host = user is not None and user.isHost()

        for e in self.db.getAllEvents():
            progress = e.progress()
            if progress == Progress.FINISHED:
                controls.append(ft.Button(f"{e.descr()}", on_click=lambda _,id=e.id: go(self.page, f"/public/ranking/{id}"), width=300))
            elif progress == Progress.ACTIVE and is_host:
                controls.append(ft.Button(f"{e.descr()}", on_click=lambda _,id=e.id: go(self.page, f"/ranking/{id}"), width=300))
            elif progress == Progress.ACTIVE:
                controls.append(ft.Button(f"{e.descr()}", on_click=lambda _,id=e.id: go(self.page, f"/public/liveEvent/{id}"), width=300))

        controls.append(ft.Button("Home", on_click=lambda _: go(self.page, "/")))

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