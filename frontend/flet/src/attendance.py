import os
import sys
import flet as ft
from view import View, go, open_url
from translate import tr

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase, User, Athlete, Attendance, Gender, Event, Progress, Restrictions, allowedCategories

class AttendanceView(View):
    def user(self) -> User:
        return self.page.session.store.get('user')
    
    def __init__(self, page: ft.Page, db, redis):
        super().__init__(page, db, redis)
        self.tr = tr(self.user().language)
        self.route = '/attendances'
        self.scroll = ft.ScrollMode.AUTO

        self.sort_column_index = 1  # team 
        self.sort_ascending = True

        def printPdf(e):
            if self.eventCtrl.value is None:
                return
            eventId = self.eventCtrl.value
            open_url(self.page, f'https://{View.api()}/attendances/{self.token()}/{self.user().id}/{eventId}')

        def exportXlsx(e):
            if self.eventCtrl.value is None:
                return
            eventId = self.eventCtrl.value
            open_url(self.page, f'https://{View.api()}/attendances_xlsx/{self.token()}/{self.user().id}/{eventId}')

        def createRows():
            if self.eventCtrl.value is None:
                return []
            event = self.db.getEvent(int(self.eventCtrl.value))
            categories = self.db.getEventCategories(event.id)

            athletes = []
            if self.user().isHost():
                for attendance in self.db.getEventAttendances(event.id):
                    athlete = self.db.getAthlete(attendance.athleteId)
                    if athlete:
                        athletes.append(athlete)
            else:
                athletes = self.db.getAthletes(self.user().id)

            data_for_rows = []
            for athlete in athletes:
                attendance = self.db.getAttendance(athlete.id, event.id)
                user = self.db.getUser(athlete.userId)
                team = user.team if user else ""
                data_for_rows.append({
                    "athlete": athlete,
                    "team": team,
                    "category": attendance.eventCategoryName if attendance else "",
                    "group": attendance.group if attendance else ""
                })

            if self.sort_column_index is not None:
                sort_key = None
                if self.sort_column_index == 1:  # team
                    sort_key = lambda item: item["team"].lower()
                elif self.sort_column_index == 2:  # given name
                    sort_key = lambda item: item["athlete"].givenname.lower()
                elif self.sort_column_index == 3:  # surname
                    sort_key = lambda item: item["athlete"].surname.lower()
                elif self.sort_column_index == 4:  # birth
                    sort_key = lambda item: item["athlete"].birth
                elif self.sort_column_index == 5:  # gender
                    sort_key = lambda item: item["athlete"].gender.name.lower()
                elif self.sort_column_index == 6:  # category
                    sort_key = lambda item: item["category"].lower()
                elif self.sort_column_index == 7:  # group
                    sort_key = lambda item: item["group"].lower()

                if sort_key:
                    data_for_rows.sort(key=sort_key, reverse=not self.sort_ascending)

            return [self.attendanceAsRow(item["athlete"], event, categories, item["team"]) for item in data_for_rows]
            
        def updateRows(e):
            self.table.rows = createRows()
            self.page.update()


        options = []
        for event in self.db.getAllEvents():
            options.append(
                ft.DropdownOption(
                    key=str(event.id),
                    text=event.descr()
                )
            )

        self.eventCtrl = ft.Dropdown(
            editable=False,
            label=self.tr.tr("select event"),
            options=options,
            width=400,
            on_select=updateRows
        )

        column_names = [
            '',
            'team',
            'given name',
            'surname',
            'birth',
            'gender',
            'category',
            'group'
        ]

        def on_sort(e: ft.DataColumnSortEvent):
            if self.sort_column_index == e.column_index:
                self.sort_ascending = not self.sort_ascending
            else:
                self.sort_column_index = e.column_index
                self.sort_ascending = True

            for i, col in enumerate(self.table.columns):
                col.label.value = self.tr.tr(column_names[i])
                if i == self.sort_column_index:
                    col.sort_ascending = self.sort_ascending
                    arrow = " ▲" if self.sort_ascending else " ▼"
                    col.label.value += arrow
                else:
                    col.sort_ascending = None
            self.table.rows = createRows()
            self.table.update()

        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(self.tr.tr(column_names[0]))),
                ft.DataColumn(ft.Text(self.tr.tr(column_names[1])), on_sort=on_sort),
                ft.DataColumn(ft.Text(self.tr.tr(column_names[2])), on_sort=on_sort),
                ft.DataColumn(ft.Text(self.tr.tr(column_names[3])), on_sort=on_sort),
                ft.DataColumn(ft.Text(self.tr.tr(column_names[4])), on_sort=on_sort),
                ft.DataColumn(ft.Text(self.tr.tr(column_names[5])), on_sort=on_sort),
                ft.DataColumn(ft.Text(self.tr.tr(column_names[6])), on_sort=on_sort),
                ft.DataColumn(ft.Text(self.tr.tr(column_names[7])), on_sort=on_sort),
            ])
        initial_sort_col_index = self.sort_column_index
        arrow = " ▲" if self.sort_ascending else " ▼"
        self.table.columns[initial_sort_col_index].label.value += arrow
        self.table.columns[self.sort_column_index].sort_ascending = self.sort_ascending
        title = f'{self.tr.tr("Attendances of")} {self.user().username if self.user().isHost() else self.user().team}'
        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr("Help"), on_click=lambda _: go(self.page, '/help')), title=ft.Text(title), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            self.eventCtrl,
            ft.Row([self.table], scroll=ft.ScrollMode.AUTO),
            ft.Row(spacing=0, controls=[
                ft.IconButton(ft.Icons.PICTURE_AS_PDF,
                          icon_color=ft.Colors.BLUE_300,
                          tooltip="pdf",
                          on_click=printPdf),
                ft.IconButton(ft.Icons.SAVE,
                          icon_color=ft.Colors.BLUE_300,
                          tooltip="xlsx",
                          on_click=exportXlsx)]),
            ft.Button(self.tr.tr("Home"), on_click=lambda _: go(self.page, "/")),
        ]

    def attendanceAsRow(self, athlete: Athlete, event: Event, categories: list, team_name: str):
        def onChange(e):
            attendance = self.db.getAttendance(athlete.id, event.id)
            if e.control.value:
                print(f'nominate {athlete.name()} for {event.descr()}')
                if attendance:
                    categoryCell.content.value = attendance.eventCategoryName
                    groupCell.content.value = attendance.group
                    groupCell.content.disabled = not self.user().isHost()
                else:
                    groupCell.content.disabled = True
                categoryCell.content.disabled = False
                allowed = allowedCategories(categories, athlete)
                categoryCell.content.options = [ft.DropdownOption(d.name) for d in allowed]
            else:
                print(f'denominate {athlete.name()} for {event.descr()}')
                self.db.hideAttendance(event.id, athlete.id, True)
                categoryCell.content.value = ''
                groupCell.content.value = ''
                categoryCell.content.disabled = True
                groupCell.content.disabled = True
                categoryCell.content.options = []
            self.page.update()

        def onUpdateCategory(e):
            self.db.setAttendanceCategory(event.id, athlete.id, e.control.value)
            groupCell.content.disabled = not self.user().isHost()
            self.page.update()

        def onUpdateGroup(e):
            self.db.setAttendanceGroup(event.id, athlete.id, e.control.value)

        attendance = self.db.getAttendance(athlete.id, event.id)
        checkBoxEnabled = event.progress() == Progress.PLANNED
        checkBoxValue = attendance is not None
        allowed = allowedCategories(categories, athlete)
        categoryCell = ft.DataCell(ft.Dropdown(
                    disabled=not attendance,
                    options=list() if attendance is None else [ft.DropdownOption(d.name) for d in allowed],
                    value=attendance.eventCategoryName if attendance else None,
                    on_select=onUpdateCategory
                    ))
        groupCell = ft.DataCell(ft.TextField(
                    disabled=not attendance or not self.user().isHost(),
                    value=attendance.group if attendance else None,
                    on_change=onUpdateGroup,
                    expand=True,
                    ))
        cells = [
            ft.DataCell(ft.Checkbox(value=checkBoxValue, disabled=not checkBoxEnabled, on_change=onChange)),
            ft.DataCell(ft.Text(team_name)),
            ft.DataCell(ft.Text(athlete.givenname)),
            ft.DataCell(ft.Text(athlete.surname)),
            ft.DataCell(ft.Text(athlete.birthFormated())),
            ft.DataCell(ft.Text(athlete.gender.name)),
            categoryCell,
            groupCell
            ]
        return ft.DataRow(cells=cells)
