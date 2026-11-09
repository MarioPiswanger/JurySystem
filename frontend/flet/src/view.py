import os
import sys
import flet as ft
from redis import StrictRedis
from translate import tr

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase

class View(ft.View):
    def __init__(self, page: ft.Page, db, redis, autocommit=True):
        super().__init__()
        self.page = page
        self.db = db
        self.redis = redis
        user = self.page.session.get('user')
        self.tr = tr(user.language if user else 'en')

    def did_mount(self):
        print(f'{type(self).__name__} did_mount')
        super().update()

    def will_unmount(self):
        print(f'{type(self).__name__} will_unmount')


    def token(self):
        return self.page.session.get('token')

    def setToken(self, token: str):
        self.page.session.set('token', token)
        user = self.page.session.get('user')
        self.redis.setex(token, 3600, str(user.id))

    @staticmethod
    def host() -> str:
        return os.environ['DOMAIN']
    
    @staticmethod
    def api() -> str:
        return os.environ['SUBDOMAIN_API'] + View.host()