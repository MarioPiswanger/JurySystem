import os
import sys
import flet as ft
from view import View, go, open_url
import asyncio
import time
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase, User, Athlete, Attendance, Event, Progress, Rating


def _display_text(value):
    return "" if value is None else str(value)

def header():
    return ['Name', 'Team', 'Category', 'Discipline', 'Rating']

def ratingAsRow(user: User, athlete: Athlete, attendance: Attendance, event: Event, rating: Rating):
    cells = [
        ft.DataCell(ft.Text(_display_text(athlete.name() if athlete else None))),
        ft.DataCell(ft.Text(_display_text(user.team if user else None))),
        ft.DataCell(ft.Text(_display_text(attendance.eventCategoryName if attendance else None))),
        ft.DataCell(ft.Text(_display_text(rating.eventDisciplineName))),
        ft.DataCell(ft.Text(_display_text(rating.prettySum()))),
        ]
    return ft.DataRow(cells=cells)

class LiveEventView(View):
    def __init__(self, page: ft.Page, db, redis, eventId):
        super().__init__(page, db, redis)
        self.route =f'/public/liveEvent/{eventId}'
        self.scroll = ft.ScrollMode.AUTO

        self._running = True

        async def handle_disconnect(e):
            self._running = False
            print('stopped live update')

        def onServerTime():
            t = time.strftime('%H:%M:%S', time.localtime())
            self.updateTableIfNewer()
            self.controls = [
                ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr('Help'), on_click=lambda _: go(self.page, '/help')), title=ft.Text(f'Live ratings of {self.event.name}, {t}'), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
                ft.Row([self.table], scroll=ft.ScrollMode.AUTO)
            ]
            self.page.update()

        # flet 1.x: page updates must happen on the event loop, not in a background thread
        async def liveUpdate():
            while self._running:
                await asyncio.sleep(1)
                if not self._running or all(v is not self for v in self.page.views):
                    break
                onServerTime()

        self.page.on_disconnect = handle_disconnect

        self.event = self.db.getEvent(eventId)
        self.recentRatingTs = None
        self.updateTableIfNewer()

        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr('Help'), on_click=lambda _: go(self.page, '/help')), title=ft.Text(f'Live ratings of {self.event.name}'), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            ft.Row([self.table], scroll=ft.ScrollMode.AUTO)
        ]
        self.page.run_task(liveUpdate)

    def will_unmount(self):
        self._running = False
        super().will_unmount()

    def updateTableIfNewer(self):
        ratingTs = self.db.getRecentRatingTs(self.event.id)
        if self.recentRatingTs is not None and ratingTs <= self.recentRatingTs:
            return
        print(f'{ratingTs=}, {self.recentRatingTs=}')
        self.recentRatingTs = ratingTs
        rows = []
        maxRows = 25 # todo this should be a setting
        for rating in self.db.getEventRatings(self.event.id, maxRows):
            athlete = self.db.getAthlete(rating.athleteId)
            user = self.db.getUser(athlete.userId)
            att = self.db.getAttendance(athlete.id, self.event.id)
            rows.append(ratingAsRow(user, athlete, att, self.event, rating))
        print(f'extracted {len(rows)} ratings')
        self.table = ft.DataTable(
                columns=[ft.DataColumn(ft.Text(h)) for h in header()],
                rows=rows,
                column_spacing=5,
                vertical_lines=ft.BorderSide(1, ft.Colors.OUTLINE)
            )