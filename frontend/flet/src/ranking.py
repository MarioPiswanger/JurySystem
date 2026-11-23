import os
import sys
import flet as ft
from view import View, go, open_url

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase, Athlete, AthleteRatings, AthleteRanking, Gender

def pretty(val):
    return '{:.1f}'.format(val)

def ratingCell(ratings: AthleteRatings, discipline: str):
    if discipline not in ratings.ratings.keys():
        return ft.DataCell(ft.Text('---'))
    rating = ratings.ratings[discipline]
    return ft.DataCell(ft.Row(spacing=5, controls=[ft.Text(pretty(rating.difficulty)), ft.Text(pretty(rating.execution))]))
    
class RankingView(View):
    def __init__(self, page: ft.Page, db, redis, eventId: int):
        super().__init__(page, db, redis)
        self.route = f'ranking/{eventId}'
        self.scroll = ft.ScrollMode.AUTO

        self.event = self.db.getEvent(eventId)
        self.disciplines = self.db.getEventDisciplines(eventId)
        self.categories = self.db.getEventCategories(eventId)
        self.rankings = []
        
        def updateRankings(e):
            if self.categoryEdit.value == 'All':
                print(f'Selected All: {len(self.categories)}')
                self.rankings = []
                for category in self.categories:
                    self.rankings += self.db.getEventCategoryRankings(self.event.id, category.name)
            else:
                self.rankings = self.db.getEventCategoryRankings(self.event.id, self.categoryEdit.value)
            self.updateControls()

        self.categoryEdit = ft.Dropdown(
            label="Category",
            width = 300,
            options=[ft.DropdownOption('All')] + [ft.DropdownOption(d.name) for d in self.categories],
            on_select=updateRankings
        )

        self.updateControls()

    def AthleteRankingAsRow(self, ranking: AthleteRanking, index: int):
        cells = [
            ft.DataCell(ft.Text(str(index + 1))),
            ft.DataCell(ft.Text(ranking.ratings.eventCategoryName)),
            ft.DataCell(ft.Text(str(ranking.ratings.group or ''))),
            ft.DataCell(ft.Text(str(ranking.ranking))),
            ft.DataCell(ft.Text(ranking.ratings.athlete.name()))
            ]
        cells += [ratingCell(ranking.ratings, d.name) for d in self.disciplines]
        cells.append(ft.DataCell(ft.Text('{:.2f}'.format(ranking.ratings.sum()))))
        return ft.DataRow(cells=cells, color=ft.Colors.GREY_900 if index % 2 == 1 else None)
        
    def updateControls(self):
        self.table = ft.DataTable(
                columns=[ft.DataColumn(ft.Text(h)) for h in ['', 'category', 'group', 'rank', 'name'] + [d.name for d in self.disciplines] + ['sum']],
                rows= [self.AthleteRankingAsRow(ranking, i) for i, ranking in enumerate(self.rankings)]
            )

        def printList(e, d):
            if self.categoryEdit.value:
                open_url(self.page, f'https://{View.api()}/ranking/{self.token()}/{self.event.id}/{self.categoryEdit.value}/{d}')

        def printCert(e):
            if self.categoryEdit.value:
                open_url(self.page, f'https://{View.api()}/certificate/{self.token()}/{self.event.id}/{self.categoryEdit.value}')

        def exportXlsx(e):
            if self.categoryEdit.value:
                open_url(self.page, f'https://{View.api()}/ranking_xlsx/{self.token()}/{self.event.id}/{self.categoryEdit.value}')

        controls = []
        disablePdf = self.categoryEdit.value == 'All'
        iconColor = ft.Colors.GREY_300 if disablePdf else ft.Colors.BLUE_300
        if len(self.table.rows) > 0:
            controls.append(
                ft.IconButton(ft.Icons.FORMAT_LIST_NUMBERED,
                              icon_color=iconColor,
                              tooltip="results",
                              disabled=disablePdf,
                              on_click=lambda e: printList(e, 0)))
            controls.append(
                ft.IconButton(ft.Icons.LIST_ALT,
                              icon_color=iconColor,
                              tooltip="details",
                              disabled=disablePdf,
                              on_click=lambda e: printList(e, 1)))
            controls.append(
                ft.IconButton(ft.Icons.PICTURE_AS_PDF,
                              icon_color=iconColor,
                              tooltip="certificates",
                              disabled=disablePdf,
                              on_click=printCert))
            controls.append(
                ft.IconButton(ft.Icons.SAVE,
                              icon_color=ft.Colors.BLUE_300,
                              tooltip="xlsx",
                              on_click=exportXlsx))

        controls.append(ft.Button("Home", on_click=lambda _: go(self.page, "/")))

        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr('Help'), on_click=lambda _: go(self.page, '/help')), title=ft.Text('Ranking'), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            ft.Text(self.event.name, size=30, color=ft.Colors.PINK_600, italic=True),
            self.categoryEdit,
            ft.Row([self.table], scroll=ft.ScrollMode.AUTO),
            ft.Row(controls=controls)]
        self.page.update()
