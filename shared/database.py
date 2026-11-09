import ast
import pymysql.cursors
import secrets
import bcrypt
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from enum import IntEnum
from typing import List


def multiline_eval(expr: str, context={}):
    "Evaluate several lines of input, returning the result of the last line"
    tree = ast.parse(expr)
    eval_exprs = []
    exec_exprs = []
    for module in tree.body:
        if isinstance(module, ast.Expr):
            eval_exprs.append(module.value)
        else:
            exec_exprs.append(module)
    exec_expr = ast.Module(exec_exprs, type_ignores=[])
    exec(compile(exec_expr, 'file', 'exec'), context)
    results = []
    for eval_expr in eval_exprs:
        results.append(eval(compile(ast.Expression((eval_expr)), 'file', 'eval'), context))
    return '\n'.join([str(r) for r in results])

class Restrictions(IntEnum):
    TRAINER = 0
    HOST = 1
    JUDGE = 2
    ADMIN = 3

class Gender(IntEnum):
    MALE = 0
    FEMALE = 1
    
class RankingType(IntEnum):
    NO_RANKING = 1
    RANKING = 0

@dataclass
class User:
    id: int
    username: str
    hash: str
    email: str
    team: str
    registered: datetime
    expires: datetime
    restrictions: Restrictions
    locked: bool
    hidden: bool
    token: str
    language: str
    
    def valid(self) -> bool:
        return datetime.now() < self.expires and not self.locked
    
    def isHost(self) ->bool:
        return self.restrictions in (Restrictions.HOST, Restrictions.ADMIN)
    
    @staticmethod
    def fromRow(row):
        return User(row['id'], row['username'], row['hash'], row['email'], row['team'], row['registered'], row['expires'], Restrictions(row['restrictions']), row['locked'] != 0, row['hidden'] != 0, row['token'], row['language'])


@dataclass
class Athlete:
    id: int
    givenname: str
    surname: str
    userId: int
    birth: datetime
    gender: Gender
    hidden: bool
    
    @staticmethod
    def fromRow(row):
        return Athlete(row['id'], row['givenname'], row['surname'], row['userId'], row['birth'], Gender(row['gender']), row['hidden'] != 0)
    
    def name(self) -> str:
        return f'{self.givenname} {self.surname}'
    
    def birthFormated(self) -> str:
        return self.birth.strftime('%d.%m.%Y')

    @staticmethod
    def birthFromString(birth: str) -> datetime:
        return datetime.strptime(birth, '%d.%m.%Y')

class Progress(IntEnum):
    PLANNED = 0
    ACTIVE = 1
    FINISHED = 2

@dataclass
class Event:
    id: int
    name: str
    userId: int
    date: datetime
    __finished: bool
    customRanking: str

    @staticmethod
    def fromRow(row):
        return Event(row['id'], row['name'], row['userId'], row['date'], row['finished'] == 1, row['customRanking'])
    
    @staticmethod
    def dateFromString(date: str) -> datetime:
        return datetime.strptime(date, '%d.%m.%Y')

    def dateFormated(self) -> str:
        return self.date.strftime('%d.%m.%Y')
    
    def descr(self) -> str:
        return f'{self.name} / {self.dateFormated()}'
    
    def progress(self, day: date | None = None) -> Progress:
        if day is None:
            day = date.today()
        if self.__finished:
            return Progress.FINISHED
        if day < self.date.date():
            return Progress.PLANNED
        return Progress.ACTIVE

@dataclass
class EventCategory:
    name: str
    eventId: int
    gender: Gender
    birthFrom: datetime
    birthTo: datetime
    rankingType: RankingType
    rankingAlgo: str

    @staticmethod
    def fromRow(row):
        return EventCategory(row['name'], row['eventId'], Gender(row['gender']), row['birthFrom'], row['birthTo'], RankingType(row['rankingType']), row['rankingAlgo'])

    @staticmethod
    def defaultRankingAlgo() -> str:
        return "'gold' if sum > 30 else 'silber' if sum > 20 else 'bronze' if sum > 10 else ''"
    

def allowedCategories(categories: list[EventCategory], athlete: Athlete) -> list[EventCategory]:
    ret = []
    for category in categories:
        if athlete.gender == category.gender and category.birthFrom <= athlete.birth <= category.birthTo:
            ret.append(category)
    return ret

