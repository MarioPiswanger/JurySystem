import os
import sys
import flet as ft
from view import View, go, open_url

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import EventDiscipline

class DisciplinesView(View):
    def __init__(self, page: ft.Page, db, redis, eventId: int):
        super().__init__(page, db, redis)
        self.eventId = eventId
        self.route = f"/disciplines/{eventId}"
        self.scroll = ft.ScrollMode.AUTO
        
        self.event = self.db.getEvent(eventId)

        def addDiscipline(e):
            if not self.name_input.value:
                return
            self.db.insertEventDiscipline(EventDiscipline(self.name_input.value, self.eventId))
            self.name_input.value = ""
            updateTable()
            self.page.update()

        def deleteDiscipline(e, name):
            self.db.removeEventDiscipline(EventDiscipline(name, self.eventId))
            updateTable()
            self.page.update()

        self.name_input = ft.TextField(label="Add Discipline", width=300, on_submit=addDiscipline)
        
        def updateTable():
            rows = []
            for discipline, can_remove in self.db.getEventDisciplinesEnableRemove(self.eventId):
                rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(discipline.name)),
                    ft.DataCell(ft.IconButton(
                        icon=ft.Icons.DELETE,
                        icon_color=ft.Colors.RED_300 if can_remove else ft.Colors.GREY,
                        disabled=not can_remove,
                        tooltip="Delete" if can_remove else "Cannot delete (in use)",
                        on_click=lambda e, n=discipline.name: deleteDiscipline(e, n)
                    ))
                ]))
            self.table.rows = rows

        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Discipline")),
                ft.DataColumn(ft.Text("")),
            ],
            rows=[]
        )
        
        updateTable()

        self.controls = [
            ft.AppBar(title=ft.Text(f"Disciplines for {self.event.name}"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            ft.Row([self.name_input, ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=ft.Colors.BLUE_300, on_click=addDiscipline)]),
            ft.Row([self.table], scroll=ft.ScrollMode.AUTO),
            ft.Button("Back", on_click=lambda _: go(self.page, "/events"))
        ]