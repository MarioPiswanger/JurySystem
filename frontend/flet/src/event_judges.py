import os
import sys
import flet as ft
from view import View, go, open_url

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import *

def header():
    return ['', 'Judge', '', '']

class EventJudgesView(View):
    def __init__(self, page: ft.Page, db, redis, eventId: int):
        super().__init__(page, db, redis)
        self.route = f"/eventJudges/{eventId}"
        self.scroll = ft.ScrollMode.AUTO

        self.event = self.db.getEvent(eventId)

        def addJudge(e):
            if not self.judgeInput.value:
                return
            self.db.addEventJudge(eventId, int(self.judgeInput.value))
            updateTable()
            self.page.update()

        def deleteJudge(e, judgeId):
            self.db.removeEventJudge(self.event.id, judgeId)
            updateTable()
            self.page.update()

        self.judgeInput = ft.Dropdown(
            label="Add Judge",
            width=300,
            options=[ft.DropdownOption(
                key=str(u.id),
                text=u.username) for u in self.db.getAllJudges() if u.valid() and not u.hidden]
        )

        def updateTable():
            rows = []
            for judgeId, judgeName, can_remove in self.db.getEventJudgesEnableRemove(self.event.id):
                rows.append(self.asRow(judgeId, judgeName, can_remove, deleteJudge))
            self.table.rows = rows

        self.table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text(h)) for h in header()],
            rows=[]
        )
        
        updateTable()

        def printJudgeLogins(e):
            open_url(self.page, f'https://{View.api()}/judgelogins/{self.token()}/{eventId}/rating_{eventId}')

        self.controls = [
            ft.AppBar(title=ft.Text(f"Judges for {self.event.name}"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            ft.Row([self.judgeInput, ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=ft.Colors.BLUE_300, on_click=addJudge)]),
            ft.Row([self.table], scroll=ft.ScrollMode.AUTO),
            ft.Row([
                ft.IconButton(icon=ft.Icons.CONTACT_PAGE, tooltip="Logins for judges", on_click=printJudgeLogins),
                ft.Button("Back", on_click=lambda _: go(self.page, "/events"))
            ])
        ]

    def asRow(self, judgeId, judgeName, can_remove, deleteFunc):
        def downlodQR(e):
            open_url(self.page, f'https://{View.api()}/qrcodes/login/{self.token()}/{judgeId}/rating_{self.event.id}')

        def recreateQr(e):
            self.db.recreateUserToken(judgeId)

        cells=[
                ft.DataCell(ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED_300 if can_remove else ft.Colors.GREY,
                    disabled=not can_remove,
                    tooltip="Delete" if can_remove else "Cannot delete (in use)",
                    on_click=lambda e, n=judgeId: deleteFunc(e, n)
                )),
                ft.DataCell(ft.Text(judgeName)),
                ft.DataCell(ft.IconButton(
                    icon=ft.Icons.QR_CODE_2_ROUNDED,
                    tooltip="qr-code for token login",
                    on_click=downlodQR
                )),
                ft.DataCell(ft.IconButton(
                    icon=ft.Icons.AUTORENEW_ROUNDED,
                    tooltip="renew token for qr-code login",
                    on_click=recreateQr
                ))
            ]
        return ft.DataRow(cells=cells)