@dataclass
class EventDiscipline:
    name: str
    eventId: int
    
    @staticmethod
    def fromRow(row):
        return EventDiscipline(row['name'], row['eventId'])

@dataclass
class Attendance:
    athleteId: int
    eventId: int
    eventCategoryName: str
    group: str
    
    @staticmethod
    def fromRow(row):
        return Attendance(row['athleteId'], row['eventId'], row['eventCategoryName'], row['group'])

@dataclass
class Rating:
    id: int
    ts: datetime
    athleteId: int
    eventId: int
    userId: int
    eventDisciplineName: str
    difficulty: float
    execution: float

    def sum(self) -> float:
        return self.difficulty + self.execution

    def prettyTuple(self):
        return '{:.2f}'.format(self.difficulty), '{:.2f}'.format(self.execution)

    def pretty(self) -> str:
        d, e = self.prettyTuple()
        return f'{d} / {e}'

    def prettySum(self):
        return '{:.2f}'.format(self.sum())

    def rate(self, difficulty: float, execution: float):
        self.ts = datetime.now()
        self.difficulty = difficulty
        self.execution = execution

    @staticmethod
    def fromRow(row):
        return Rating(row['id'], row['ts'], row['athleteId'], row['eventId'], row['userId'], row['eventDisciplineName'], row['difficulty'], row['execution'])

@dataclass
class AthleteRatings:
    athlete: Athlete
    eventId: int
    eventCategoryName: str
    group: str
    ratings: dict[str, Rating]
    
    def sum(self) -> float:
        return sum(r.sum() for r in self.ratings.values())
    
    def ratingOrNone(self, discipline: str):
        if discipline in self.ratings.keys():
            return self.ratings[discipline].difficulty, self.ratings[discipline].execution, self.ratings[discipline].id
        return None, None, None

    def prettyOrDefault(self, discipline: str, default='---') -> str:
        if discipline in self.ratings.keys():
            return self.ratings[discipline].pretty()
        return default

@dataclass
class AthleteRanking:
    ranking: str
    ratings: AthleteRatings

