import os
import sys
import flet as ft
import datetime
from view import View

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase, Event, Progress


def header():
    return ['', '', 'Event name', 'date', 'progress', '', '', '', '']

def eventAsRow(tr, event: Event, editFunc: callable, deleteFunc: callable, finishFunc: callable):
    if event.progress() == Progress.ACTIVE:
        finishButon = ft.IconButton(icon=ft.Icons.STOP,
                                  icon_color=ft.Colors.RED_300,
                                  tooltip=tr.tr("Finish Event"),
                                  on_click=lambda e: finishFunc(e, event.id, True))
    elif event.progress() == Progress.FINISHED:
        finishButon = ft.IconButton(icon=ft.Icons.START,
                                  icon_color=ft.Colors.GREEN_300,
                                  tooltip=tr.tr("Open Event"),
                                  on_click=lambda e: finishFunc(e, event.id, False))
    else:
        finishButon = ft.IconButton(icon=ft.Icons.STOP,
                                  icon_color=ft.Colors.GREY_300, disabled=True)

    cells = [
        ft.DataCell(ft.IconButton(
                    icon=ft.Icons.EDIT,
                    icon_color=ft.Colors.GREEN_300,
                    tooltip="Edit",
                    on_click=lambda e: editFunc(e, event.id))),
        ft.DataCell(ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED_300,
                    tooltip="Delete",
                    on_click=lambda e: deleteFunc(e, event.id))),
        ft.DataCell(ft.Text(event.name)),
        ft.DataCell(ft.Text(event.dateFormated())),
        ft.DataCell(ft.Text(event.progress().name)),
        ft.DataCell(ft.IconButton(icon=ft.Icons.CATEGORY,
                                icon_color=ft.Colors.BLUE_300,
                                tooltip="Categories",
                                on_click=lambda e: e.control.page.go(f"/categories/{event.id}"))),
        ft.DataCell(ft.IconButton(icon=ft.Icons.FITNESS_CENTER,
                                icon_color=ft.Colors.ORANGE_300,
                                tooltip="Disciplines",
                                on_click=lambda e: e.control.page.go(f"/disciplines/{event.id}"))),
        ft.DataCell(ft.IconButton(icon=ft.Icons.BALANCE_ROUNDED,
                                icon_color=ft.Colors.GREEN_300,
                                tooltip="Judges",
                                on_click=lambda e: e.control.page.go(f"/eventJudges/{event.id}"))),
        ft.DataCell(finishButon)
        ]
    return ft.DataRow(cells=cells)

