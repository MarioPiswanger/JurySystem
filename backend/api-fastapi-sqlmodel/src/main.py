import io
import os
import sys
import base64
import json
import re
import uuid
from pathlib import Path
from fastapi import FastAPI, Response, Request, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from datetime import datetime
import httpx
import qrcode
from openpyxl import Workbook
from io import BytesIO
from redis import StrictRedis

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase, Athlete

r = StrictRedis(host='redis', port=6379, db=0, password='redispass', decode_responses=True)

api = FastAPI()
api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"https://{os.environ.get('SUBDOMAIN_JURY', '')}{os.environ.get('DOMAIN', '')}"
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

api.mount("/static", StaticFiles(directory="static"), name="static")
env = Environment(loader=FileSystemLoader('templates'))
UPLOAD_DIR = Path(os.environ.get(
    "UPLOAD_DIR",
    os.path.join(os.path.dirname(__file__), "..", "uploads"),
))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_INDEX = UPLOAD_DIR / "index.json"
MAX_IMAGE_BYTES = 15 * 1024 * 1024
OCR_URL = os.environ.get("BIB_OCR_URL", "http://bib-ocr:8000")

def createResponse(template: str, context: dict, filename: str) -> Response:
    template = env.get_template('table.html')
    rendered_html = template.render(context)
    pdf_file = HTML(string=rendered_html).write_pdf()
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return Response(pdf_file, headers=headers, media_type='application/pdf')

def createXlsxResponse(headers: list[str], tables: list[tuple[str, list[list]]], filename: str, sheet_title: str = 'Export') -> StreamingResponse:
    output = BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = alphaNum(sheet_title)[:31] or 'Export'

    for index, (table_title, rows) in enumerate(tables):
        if index > 0:
            ws.append([])
        if table_title:
            ws.append([table_title])
        ws.append(headers)
        for row in rows:
            ws.append(row)

    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        },
    )

def alphaNum(text: str) -> str:
    return ''.join(x for x in text if x.isalnum())


def validateToken(token: str, userId: int | None = None) -> None:
    tokenUserId = r.get(token)
    if tokenUserId is None or (
        userId is not None and tokenUserId != str(userId)
    ):
        raise HTTPException(
            status_code=401,
            detail="unautohrized"
        )

def buildAthletesTable(db: JuryDatabase, userId: int):
    user = db.getUser(userId)
    data = [[athlete.name(), athlete.birthFormated(), athlete.gender.name] for athlete in db.getAthletes(userId)]
    return user, ['name', 'birth', 'gender'], [('', data)]

def buildAttendancesTables(db: JuryDatabase, userId: int, eventId: int):
    event = db.getEvent(eventId)
    athleteAttendances = []

    user = db.getUser(userId)
    if user.isHost():
        for attendance in db.getEventAttendances(event.id):
            athlete = db.getAthlete(attendance.athleteId)
            team = db.getUser(athlete.userId).team
            athleteAttendances.append((attendance, team, athlete))
    else:
        for attendance in db.getAttendances(eventId, userId):
            athleteAttendances.append((attendance, user.team, db.getAthlete(attendance.athleteId)))

    # sort by group, team, givenname
    athleteAttendances.sort(key=lambda t: (t[0].group, t[1], t[2].givenname))

    data = [[t, a.name(), a.birthFormated(), a.gender.name, b.eventCategoryName, b.group] for b, t, a in athleteAttendances]

    # group by group
    tables = []
    if user.isHost():
        prevGroup = None
        for row in data:
            if prevGroup != row[5]:
                tables.append((row[5], []))
                prevGroup = row[5]
            tables[-1][1].append(row)
    else:
        tables = [('', data)]

    return user, event, ['team', 'name', 'birth', 'gender', 'category', 'group'], tables

@api.get("/test")
async def test():
    return {"message": f"API running {datetime.now()}"}


