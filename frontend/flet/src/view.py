import os
import sys
import flet as ft
from redis import StrictRedis
from translate import tr

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase


def go(page: ft.Page, route: str):
    """Navigate to route (replacement for the removed page.go in flet 1.x)."""
    if page.route == route:
        # push_route does not fire on_route_change if the route is unchanged
        page.on_route_change(ft.RouteChangeEvent(name="route_change", control=page, route=route))
    else:
        page.run_task(page.push_route, route)


def open_url(page: ft.Page, url: str):
    """Open url in the browser (replacement for the removed page.launch_url in flet 1.x)."""
    launcher = page.session.store.get('_url_launcher')
    if launcher is None:
        launcher = ft.UrlLauncher()
        page.session.store.set('_url_launcher', launcher)
    page.run_task(launcher.launch_url, url)


class View(ft.View):
    def __init__(self, page: ft.Page, db, redis, autocommit=True):
        super().__init__()
        # in flet 1.x Control.page is a read-only property, so keep our own reference
        self._jury_page = page
        self.db = db
        self.redis = redis
        user = page.session.store.get('user')
        self.tr = tr(user.language if user else 'en')

    @property
    def page(self) -> ft.Page:
        try:
            return super().page
        except RuntimeError:
            return self._jury_page

    def did_mount(self):
        print(f'{type(self).__name__} did_mount')
        super().update()

    def will_unmount(self):
        print(f'{type(self).__name__} will_unmount')


    def token(self):
        return self.page.session.store.get('token')

    def setToken(self, token: str):
        self.page.session.store.set('token', token)
        user = self.page.session.store.get('user')
        self.redis.setex(token, 3600, str(user.id))

    @staticmethod
    def host() -> str:
        return os.environ['DOMAIN']

    @staticmethod
    def api() -> str:
        return os.environ['SUBDOMAIN_API'] + View.host()
