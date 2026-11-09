import os
import sys
import flet as ft
from view import View

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import Progress

class RankingHomeView(View):
    def __init__(self, page: ft.Page, db, redis):
        super().__init__(page, db, redis)
        self.route = '/ranking_home'
        self.scroll = False

        controls = [
            ft.Text("Events", size=40, weight="bold"),
        ]
        user = self.page.session.get("user")
        is_host = user is not None and user.isHost()

        for e in self.db.getAllEvents():
            progress = e.progress()
            if progress == Progress.FINISHED:
                controls.append(ft.ElevatedButton(f"{e.descr()}", on_click=lambda _,id=e.id: self.page.go(f"/public/ranking/{id}"), width=300))
            elif progress == Progress.ACTIVE and is_host:
                controls.append(ft.ElevatedButton(f"{e.descr()}", on_click=lambda _,id=e.id: self.page.go(f"/ranking/{id}"), width=300))
            elif progress == Progress.ACTIVE:
                controls.append(ft.ElevatedButton(f"{e.descr()}", on_click=lambda _,id=e.id: self.page.go(f"/public/liveEvent/{id}"), width=300))

        controls.append(ft.ElevatedButton("Home", on_click=lambda _: self.page.go("/")))

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
                alignment=ft.alignment.center
            )
        ]