@api.post("/images/upload/{eventId}/{userId}/{token}")
async def uploadImage(
    eventId: int,
    userId: int,
    token: str,
    image: UploadFile = File(...),
):
    validateToken(token, userId)
    db = JuryDatabase("db")
    user = db.getUser(userId)
    if user is None or not user.isHost():
        raise HTTPException(status_code=403, detail="Nur Hosts dürfen Bilder hochladen.")
    if not any(event.id == eventId for event in db.getAllEvents()):
        raise HTTPException(status_code=404, detail="Event nicht gefunden.")

    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"} or image.content_type not in {
        "image/jpeg",
        "image/png",
    }:
        raise HTTPException(status_code=415, detail="Nur JPEG- und PNG-Bilder sind erlaubt.")

    imageBytes = await image.read(MAX_IMAGE_BYTES + 1)
    if len(imageBytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Bild ist zu groß (max. 15 MB).")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            ocrResponse = await client.post(
                f"{OCR_URL.rstrip('/')}/detect",
                files={"image": (image.filename, imageBytes, image.content_type)},
            )
            ocrResponse.raise_for_status()
            detected = ocrResponse.json()
    except httpx.RequestError as error:
        raise HTTPException(
            status_code=503,
            detail="Der Startnummern-Erkennungsdienst ist nicht erreichbar.",
        ) from error
    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail="Der Startnummern-Erkennungsdienst konnte das Bild nicht auswerten.",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail="Der Startnummern-Erkennungsdienst hat eine ungültige Antwort geliefert.",
        ) from error

    try:
        numbers = sorted(
            {
                str(item["number"])
                for item in detected["numbers"]
                if re.fullmatch(r"\d{1,4}", str(item["number"]))
            }
        )
    except (KeyError, TypeError) as error:
        raise HTTPException(
            status_code=502,
            detail="Die Erkennungsantwort enthält keine gültigen Startnummern.",
        ) from error

    filename = f"{uuid.uuid4().hex}{'.png' if suffix == '.png' else '.jpg'}"
    destination = UPLOAD_DIR / filename
    destination.write_bytes(imageBytes)

    records = json.loads(IMAGE_INDEX.read_text(encoding="utf-8")) if IMAGE_INDEX.exists() else []
    records.append({"filename": filename, "eventId": eventId, "numbers": numbers})
    temporaryIndex = IMAGE_INDEX.with_suffix(".tmp")
    temporaryIndex.write_text(
        json.dumps(records, ensure_ascii=False),
        encoding="utf-8",
    )
    temporaryIndex.replace(IMAGE_INDEX)
    return {"filename": filename, "numbers": numbers}


@api.get("/images/search/{eventId}/{number}")
async def searchImages(eventId: int, number: str):
    if not re.fullmatch(r"\d{1,4}", number):
        raise HTTPException(status_code=400, detail="Ungültige Startnummer.")
    records = json.loads(IMAGE_INDEX.read_text(encoding="utf-8")) if IMAGE_INDEX.exists() else []
    return {
        "images": [
            {"filename": record["filename"], "url": f"/images/files/{record['filename']}"}
            for record in records
            if record.get("eventId") == eventId and number in record.get("numbers", [])
        ]
    }


@api.get("/images/files/{filename}")
async def getImage(filename: str):
    if not re.fullmatch(r"[a-f0-9]{32}\.(jpg|png)", filename):
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    path = UPLOAD_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    mediaType = "image/png" if filename.endswith(".png") else "image/jpeg"
    return FileResponse(path, media_type=mediaType)

@api.get('/athletes/{token}/{userId}', response_class=HTMLResponse)
async def athletes(userId: int, token: str):
    validateToken(token)
    db = JuryDatabase('db')
    user, headers, tables = buildAthletesTable(db, userId)

    context = {
            "orientation": 'A4 portrait',
            "title": f'Athletes of {user.team}',
            "headers": headers,
            "tables": tables
        }
    return createResponse('table.html', context, f'athletes_{alphaNum(user.team)}.pdf')

@api.get('/athletes_xlsx/{token}/{userId}')
async def athletes_xlsx(userId: int, token: str):
    validateToken(token)
    db = JuryDatabase('db')
    user, headers, tables = buildAthletesTable(db, userId)
    return createXlsxResponse(headers, tables, f'athletes_{alphaNum(user.team)}.xlsx', user.team)