class EventView(View):
    def __init__(self, page: ft.Page, db, redis):
        super().__init__(page, db, redis)
        self.route = "/events"
        self.scroll = ft.ScrollMode.AUTO

        user = self.page.session.get('user')

        def addFunc(e):
            self.page.go("/eventEdit/0")

        def editFunc(e, eventId):
            self.page.go(f"/eventEdit/{eventId}")

        def deleteFunc(e, eventId):
            event = self.db.getEvent(eventId)
            def yes(e):
                self.db.removeEvent(eventId)
                dlg.open = False
                self.table.rows = createRows()
                e.control.page.update()

            def no(e):
                print('cancel')
                dlg.open = False
                e.control.page.update()

            dlg = ft.AlertDialog(
                modal=True,
                content=ft.Text(f"Delete event {event.descr()} ?"),
                actions=[
                    ft.TextButton("Yes", on_click=yes),
                    ft.TextButton("No", on_click=no),
                ],
                actions_alignment=ft.MainAxisAlignment.END)
            e.control.page.overlay.append(dlg)
            dlg.open = True
            e.control.page.update()

        def finishEvent(e, eventId: int, finish: bool):
            event = self.db.getEvent(eventId)
            def yes(e):
                self.db.finishEvent(eventId, finish)
                dlg.open = False
                self.table.rows = createRows()
                e.control.page.update()

            def no(e):
                print('cancel')
                dlg.open = False
                e.control.page.update()

            msg = self.tr.tr('Finish Event' if finish else 'Open Event')

            dlg = ft.AlertDialog(
                modal=True,
                content=ft.Text(f'{msg} {event.descr()} ?'),
                actions=[
                    ft.TextButton(self.tr.tr("Yes"), on_click=yes),
                    ft.TextButton(self.tr.tr("No"), on_click=no),
                ],
                actions_alignment=ft.MainAxisAlignment.END)
            e.control.page.overlay.append(dlg)
            dlg.open = True
            e.control.page.update()
        
        def createRows():
            return [eventAsRow(self.tr, event, editFunc, deleteFunc, finishEvent) for event in self.db.getEvents(user.id)]

        self.table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text(self.tr.tr(h))) for h in header()],
            rows=createRows()
        )

        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr('Help'), on_click=lambda _: self.page.go('/help')), title=ft.Text(f'Events of {user.username}'), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            ft.Row([self.table], scroll=ft.ScrollMode.AUTO),
            ft.Row(
                spacing=0,
                controls=[
                    ft.IconButton(
                        ft.Icons.ADD_CIRCLE,
                        icon_color=ft.Colors.BLUE_300,
                        tooltip="Neues Event",
                        on_click=addFunc
                    )
                ]
            ),
            ft.ElevatedButton("Home", on_click=lambda _: self.page.go("/"))
        ]

class EventEditView(View):
    def __init__(self, page: ft.Page, db, redis, eventId: int):
        super().__init__(page, db, redis)
        self.route = f"/eventEdit/{eventId}"
        self.scroll = ft.ScrollMode.AUTO
        createEvent = eventId == 0

        user = self.page.session.get('user')

        event = self.db.getEvent(eventId) if not createEvent else Event(0, "", user.id, datetime.datetime.now(), False, "")

        name_input = ft.TextField(label="Event Name", width=300, value=event.name)
        event_date_str = event.dateFormated()

        self.event_date = ft.TextField(
            label="event date",
            value=event_date_str,
            disabled=True,
            width=115
        )

        def onChangeDate(e):
            d = e.control.value
            if d:
                self.event_date.value = d.strftime("%d.%m.%Y")
                self.page.update()

        date_input = ft.ElevatedButton(
            "Pick date",
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=lambda e: page.open(
                ft.DatePicker(
                    first_date=datetime.datetime(year=1980, month=1, day=1),
                    last_date=datetime.datetime(year=2030, month=12, day=31),
                    on_change=onChangeDate
                )
            ),
        )
        
        rating_input = ft.TextField(
            label="custom ranking",
            value=event.customRanking,
            multiline=True,
            width=300
        )

        def saveEvent(e):
            name = name_input.value.strip()
            date = self.event_date.value.strip()
            
            if not name or not date:
                self.page.open(ft.SnackBar(ft.Text("Bitte Name und Datum eingeben!"), bgcolor="red"))
                return

            if createEvent:
                self.db.insertEvent(name, user.id, Event.dateFromString(date), rating_input.value)
            else:
                self.db.updateEvent(event.id, name, user.id, Event.dateFromString(date), rating_input.value)

            self.page.go("/events")

        def cancel(e):
            self.page.go("/events")

        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr('Help'), on_click=lambda _: self.page.go('/help')), title=ft.Text("Event erstellen" if createEvent else "Event bearbeiten"),
                      bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            name_input,
            self.event_date,
            date_input,
            rating_input,
            ft.Row(spacing=0, controls=[
                ft.IconButton(icon=ft.Icons.CHECK_CIRCLE, icon_color=ft.Colors.GREEN_300, tooltip="Speichern", on_click=saveEvent),
                ft.IconButton(icon=ft.Icons.CANCEL, icon_color=ft.Colors.RED_300, tooltip="Abbrechen", on_click=cancel),
            ]),
        ]