class JuryDatabase:
    def __init__(self, host: str, autocommit=False):
        self.conn = pymysql.connect(host=host,
                            user='JurySystem',
                            password='asdfuas347lkasudhr',
                            database='JurySystem',
                            cursorclass=pymysql.cursors.DictCursor,
                            autocommit=autocommit)
        self.addInitialUsers()

    def __del__(self):
        if hasattr(self, "conn"):
            self.conn.close()

    def addInitialUsers(self):
        with self.conn.cursor() as cursor:
            if cursor.execute(f'SELECT COUNT(*) FROM `users`;') != 1:
                raise ImportError
            cnt = cursor.fetchone()['COUNT(*)']
            if cnt > 0:
                return

        self.insertUser('admin', 'pass', 'john.doe@example.com', '', Restrictions.ADMIN, 'ge', 1)
        self.insertUser('host', 'pass', 'john.doe@example.com', '', Restrictions.HOST, 'ge', 2)
        self.insertUser('michelhausen', 'pass', 'john.doe@example.com', 'Sportunion Michelhausen', Restrictions.TRAINER, 'en', 3)
        self.insertUser('tulln', 'pass', 'john.doe@example.com', 'Sportunion Tulln', Restrictions.TRAINER, 'ge', 4)
        judgeId = self.insertUser('judge', 'pass', 'john.doe@example.com', '', Restrictions.JUDGE, 'ge', 5)
        self.setUserToken(judgeId, 'asdfasdf')

    def validateUser(self, username: str, password: str):
        with self.conn.cursor() as cursor:
           if cursor.execute(f'SELECT * FROM users WHERE username="{username}";') != 1:
               return None
           row = cursor.fetchone()
           user = User.fromRow(row)
           if bcrypt.checkpw(password.encode(), user.hash.encode()) and user.valid():
               return user.id
           return None

    def validateUserByToken(self, username: str, token: str):
        with self.conn.cursor() as cursor:
           if cursor.execute(f'SELECT * FROM users WHERE username="{username}";') != 1:
               return None
           row = cursor.fetchone()
           user = User.fromRow(row)
           if len(user.token) == 0:
               return None
           if user.token == token and user.valid():
               return user.id
           return None

    def getUser(self, userId: int) -> User:
        with self.conn.cursor() as cursor:
            sql = f'SELECT * FROM users WHERE id="{userId}";'
            cursor.execute(sql)
            return User.fromRow(cursor.fetchone())
        return None
    
    def getUserByName(self, userName: str) -> User:
        with self.conn.cursor() as cursor:
            sql = f'SELECT * FROM users WHERE username="{userName}";'
            cursor.execute(sql)
            return User.fromRow(cursor.fetchone())
        return None

    def insertUser(self, username: str, password: str, email:str, team:str, restrictions: Restrictions, language: str, id=None) -> int:
        locked = 0
        salt = bcrypt.gensalt()
        with self.conn.cursor() as cursor:
            idText, idValue = ("id, ", f"'{id}', ") if id else ('', '')
            token = secrets.token_urlsafe() if restrictions == Restrictions.JUDGE else ''
            sql = f"INSERT INTO users ({idText}username, hash, email, team, registered, expires, restrictions, locked, token, language) VALUES ({idValue}'{username}', '{bcrypt.hashpw(password.encode(), salt).decode()}', '{email}','{team}', '{datetime.now()}', '{datetime.now() + timedelta(weeks=300)}', {restrictions.value}, {locked}, '{token}', '{language}');"
            cnt = cursor.execute(sql)
            if cnt != 1:
                return None
            self.conn.commit()
            return cursor.lastrowid
        return None

    def createPublicRegistration(
        self,
        username: str,
        password: str,
        email: str,
        team: str,
        givenname: str,
        surname: str,
        birth: datetime,
        gender: Gender,
        eventId: int,
        categoryName: str,
    ) -> int:
        passwordHash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        self.conn.begin()
        with self.conn.cursor() as cursor:
            try:
                cursor.execute(
                    "SELECT `date`, `finished`, `deleted` FROM `events` "
                    "WHERE `id` = %s FOR UPDATE",
                    (eventId,),
                )
                event = cursor.fetchone()
                if (
                    event is None
                    or event["deleted"]
                    or event["finished"]
                    or date.today() >= event["date"].date()
                ):
                    raise ValueError("Event-Anmeldung ist nicht mehr möglich.")
                cursor.execute(
                    """SELECT COUNT(*) AS `count` FROM `event_categories`
                    WHERE `eventId` = %s AND `name` = %s AND `gender` = %s
                    AND `birthFrom` <= %s AND `birthTo` >= %s""",
                    (eventId, categoryName, gender.value, birth, birth),
                )
                if cursor.fetchone()["count"] != 1:
                    raise ValueError("Die Wettkampfklasse passt nicht zu den Teilnehmerdaten.")
                cursor.execute(
                    """INSERT INTO `users`
                    (`username`, `hash`, `email`, `team`, `registered`, `expires`,
                     `restrictions`, `locked`, `token`, `language`)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 0, '', 'ge')""",
                    (
                        username,
                        passwordHash,
                        email,
                        team,
                        datetime.now(),
                        datetime.now() + timedelta(weeks=300),
                        Restrictions.TRAINER.value,
                    ),
                )
                userId = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO `athletes`
                    (`givenname`, `surname`, `userId`, `birth`, `gender`)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (givenname, surname, userId, birth, gender.value),
                )
                athleteId = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO `attendances`
                    (`athleteId`, `eventId`, `eventCategoryName`, `group`)
                    VALUES (%s, %s, %s, '')""",
                    (athleteId, eventId, categoryName),
                )
                self.conn.commit()
                return userId
            except (pymysql.MySQLError, ValueError):
                self.conn.rollback()
                raise
    
    def removeUser(self, userId: int) -> bool:
        with self.conn.cursor() as cursor:
            sql = f"DELETE FROM `users` WHERE `users`.`id` = {userId} ;"
            cnt = cursor.execute(sql)
            self.conn.commit()
            return cnt != 0
        return False
    
    def updateUser(self, userId: int, username: str, password: str, email: str, team: str, expires: datetime, restrictions: Restrictions, locked: bool, language:str):
        with self.conn.cursor() as cursor:
            sql = f"UPDATE `users` SET `username` = '{username}',`hash` = '{bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()}', `email` = '{email}', `team` = '{team}', `expires` = '{expires}',`restrictions` = '{restrictions.value}', `locked` = '{1 if locked else 0}', `language` = '{language}' WHERE `users`.`id` = {userId};"
            cnt = cursor.execute(sql)
            self.conn.commit()
            return cnt != 0
        return False
    
    def setUserToken(self, userId: int, token: str) -> None:
        with self.conn.cursor() as cursor:
            sql = f"UPDATE `users` SET `token` = '{token}' WHERE `users`.`id` = {userId};"
            cnt = cursor.execute(sql)
            self.conn.commit()
    
    def recreateUserToken(self, userId: int) -> None:
        self.setUserToken(userId, secrets.token_urlsafe())

    def getAllUsers(self) -> List[User]:
        users = []
        with self.conn.cursor() as cursor:
            cursor.execute('SELECT * FROM users WHERE hidden = 0;')
            for row in cursor.fetchall():
                users.append(User.fromRow(row))
        return users
    
    def getAllJudges(self) -> List[User]:
        users = []
        with self.conn.cursor() as cursor:
            sql = f'SELECT * FROM users WHERE hidden = 0 AND restrictions = {int(Restrictions.JUDGE)};'
            cursor.execute(sql)
            for row in cursor.fetchall():
                users.append(User.fromRow(row))
        return users
    
    def getAthletes(self, userId: int) -> List[Athlete]:
        athletes = []
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT * FROM athletes WHERE userId = {userId} AND hidden = 0;')
            for row in cursor.fetchall():
                athletes.append(Athlete.fromRow(row))
        return athletes
    
    def getAthlete(self, athleteId: int) -> Athlete:
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT * FROM athletes WHERE id = {athleteId};')
            return Athlete.fromRow(cursor.fetchone())
        return None
    
    def insertAthlete(self, givenname: str, surname: str, userId: int, birth: datetime, gender: Gender):
        with self.conn.cursor() as cursor:
            sql = f"INSERT INTO athletes (givenname, surname, userId, birth, gender) VALUES ('{givenname}', '{surname}', '{userId}','{birth}', {gender.value});"
            cnt = cursor.execute(sql)
            if cnt != 1:
                return None
            self.conn.commit()
            return cursor.lastrowid
        return None

    def updateAthlete(self, athleteId: int,  givenname: str, surname: str, userId: int, birth: datetime, gender: Gender):
        with self.conn.cursor() as cursor:
            sql = f"UPDATE `athletes` SET `givenname` = '{givenname}',`surname` = '{surname}', `userId` = '{userId}', `birth` = '{birth}', `gender` = {gender.value} WHERE `athletes`.`id` = {athleteId};"
            cnt = cursor.execute(sql)
            self.conn.commit()
            return cnt != 0
        return False

    def athleteHasAttendances(self, athleteId):
        with self.conn.cursor() as cursor:
            sql = f"SELECT * FROM `attendances` WHERE `athleteId` = {athleteId};"
            return cursor.execute(sql) != 0
        return False

    def hideAthlete(self, athleteId: int, hide: bool):
        with self.conn.cursor() as cursor:
            sql = f"UPDATE `athletes` SET `hidden` = {1 if hide else 0} WHERE `athletes`.`id` = {athleteId};"
            cursor.execute(sql)
            self.conn.commit()

    def removeAthlete(self, athleteId: int) -> bool:
        """An athlete can only be deleted if there are no attendancies any more, 
            otherwise he can only be hidden."""
        if self.athleteHasAttendances(athleteId):
            self.hideAthlete(athleteId, True)
        else:
            with self.conn.cursor() as cursor:
                sql = f"DELETE FROM `athletes` WHERE `athletes`.`id` = {athleteId} ;"
                cnt = cursor.execute(sql)
                self.conn.commit()
                return cnt != 0
        return False
    
    def getAttendances(self, eventId, userId) -> list[Attendance]:
        attendances = []
        with self.conn.cursor() as cursor:
            sql = f"SELECT * FROM `attendances` JOIN `athletes` ON `attendances`.`athleteId` = `athletes`.`id` WHERE `athletes`.`userId` = {userId} AND `eventId` = {eventId} AND `attendances`.`hidden` = 0;"
            cursor.execute(sql)
            for row in cursor.fetchall():
                if len(row['eventCategoryName']) > 0:
                    attendances.append(Attendance.fromRow(row))
        return attendances
    
    def addAttendance(self, eventId: int, athleteId: int, categoryName):
        with self.conn.cursor() as cursor:
            sql = f"INSERT INTO `attendances` (`athleteId`, `eventId`, `eventCategoryName`, `group`) VALUES ('{athleteId}', '{eventId}', '{categoryName}', '');"
            cnt = cursor.execute(sql)
            if cnt != 1:
                return None
            self.conn.commit()
            return cursor.lastrowid
        return None
    
    def setAttendanceCategory(self, eventId: int, athleteId: int, category: str):
        attendance = self._getAttendance(athleteId, eventId)
        if attendance is None:
            self.addAttendance(eventId, athleteId, category)
            return
        with self.conn.cursor() as cursor:
            sql = f"UPDATE `attendances` SET `eventCategoryName` = '{category}', `hidden` = 0 WHERE `athleteId` = {athleteId} AND `eventId` = {eventId};"
            cursor.execute(sql)
            self.conn.commit()

    def setAttendanceGroup(self, eventId: int, athleteId: int, group: str):
        with self.conn.cursor() as cursor:
            sql = f"UPDATE `attendances` SET `group` = '{group}' WHERE `athleteId` = {athleteId} AND `eventId` = {eventId};"
            cursor.execute(sql)
            self.conn.commit()

    def hideAttendance(self, eventId: int, athleteId: int, hide: bool):
        with self.conn.cursor() as cursor:
            sql = f"UPDATE `attendances` SET `hidden` = {1 if hide else 0} WHERE `athleteId` = {athleteId} AND `eventId` = {eventId};"
            cursor.execute(sql)
            self.conn.commit()

    def deleteAttendance(self, eventId: int, athleteId: int, category: str):
        '''may break integrity, only used for automatic tests'''
        with self.conn.cursor() as cursor:
            sql = f"DELETE FROM `attendances` WHERE `athleteId` = {athleteId} AND `eventId` = {eventId} AND `eventCategoryName` = '{category}';"
            cursor.execute(sql)
            self.conn.commit()
    
    def getEvents(self, userId: int) -> List[Event]:
        events = []
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT * FROM events WHERE userId = {userId} AND `deleted` = 0;')
            for row in cursor.fetchall():
                events.append(Event.fromRow(row))
        return events
    
    def getAllEvents(self) -> List[Event]:
        events = []
        with self.conn.cursor() as cursor:
            cursor.execute('SELECT * FROM events WHERE `deleted` = 0 ORDER BY `date`, `name`;')
            for row in cursor.fetchall():
                events.append(Event.fromRow(row))
        return events
    
    def getEvent(self, eventId: int) -> Event:
        with self.conn.cursor() as cursor:
            if cursor.execute(f'SELECT * FROM events WHERE id = {eventId};') > 0:
                return Event.fromRow(cursor.fetchone())
        return None
    
    def insertEvent(self, name: str, userId: int, date: datetime, customRanking: str):
        with self.conn.cursor() as cursor:
            sql = f"INSERT INTO events (name, userId, date, customRanking) VALUES ('{name}', '{userId}', '{date}', '{customRanking}');"
            cnt = cursor.execute(sql)
            if cnt != 1:
                return None
            self.conn.commit()
            return cursor.lastrowid
        return None

    def updateEvent(self, eventId: int,  name: str, userId: int, date: datetime, customRanking: str):
        with self.conn.cursor() as cursor:
            sql = f"UPDATE `events` SET `name` = '{name}', `userId` = '{userId}', `date` = '{date}', `customRanking` = '{customRanking}' WHERE `events`.`id` = {eventId};"
            cnt = cursor.execute(sql)
            self.conn.commit()
            return cnt != 0
        return False
    
    def finishEvent(self, eventId:int, finished: bool):
        with self.conn.cursor() as cursor:
            sql = f"UPDATE `events` SET `finished` = {1 if finished else 0} WHERE `events`.`id` = {eventId};"
            cnt = cursor.execute(sql)
            self.conn.commit()

    def removeEvent(self, eventId: int) -> bool:
        with self.conn.cursor() as cursor:
            sql = f"UPDATE `events` SET `deleted`= 1 WHERE `events`.`id` = {eventId} ;"
            cnt = cursor.execute(sql)
            self.conn.commit()
            return cnt != 0
        return False
    
    def deleteEvent(self, eventId: int):
        '''delte event (only used for tests)'''
        with self.conn.cursor() as cursor:
            sql = f"DELETE FROM `events` WHERE `events`.`id` = {eventId} ;"
            cnt = cursor.execute(sql)
            self.conn.commit()
    
    def getEventCategory(self, eventId: int, eventCategoryName: str) -> EventCategory:
        with self.conn.cursor() as cursor:
            if cursor.execute(f'SELECT * FROM `event_categories` WHERE `eventId` = {eventId} AND `name`= "{eventCategoryName}";'):
                return EventCategory.fromRow(cursor.fetchone())
        return None

    def _getAttendance(self, athleteId: int, eventId: int) -> Attendance:
        with self.conn.cursor() as cursor:
            if cursor.execute(f'SELECT * FROM attendances WHERE athleteId = {athleteId} AND eventId = {eventId};'):
                return Attendance.fromRow(cursor.fetchone())
        return None

    def getAttendance(self, athleteId: int, eventId: int) -> Attendance:
        with self.conn.cursor() as cursor:
            if cursor.execute(f'SELECT * FROM attendances WHERE athleteId = {athleteId} AND eventId = {eventId} AND hidden = 0;'):
                return Attendance.fromRow(cursor.fetchone())
        return None
 
    def getEventAttendances(self, eventId: int, eventCategoryName: str='') -> list[Attendance]:
        attendances = []
        with self.conn.cursor() as cursor:
            category = f' AND `eventCategoryName` = "{eventCategoryName}"' if len(eventCategoryName) > 0 else ''
            cursor.execute(f'SELECT * FROM attendances WHERE eventId = {eventId}{category} AND hidden = 0;')
            for row in cursor.fetchall():
                attendances.append(Attendance.fromRow(row))
        return attendances

    def getEventCategoryAthleteIds(self, eventId: int, eventCategoryName: str) -> list[int]:
        athleteIds = []
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT `athleteId` FROM `attendances` WHERE `eventId` = {eventId} AND `eventCategoryName` = "{eventCategoryName}" AND `hidden` = 0;')
            for row in cursor.fetchall():
                athleteIds.append(int(row['athleteId']))
        return athleteIds
    
    def getEventRatings(self, eventId: int, max: int) -> list[Rating]:
        ratings = []
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT * FROM ratings WHERE eventId = {eventId} ORDER BY id DESC LIMIT {max};')
            for row in cursor.fetchall():
                ratings.append(Rating.fromRow(row))
        return ratings
    
    def getRecentRatingTs(self, eventId: int) -> datetime:
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT MAX(`ts`) as maxTs FROM `ratings`;')
            return cursor.fetchone()['maxTs']
        return None

    def getEventDisciplines(self, eventId: int) -> list[EventDiscipline]:
        disciplines = []
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT * FROM `event_disciplines` WHERE eventId = {eventId} ORDER BY name;')
            for row in cursor.fetchall():
                disciplines.append(EventDiscipline.fromRow(row))
        return disciplines

    def isValidEventDiscipline(self, eventId: int, disciplineName: str) -> bool:
        if disciplineName is None:
            return False

        disciplineName = disciplineName.strip()
        if disciplineName == '' or disciplineName.lower() == 'none':
            return False

        with self.conn.cursor() as cursor:
            sql = 'SELECT COUNT(*) AS cnt FROM `event_disciplines` WHERE `eventId` = %s AND `name` = %s;'
            cursor.execute(sql, (eventId, disciplineName))
            return cursor.fetchone()['cnt'] == 1
    
    def getEventDisciplinesEnableRemove(self, eventId: int) -> list[(EventDiscipline, bool)]:
        disciplines = []
        for discipline in self.getEventDisciplines(eventId):
            disciplines.append((discipline, self.canRemoveEventDiscipline(discipline)))
        return disciplines

    def insertEventDiscipline(self, discipline: EventDiscipline):
        with self.conn.cursor() as cursor:
            cnt = cursor.execute(f'INSERT INTO `event_disciplines` (`name`, `eventId`) VALUES ("{discipline.name}", "{discipline.eventId}");')
            if cnt != 1:
                return
            self.conn.commit()

    def canRemoveEventDiscipline(self, discipline: EventDiscipline) -> bool:
        with self.conn.cursor() as cursor:
            res = cursor.execute(f'SELECT COUNT(*) FROM `ratings` WHERE `eventId`="{discipline.eventId}" AND `eventDisciplineName`="{discipline.name}";')
            if res != 1:
                return False
            cnt = cursor.fetchone()['COUNT(*)']
            if cnt == 0:
                return True
        return False

    def removeEventDiscipline(self, discipline: EventDiscipline) -> bool:
        if not self.canRemoveEventDiscipline(discipline):
            return False
        with self.conn.cursor() as cursor:
            sql = f'DELETE FROM event_disciplines WHERE `event_disciplines`.`eventId` = "{discipline.eventId}" AND `event_disciplines`.`name` = "{discipline.name}";'
            cnt = cursor.execute(sql)
            self.conn.commit()
            return cnt != 0
        return False

    def getEventCategories(self, eventId: int) -> list[EventCategory]:
        categories = []
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT * FROM `event_categories` WHERE eventId = {eventId} ORDER BY name;')
            for row in cursor.fetchall():
                categories.append(EventCategory.fromRow(row))
        return categories

    def getEventGroups(self, eventId: int) -> list[str]:
        groups = []
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT DISTINCT `group` FROM `attendances` WHERE eventId = {eventId} AND `hidden` = 0 AND TRIM(`group`) <> "" ORDER BY `group`;')
            for row in cursor.fetchall():
                groups.append(row['group'])
        return groups
    
    def getEventGroup(self, eventId: int, group: str) -> list[Athlete]:
        athletes = []
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT `athletes`.* FROM `attendances` JOIN `athletes` ON athletes.id=attendances.athleteId WHERE `attendances`.`eventId` = {eventId} AND `attendances`.`group` = "{group}" AND `attendances`.`hidden` = 0;')
            for row in cursor.fetchall():
                athletes.append(Athlete.fromRow(row))
        return athletes

    def getEventsofJudge(self, judgeId: int) -> list[Event]:
        events = []
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT `events`.* FROM `event_judges` JOIN `events` ON events.id=event_judges.eventId WHERE `event_judges`.`userId` = {judgeId} AND `events`.`deleted`=0;')
            for row in cursor.fetchall():
                events.append(Event.fromRow(row))
        return events

    def getEventJudges(self, eventId: int) -> list[User]:
        users = []
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT `users`.* FROM `event_judges` JOIN `users` ON users.id=event_judges.userId WHERE `event_judges`.`eventId` = {eventId};')
            for row in cursor.fetchall():
                users.append(User.fromRow(row))
        return users
    
    def addEventJudge(self, eventId: int, judgeId: int):
        with self.conn.cursor() as cursor:
            cnt = cursor.execute(f'INSERT INTO `event_judges` (`eventId`, `userId`) VALUES ("{eventId}", "{judgeId}");')
            if cnt != 1:
                return
            self.conn.commit()

    def canRemoveEventJudge(self, eventId: int, judgeId: int) -> bool:
        with self.conn.cursor() as cursor:
            res = cursor.execute(f'SELECT COUNT(*) FROM `ratings` WHERE `eventId`="{eventId}" AND `userId`="{judgeId}";')
            if res != 1:
                return False
            cnt = cursor.fetchone()['COUNT(*)']
            if cnt == 0:
                return True
        return False

    def getEventJudgesEnableRemove(self, eventId: int) -> list[(int, str, bool)]:
        judges = []
        for judge in self.getEventJudges(eventId):
            user = self.getUser(judge.id)
            judges.append((user.id, user.username, self.canRemoveEventJudge(eventId, user.id)))
        return judges

    def removeEventJudge(self, eventId: int, judgeId: int) -> bool:
        if not self.canRemoveEventJudge(eventId, judgeId):
            return False
        with self.conn.cursor() as cursor:
            sql = f'DELETE FROM event_judges WHERE `event_judges`.`eventId` = {eventId} AND `event_judges`.`userId` = {judgeId};'
            cnt = cursor.execute(sql)
            self.conn.commit()
            return cnt != 0
        return False

    def getAthleteRatings(self, athleteId: int, eventId: int) -> list[Rating]:
        ratings = {}
        with self.conn.cursor() as cursor:
            cursor.execute(f'SELECT * FROM `ratings` WHERE `eventId` = {eventId} AND `athleteId` = "{athleteId}";')
            for row in cursor.fetchall():
                rating = Rating.fromRow(row)
                ratings[rating.eventDisciplineName] = rating
        return ratings

    def getAthleteAndRatings(self, athleteId: int, eventId: int) -> AthleteRatings:
        athlete = self.getAthlete(athleteId)
        attendance = self.getAttendance(athleteId, eventId)
        return AthleteRatings(athlete, eventId, attendance.eventCategoryName, attendance.group, self.getAthleteRatings(athleteId, eventId))

    def _getEventCategoryRankings(self, eventId, category: EventCategory) -> list[AthleteRanking]:
        customRanking = self.getEvent(eventId).customRanking
        rankings = []
        ratings = [self.getAthleteAndRatings(athleteId, eventId) for athleteId in self.getEventCategoryAthleteIds(eventId, category.name)]
        ratings.sort(key=lambda rating: rating.sum(), reverse=True)
        if category.rankingType == RankingType.RANKING:
            prev = (None, None)
            for i, rating in enumerate(ratings, 1):
                ratingSum = rating.sum()
                if ratingSum == 0.0:
                    rankings.append(AthleteRanking('DNF', rating))
                else:
                    if prev[0] is None:
                        rank = i
                    else:
                        rank = prev[1] if math.isclose(ratingSum, prev[0], abs_tol=1e-3) else i
                    rankings.append(AthleteRanking(str(rank), rating))
                    prev = ratingSum, rank
        elif category.rankingType == RankingType.NO_RANKING:
            for rating in ratings:
                ratingSum = round(rating.sum(), 6)
                if ratingSum == 0.0:
                    rankings.append(AthleteRanking('DNF', rating))
                else:
                    rankings.append(AthleteRanking(multiline_eval(f'{customRanking}\n{category.rankingAlgo}', {'sum':ratingSum}), rating))
        return rankings

    def getEventCategoryRankings(self, eventId: int, eventCategoryName: str) -> list[AthleteRanking]:
        category = self.getEventCategory(eventId, eventCategoryName)
        return self._getEventCategoryRankings(eventId, category)

    def insertEventCategory(self, category: EventCategory) -> bool:
        with self.conn.cursor() as cursor:
            sql = "INSERT INTO `event_categories` (`name`, `eventId`, `gender`, `birthFrom`, `birthTo`, `rankingType`, `rankingAlgo`) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            try:
                cursor.execute(sql, (category.name, category.eventId, category.gender.value, category.birthFrom, category.birthTo, category.rankingType.value, category.rankingAlgo))
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error inserting event category: {e}")
                return False

    def updateEventCategory(self, category: EventCategory, oldName: str) -> bool:
        with self.conn.cursor() as cursor:
            sql = "UPDATE `event_categories` SET `name` = %s, `gender` = %s, `birthFrom` = %s, `birthTo` = %s, `rankingType` = %s, `rankingAlgo` = %s WHERE `eventId` = %s AND `name` = %s"
            try:
                cursor.execute(sql, (category.name, category.gender.value, category.birthFrom, category.birthTo, category.rankingType.value, category.rankingAlgo, category.eventId, oldName))
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error updating event category: {e}")
                return False

    def removeEventCategory(self, eventId: int, name: str) -> bool:
        with self.conn.cursor() as cursor:
            sql = "DELETE FROM `event_categories` WHERE `eventId` = %s AND `name` = %s"
            try:
                cursor.execute(sql, (eventId, name))
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error deleting event category: {e}")
                return False

    def updateRating(self, ratingId: int, userId: int, difficulty: float, execution: float):
        with self.conn.cursor() as cursor:
            sql = f"UPDATE `ratings` SET`ts`='{datetime.now()}', `userId`='{userId}', `difficulty`='{difficulty}', `execution`='{execution}' WHERE `id`='{ratingId}'"
            cnt = cursor.execute(sql)
            if cnt != 1:
                return None
            self.conn.commit()
            return cursor.lastrowid
        return None

    def insertRating(self, athleteId: int, eventId: int, userId: int, eventDisciplineName: str, difficulty: float, execution: float):
        if not self.isValidEventDiscipline(eventId, eventDisciplineName):
            return None

        eventDisciplineName = eventDisciplineName.strip()

        with self.conn.cursor() as cursor:
            sql = f"INSERT INTO `ratings` (athleteId, eventId, ts, userId, eventDisciplineName, difficulty, execution) VALUES ('{athleteId}', '{eventId}', '{datetime.now()}', '{userId}', '{eventDisciplineName}', '{difficulty}', '{execution}');"
            cnt = cursor.execute(sql)
            if cnt != 1:
                return None
            self.conn.commit()
            return cursor.lastrowid
        return None
    
    def removeRating(self, ratingId: int):
        with self.conn.cursor() as cursor:
            sql = f"DELETE FROM `ratings` WHERE `ratings`.`id` = '{ratingId}';"
            cnt = cursor.execute(sql)
            self.conn.commit()
            return cnt != 0
        return False