@api.get('/attendances/{token}/{userId}/{eventId}', response_class=HTMLResponse)
async def attendances(userId: int, eventId: int, token: str):
    validateToken(token)
    db = JuryDatabase('db')
    user, event, headers, tables = buildAttendancesTables(db, userId, eventId)

    title = f'Attendances for {event.descr()}'
    if not user.isHost():
        title += f' of {user.team}'

    context = {
            "orientation": 'A4 portrait',
            "title": title,
            "headers": headers,
            "tables": tables
        }
    return createResponse('table.html', context, f'attendance_{alphaNum(event.name)}_{alphaNum(user.team)}.pdf')

@api.get('/attendances_xlsx/{token}/{userId}/{eventId}')
async def attendances_xlsx(userId: int, eventId: int, token: str):
    validateToken(token)
    db = JuryDatabase('db')
    user, event, headers, tables = buildAttendancesTables(db, userId, eventId)
    return createXlsxResponse(headers, tables, f'attendance_{alphaNum(event.name)}_{alphaNum(user.team)}.xlsx', event.name)

@api.get('/results/{eventId}', response_class=HTMLResponse)
async def results(eventId: int):
    db = JuryDatabase('db')
    event = db.getEvent(eventId)
    disciplines = db.getEventDisciplines(eventId)
    tables = []
    for category in db.getEventCategories(eventId):
        data = []
        for rank in db.getEventCategoryRankings(eventId, category.name):
            athlete = rank.ratings.athlete
            ratingData = []
            for discipline in disciplines:
                ratingData.append(rank.ratings.prettyOrDefault(discipline.name))
            user = db.getUser(athlete.userId)
            data.append([rank.ranking, athlete.name(), user.team] + ratingData + [rank.ratings.sum()])
        if len(data):
            tables.append((category.name, data))

    context = {
            "orientation": 'A4 landscape',
            "title": f'Rankings for {event.descr()}',
            "headers": ['rank', 'name', 'team'] + [d.name for d in disciplines] + ['rating'],
            "tables": tables
        }
    return createResponse('table.html', context, f'{event.name}.pdf')

@api.get('/results_xlsx/{eventId}')
async def results_xlsx(eventId: int):
    db = JuryDatabase('db')
    event = db.getEvent(eventId)
    disciplines = db.getEventDisciplines(eventId)
    rows = []
    for category in db.getEventCategories(eventId):
        for rank in db.getEventCategoryRankings(eventId, category.name):
            athlete = rank.ratings.athlete
            ratingData = []
            for discipline in disciplines:
                ratingData.append(rank.ratings.prettyOrDefault(discipline.name))
            user = db.getUser(athlete.userId)
            rows.append([category.name, rank.ranking, athlete.name(), user.team, rank.ratings.group] + ratingData + [rank.ratings.sum()])

    return createXlsxResponse(['category', 'rank', 'name', 'team', 'group'] + [d.name for d in disciplines] + ['rating'], [('', rows)], f'results_{alphaNum(event.name)}.xlsx', event.name)

@api.get('/ranking/{token}/{eventId}/{category}/{detail}', response_class=HTMLResponse)
async def ranking(eventId: int, token: str, category: str, detail: int):
    if r.get(token) is None:
        raise HTTPException(
            status_code=401,
            detail="unautohrized"
        )
    db = JuryDatabase('db')
    event = db.getEvent(eventId)
    disciplines = db.getEventDisciplines(eventId)
    data = []
    for rank in db.getEventCategoryRankings(eventId, category):
        athlete = rank.ratings.athlete
        ratingData = []
        if detail == 1:
            for discipline in disciplines:
                ratingData.append(rank.ratings.prettyOrDefault(discipline.name))
        user = db.getUser(athlete.userId)
        data.append([rank.ranking, athlete.name(), user.team] + ratingData + [rank.ratings.sum()])

    context = {
            "orientation": 'A4 portrait' if detail == 0 else 'A4 landscape',
            "title": f'Rankings for {event.descr()} / {category}',
            "headers": ['rank', 'name', 'team'] + ([d.name for d in disciplines] if detail == 1 else []) + ['rating'],
            "tables": [('', data)]
        }
    return createResponse('table.html', context, f'ranking_{category}.pdf')

