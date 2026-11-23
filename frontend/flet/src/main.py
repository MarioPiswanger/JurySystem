import sys
import os
import flet as ft
from navigation import Navigator

from redis import StrictRedis

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase

def main(page: ft.Page):
    page.title = "Jury System"
    db = JuryDatabase('db', True)
    redis = StrictRedis(host='redis', port=6379, db=0, password='redispass', decode_responses=True)
    navi = Navigator(page, db, redis)
    page.on_route_change = navi.route_change
    page.on_view_pop = navi.view_pop
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    navi.route_change(None)

ft.run(main, view=ft.AppView.WEB_BROWSER, assets_dir="assets")
