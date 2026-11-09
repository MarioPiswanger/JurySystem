import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "."))
from database import *

@dataclass
class Route():
    name: str
    route: str
    allowed: list[Restrictions]
    
    def isAllowed(self, user: User) -> bool:
        if user.restrictions == Restrictions.ADMIN:
            return True
        for allowed in self.allowed:
            if user.restrictions.value == allowed.value:
                return True
        return False

routes = [
    Route("Users", "/users", [Restrictions.ADMIN]),
    Route("Athletes", "/athletes", [Restrictions.TRAINER]),
    Route("Attendances", "/attendances", [Restrictions.HOST, Restrictions.TRAINER]),
    Route("Events", "/events", [Restrictions.HOST]),
    Route("Rating", "/rating", [Restrictions.HOST, Restrictions.JUDGE]),
    Route("Ranking", "/ranking", [Restrictions.HOST, Restrictions.TRAINER])
]

def allowedRoutes(user: User) -> list[Route]:
    ret = []
    if not user:
        return ret
    for route in routes:
        if route.isAllowed(user):
            ret.append(route)
    return ret