@api.get('/ranking_xlsx/{token}/{eventId}/{category}')
async def ranking_xlsx(eventId: int, token: str, category: str):
    if r.get(token) is None:
        raise HTTPException(
            status_code=401,
            detail="unautohrized"
        )

    db = JuryDatabase('db')
    event = db.getEvent(eventId)
    disciplines = db.getEventDisciplines(eventId)

    output = BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = event.name

    ws.append(['category', 'rank', 'name', 'team', 'group'] + [d.name for d in disciplines] + ['rating'])

    categories = [c.name for c in db.getEventCategories(eventId)] if category == 'All' else [db.getEventCategory(eventId, category).name]
    for cat in categories:
        for rank in db.getEventCategoryRankings(eventId, cat):
            athlete = rank.ratings.athlete
            ratingData = []
            for discipline in disciplines:
                ratingData.append(rank.ratings.prettyOrDefault(discipline.name))
            user = db.getUser(athlete.userId)
            ws.append([cat, rank.ranking, athlete.name(), user.team, rank.ratings.group] + ratingData + [rank.ratings.sum()])

    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={event.name}_{category}.xlsx"
        },
    )


@api.get('/certificate/{token}/{eventId}/{category}', response_class=HTMLResponse)
async def certificate(token: str, eventId: int, category: str):
    if r.get(token) is None:
        raise HTTPException(
            status_code=401,
            detail="unautohrized"
        )

    db = JuryDatabase('db')
    event = db.getEvent(eventId)

    template = env.get_template('certificate.html')
    context = {
        "title": f'{event.name}',
        "event": event,
        "category": category,
        "rankingType": db.getEventCategory(eventId, category).rankingType,
        "rankings": db.getEventCategoryRankings(eventId, category)
    }
    rendered_html = template.render(context)
    pdf_file = HTML(string=rendered_html, base_url=".").write_pdf()
    filename = f'{alphaNum(event.name)}.pdf'
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return Response(pdf_file, headers=headers, media_type='application/pdf')


def get_bytes(image):
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='png')
    return img_byte_arr.getvalue()

def judge_login_url(user, target: str) -> str:
    return f"https://{os.environ['SUBDOMAIN_JURY'] + os.environ['DOMAIN']}/autoLogin/{user.username}/{user.token}/{target}"

@api.get('/qrcodes/login/{token}/{userId}/{target}', response_class=HTMLResponse)
async def qrCodesLogin(userId: int, token: str, target: str, request: Request) ->Response:
    if r.get(token) is None:
        raise HTTPException(
            status_code=401,
            detail="unautohrized"
        )
    db = JuryDatabase('db')
    user = db.getUser(userId)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="user not found"
        )
    img = qrcode.make(judge_login_url(user, target))
    filename = f'login_{alphaNum(user.username)}.png'
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return Response(get_bytes(img), headers=headers, media_type='application/png')

@api.get('/judgelogins/{token}/{eventId}/{target}', response_class=HTMLResponse)
async def qrCodesLoginAllJudges(eventId: int, token: str, target: str) ->Response:
    if r.get(token) is None:
        raise HTTPException(
            status_code=401,
            detail="unautohrized"
        )
    db = JuryDatabase('db')
    event = db.getEvent(eventId)
    judges = db.getEventJudges(eventId)
    if not judges:
        raise HTTPException(
            status_code=404,
            detail="no judges for this event"
        )
    targets = []
    for judge in judges:
        img = qrcode.make(judge_login_url(judge, target))
        targets.append((judge.username, base64.b64encode(get_bytes(img)).decode("utf-8")))

    template = env.get_template('qr_login.html')
    context = {
        "event": event,
        "targets": targets
    }
    rendered_html = template.render(context)
    pdf_file = HTML(string=rendered_html, base_url=".").write_pdf()
    filename = f'{alphaNum(event.name)}.pdf'
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return Response(pdf_file, headers=headers, media_type='application/pdf')
