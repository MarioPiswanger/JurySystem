import os
import sys
import datetime
import flet as ft
from view import View, go, open_url
from translate import tr

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase, Athlete, Gender, Event, Progress


def header():
    return ['', '', 'given name', 'surname', 'birth', 'gender']

class AthleteView(View):
    def __init__(self, page: ft.Page, db, redis):
        super().__init__(page, db, redis)
        self.route = '/athletes'
        self.scroll = ft.ScrollMode.AUTO
        user = self.page.session.store.get('user')

        def createRows():
            return [self.athleteAsRow(athlete, editFunc, deleteFunc) for athlete in self.db.getAthletes(user.id)]

        def updateRows(e):
            self.table.rows = createRows()
            self.page.update()

        def deleteFunc(e, athleteId):
            athlete = self.db.getAthlete(athleteId)
            def yes(e):
                self.db.removeAthlete(athleteId)
                self.page.pop_dialog()
                updateRows(e)

            def no(e):
                print('cancel')
                self.page.pop_dialog()

            dlg = ft.AlertDialog(
                modal=True,
                content=ft.Text(f"{self.tr.tr('Delete athlete')} '{athlete.name()}'?"),
                actions=[
                    ft.TextButton(self.tr.tr("Yes"), on_click=yes),
                    ft.TextButton(self.tr.tr("No"), on_click=no),
                ],
                actions_alignment=ft.MainAxisAlignment.END)
            self.page.show_dialog(dlg)

        def editFunc(e, athleteId):
            print(f'edit {athleteId=}')
            go(self.page, f'/athleteEdit/{athleteId}')
        
        def addFunc(e):
            go(self.page, f'/athleteEdit/0')
            
        def printPdf(e):
            open_url(self.page, f'https://{View.api()}/athletes/{self.token()}/{user.id}')

        def exportXlsx(e):
            open_url(self.page, f'https://{View.api()}/athletes_xlsx/{self.token()}/{user.id}')

        self.table = ft.DataTable(
                columns=[ft.DataColumn(ft.Text(self.tr.tr(h))) for h in header()],
                rows=createRows()
            )
        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr("Help"), on_click=lambda _: go(self.page, '/help')), title=ft.Text(f'Athletes of {user.team}'), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            ft.Row([self.table], scroll=ft.ScrollMode.AUTO),
            ft.Row(spacing=0, controls=[
                ft.IconButton(ft.Icons.ADD_CIRCLE,
                    icon_color=ft.Colors.BLUE_300,
                    tooltip=self.tr.tr("Add"),
                    on_click=addFunc),
                ft.IconButton(ft.Icons.PICTURE_AS_PDF,
                          icon_color=ft.Colors.BLUE_300,
                          tooltip="pdf",
                          on_click=printPdf),
                ft.IconButton(ft.Icons.SAVE,
                          icon_color=ft.Colors.BLUE_300,
                          tooltip="xlsx",
                          on_click=exportXlsx)]),
            ft.Button("Home", on_click=lambda _: go(self.page, "/")),
        ]
        
    def athleteAsRow(self, athlete: Athlete, editFunc: callable, deleteFunc: callable):
        cells = [
            ft.DataCell(ft.IconButton(
                        icon=ft.Icons.EDIT,
                        icon_color=ft.Colors.GREEN_300,
                        tooltip=self.tr.tr('Edit'),
                        on_click=lambda e: editFunc(e, athlete.id))),
            ft.DataCell(ft.IconButton(
                        icon=ft.Icons.DELETE,
                        icon_color=ft.Colors.RED_300,
                        tooltip=self.tr.tr('Delete'),
                        on_click=lambda e: deleteFunc(e, athlete.id))),
            ft.DataCell(ft.Text(athlete.givenname)),
            ft.DataCell(ft.Text(athlete.surname)),
            ft.DataCell(ft.Text(athlete.birthFormated())),
            ft.DataCell(ft.Text(athlete.gender.name))
            ]
        return ft.DataRow(cells=cells)



class AthleteEditView(View):
    def __init__(self, page: ft.Page, db, redis, athleteId: int):
        super().__init__(page, db, redis)
        self.route = f'/athleteEdit/{athleteId}'
        self.scroll = ft.ScrollMode.AUTO
        createAthlete = athleteId == 0
        user = self.page.session.store.get('user')

        def update(e):
            if createAthlete:
                print(f'creating athlete')
                self.db.insertAthlete(givenNameEdit.value, surnameEdit.value, user.id, Athlete.birthFromString(self.birthEdit.value), Gender[genderEdit.value])
            else:
                print(f'saving {athleteId=}')
                self.db.updateAthlete(athleteId, givenNameEdit.value, surnameEdit.value, user.id, Athlete.birthFromString(self.birthEdit.value), Gender[genderEdit.value])
            go(self.page, "/athletes")
            
        def cancel(e):
            print(f'cancel {athleteId=}')
            go(self.page, "/athletes")

        def onChangeBirth(e):
            self.birthEdit.value = e.control.value.strftime("%d.%m.%Y")
            self.page.update()

        print(f'get athlete {athleteId=}')
        if not createAthlete:
            athlete = self.db.getAthlete(athleteId)
            birth_value = athlete.birthFormated()
        else:
            birth_value = ""
        givenNameEdit = ft.TextField(label=self.tr.tr("given name"), value=None if createAthlete else athlete.givenname)
        surnameEdit = ft.TextField(label=self.tr.tr("surname"), value=None if createAthlete else athlete.surname)
        teamEdit = ft.TextField(label=self.tr.tr("team"), value=user.team, disabled=True)
        self.birthEdit = ft.TextField(
            label=self.tr.tr("birth"),
            value=birth_value,
            disabled=True,
            width=115
        )
        birthPicker = ft.Button(
            self.tr.tr("pick date"),
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=lambda e: page.show_dialog(
                ft.DatePicker(
                    first_date=datetime.datetime(year=1980, month=1, day=1),
                    last_date=datetime.datetime(year=2025, month=12, day=31),
                    on_change = onChangeBirth
                )
            ),
        )
        birth_row = ft.Row(
            controls=[
                self.birthEdit,
                birthPicker
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        
    
        genderEdit = ft.Dropdown(
            label=self.tr.tr("gender"),
            width = 300,
            options=[ft.DropdownOption(e.name) for e in Gender],
            value=Gender.FEMALE.name if createAthlete else athlete.gender.name)
        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr("Help"), on_click=lambda _: go(self.page, '/help')), title=ft.Text(f'{self.tr.tr('Create ') if createAthlete else self.tr.tr('Edit ')} {self.tr.tr('Athlete')}'), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            givenNameEdit,
            surnameEdit,
            teamEdit,
            birth_row,
            genderEdit,
            ft.Row(spacing=0, controls=[
                    ft.IconButton(
                        icon=ft.Icons.CHECK_CIRCLE,
                        icon_color=ft.Colors.GREEN_300,
                        tooltip=self.tr.tr("Save"),
                        on_click=update),
                    ft.IconButton(
                        icon=ft.Icons.CANCEL,
                        icon_color=ft.Colors.RED_300,
                        tooltip=self.tr.tr("Cancel"),
                        on_click=cancel)], scroll=ft.ScrollMode.AUTO),
            ft.Button("Home", on_click=lambda _: go(self.page, "/"))
            ]
