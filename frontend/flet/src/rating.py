import os
import sys
import flet as ft
from view import View, go, open_url
from datetime import datetime
from translate import tr

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase, Athlete, AthleteRatings, Gender

numFilter = ft.InputFilter(regex_string=r'^(\d+(\.\d*)?|\.\d+)$')

def formatPoints(value):
    if value is None:
        return '-----'
    return '{:.1f}'.format(value)

class RatingSelectEventView(View):
    def __init__(self, page: ft.Page, db, redis):
        super().__init__(page, db, redis)
        self.route = '/rating'
        self.scroll = None

        buttons = [
            ft.Button(
                f"{e.descr()}",
                on_click=lambda _, id=e.id: go(self.page, f'/rating/{id}'),
                width=300
            ) for e in self.db.getAllEvents()
        ]
        buttons.append(ft.Button("Home", on_click=lambda _: go(self.page, "/")))

        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr("Help"), on_click=lambda _: go(self.page, '/help')), title=ft.Text('Select Event'), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            ft.Container(
                content=ft.Column(
                    controls=buttons,
                    scroll=ft.ScrollMode.AUTO,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                expand=True,
                alignment=ft.Alignment.CENTER
            )
        ]

class RatingView(View):
    def __init__(self, page: ft.Page, db, redis, eventId: int):
        super().__init__(page, db, redis)
        self.route = f'/rating/{eventId}'
        self.scroll = ft.ScrollMode.AUTO

        self.user = self.page.session.store.get('user')
        self.tr = tr(self.user.language)
        self.event = self.db.getEvent(eventId)
        self.disciplines = self.db.getEventDisciplines(eventId)
        self.groups = self.db.getEventGroups(eventId)
        self.athletes = []
        
        def selectedDiscipline():
            discipline = self.disciplineEdit.value
            return discipline if discipline and discipline.strip() else None

        def updateAthletes(e):
            self.groupEdit.disabled = selectedDiscipline() is None
            if self.groupEdit.disabled or not self.groupEdit.value:
                self.athletes = []
            else:
                self.athletes = self.db.getEventGroup(self.event.id, self.groupEdit.value)
            self.updateControls()

        self.disciplineEdit = ft.Dropdown(
            label=self.tr.tr("Discipline"),
            width = 300,
            options=[ft.DropdownOption(d.name) for d in self.disciplines],
            on_select=updateAthletes
        )
        self.groupEdit = ft.Dropdown(
            label=self.tr.tr("Group"),
            width = 300,
            options=[ft.DropdownOption(g) for g in self.groups],
            disabled=True,
            on_select=updateAthletes
        )
        self.updateControls()

    def AthleteRatingAsRow(self, athlete: Athlete, discipline: str, editFunc: callable, index: int):
        ratings = self.db.getAthleteAndRatings(athlete.id, self.event.id)
        _, _, ratingId = ratings.ratingOrNone(discipline)
        def remove(e):
            self.db.removeRating(ratingId)
            self.updateControls()

        cells = [
            ft.DataCell(ft.Text(athlete.name())),
            ft.DataCell(ft.Text(ratings.eventCategoryName)),
            ft.DataCell(ft.Text(ratings.prettyOrDefault(discipline))),
            ft.DataCell(ft.Row(spacing=0, controls=[
                ft.IconButton(
                    icon=ft.Icons.EDIT,
                    icon_color=ft.Colors.GREEN_300,
                    tooltip=self.tr.tr("Edit Rating"),
                    on_click=lambda e: editFunc(e, ratings, discipline)),
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED_300,
                    tooltip=self.tr.tr("Delete"),
                    on_click=remove)]))
        ]
        return ft.DataRow(cells=cells, color=ft.Colors.GREY_900 if index % 2 == 1 else None)
        
    def updateControls(self):
        
        def editRating(e, ratings: AthleteRatings, discipline: str):
            print(f'edit athlete="{ratings.athlete.name()}"')
            difficultyContent, executionContent, ratingId = ratings.ratingOrNone(discipline)
            
            d_val = "{:.2f}".format(difficultyContent) if difficultyContent is not None else ""
            e_val = "{:.2f}".format(executionContent) if executionContent is not None else ""

            difficultyEdt = ft.TextField(
                label=self.tr.tr("difficulty"),
                value=d_val,
                width=120,
                read_only=True,
                text_align=ft.TextAlign.CENTER,
            )
            executionEdt = ft.TextField(
                label=self.tr.tr("execution"),
                value=e_val,
                width=120,
                read_only=True,
                text_align=ft.TextAlign.CENTER,
            )

            self.active_field = difficultyEdt

            def highlight_field(front, back):
                self.active_field = front
                front.border_width = 2
                front.border_color = None
                back.border_width = 1
                front.update()
                back.update()

            def set_difficulty(e):
                highlight_field(difficultyEdt, executionEdt)

            def set_execution(e):
                highlight_field(executionEdt, difficultyEdt)

            difficultyEdt.on_focus = set_difficulty
            executionEdt.on_focus = set_execution

            def add_char(char):
                if self.active_field.value is None:
                    self.active_field.value = ""
                
                if self.active_field.value == "0" and char == "0":
                    return
                if self.active_field.value == "0" and char != ".":
                    self.active_field.value = char
                else:
                    self.active_field.value += char
                self.active_field.update()

            def backspace(e):
                if self.active_field.value and len(self.active_field.value) > 0:
                    self.active_field.value = self.active_field.value[:-1]
                    self.active_field.update()

            def digit_btn(text, handler):
                return ft.OutlinedButton(
                    content=text,
                    on_click=handler,
                    expand=1,
                    height=72,
                    style=ft.ButtonStyle(
                        text_style=ft.TextStyle(size=26),
                    ),
                )

            sheet_height = self.page.height * 0.85

            keypad = ft.Column(
                [
                    ft.Row([
                        digit_btn("7", lambda _: add_char("7")),
                        digit_btn("8", lambda _: add_char("8")),
                        digit_btn("9", lambda _: add_char("9")),
                    ], spacing=8),

                    ft.Row([
                        digit_btn("4", lambda _: add_char("4")),
                        digit_btn("5", lambda _: add_char("5")),
                        digit_btn("6", lambda _: add_char("6")),
                    ], spacing=8),

                    ft.Row([
                        digit_btn("1", lambda _: add_char("1")),
                        digit_btn("2", lambda _: add_char("2")),
                        digit_btn("3", lambda _: add_char("3")),
                    ], spacing=8),

                    ft.Row(
                        [
                            digit_btn(".", lambda _: add_char(".")),
                            digit_btn("0", lambda _: add_char("0")),
                            ft.Button(
                                content=ft.Icon(ft.Icons.BACKSPACE_OUTLINED, size=28),
                                on_click=backspace,
                                expand=1,
                                height=72,
                            ),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=8,
            )

            def close_sheet(save):
                sheet.bottom = -sheet_height
                self.page.update()
                self.page.overlay.remove(sheet)
                if save:
                    print(f'update athlete="{ratings.athlete.name()}"')
                    if ratingId is None:
                        self.db.insertRating(ratings.athlete.id, ratings.eventId,
                                            self.user.id, discipline,
                                            difficultyEdt.value, executionEdt.value)
                    else:
                        self.db.updateRating(ratingId, self.user.id, difficultyEdt.value,
                                            executionEdt.value)
                else:
                    print(f'cancel athlete="{ratings.athlete.name()}"')
                self.page.update()
                self.updateControls()

            sheet = ft.Container(
                width=self.page.width,
                height=sheet_height,
                bgcolor=ft.Colors.SURFACE,
                border_radius=ft.BorderRadius.only(top_left=20, top_right=20),
                padding=16,
                bottom=-sheet_height,
                animate_position=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                content=ft.Column(
                    [
                        ft.Text(f'{discipline} / {ratings.eventCategoryName}', size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(f'{ratings.athlete.name()} / {ratings.athlete.birthFormated()}', size=16),
                        ft.Row(controls=[difficultyEdt, executionEdt], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Divider(),
                        keypad,
                        ft.Row([
                                ft.OutlinedButton(
                                    icon_color=ft.Colors.GREEN_300,
                                    icon=ft.Icons.CHECK_ROUNDED,
                                    expand=1,
                                    height=56,
                                    on_click=lambda e: close_sheet(True),
                                ),
                                ft.OutlinedButton(
                                    icon_color=ft.Colors.RED_300,
                                    icon=ft.Icons.CANCEL_ROUNDED,
                                    expand=1,
                                    height=56,
                                    on_click=lambda e: close_sheet(False),
                                ),
                            ],
                            spacing=12,
                        ),
                    ],
                    spacing=12,
                    expand=True,
                ),
            )

            self.page.overlay.append(sheet)
            self.page.update()

            # slide up
            sheet.bottom = 0
            self.page.update()
        
        selected_discipline = self.disciplineEdit.value if self.disciplineEdit.value and self.disciplineEdit.value.strip() else None
        self.table = ft.DataTable(
                columns=[ft.DataColumn(ft.Text(h)) for h in ['name', 'cat', selected_discipline or self.tr.tr('Discipline'), '']],
                rows= [self.AthleteRatingAsRow(athlete, selected_discipline, editRating, i) for i, athlete in enumerate(self.athletes)] if selected_discipline else [],
                column_spacing=10,
                vertical_lines=ft.BorderSide(1, ft.Colors.OUTLINE)
            )

        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr('Help'), on_click=lambda _: go(self.page, '/help')), title=ft.Text(f'Rating'), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            ft.Column(controls=[
                ft.Text(self.event.name, size=30, color=ft.Colors.PINK_600, italic=True),
                ft.Row([self.disciplineEdit, self.groupEdit], wrap=True),
                ft.Row([self.table], scroll=ft.ScrollMode.AUTO),
                ft.Button("Home", on_click=lambda _: go(self.page, "/"))
            ], scroll=ft.ScrollMode.AUTO, expand=True)
        ]
        self.page.update()
