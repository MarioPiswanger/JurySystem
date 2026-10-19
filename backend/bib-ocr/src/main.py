import os
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response

from recognizer import BibRecognizer, annotate

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
INDEX_HTML = os.path.join(os.path.dirname(__file__), 'static', 'index.html')

recognizer: BibRecognizer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global recognizer
    # loading YOLO + PaddleOCR takes a few seconds, do it once at startup
    recognizer = await run_in_threadpool(BibRecognizer)
    yield


api = FastAPI(
    title='Startnummern-Erkennung',
    description='Erkennt Startnummern auf Fotos: YOLO findet die Startnummer bzw. den Läufer, '
                'PaddleOCR liest die Ziffern. Zum Ausprobieren gibt es eine Upload-Seite unter `/`.',
    lifespan=lifespan,
)

IMAGE_FIELD = File(..., description='Foto als JPEG oder PNG (max. 15 MB)')


async def decodeImage(image: UploadFile) -> np.ndarray:
    data = await image.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail='Bild ist zu groß (max. 15 MB)')
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail='Datei ist kein gültiges Bild')
    return img


@api.get('/', include_in_schema=False)
async def index():
    return FileResponse(INDEX_HTML)


@api.get('/health', summary='Status', description='Ob der Dienst bereit ist und welcher Modus (`bib` / `person`) läuft.')
async def health():
    return {'status': 'ok', 'mode': recognizer.mode if recognizer else 'loading'}


@api.post('/detect', summary='Startnummern erkennen',
          description='Liefert alle erkannten Startnummern mit Sicherheit und Position im Bild als JSON.')
async def detect(image: UploadFile = IMAGE_FIELD):
    img = await decodeImage(image)
    start = time.perf_counter()
    results = await run_in_threadpool(recognizer.recognize, img)
    return {
        'mode': recognizer.mode,
        'timeMs': round((time.perf_counter() - start) * 1000),
        'numbers': [r.toDict() for r in results],
    }


@api.post('/detect/annotated', summary='Startnummern im Bild markieren',
          description='Liefert das Foto als JPEG mit eingezeichneten Boxen. '
                      'Die erkannten Nummern stehen im Header `X-Bib-Numbers`.',
          response_class=Response,
          responses={200: {'content': {'image/jpeg': {}}, 'description': 'Foto mit markierten Startnummern'}})
async def detectAnnotated(image: UploadFile = IMAGE_FIELD):
    img = await decodeImage(image)
    results = await run_in_threadpool(recognizer.recognize, img)
    ok, jpg = cv2.imencode('.jpg', annotate(img, results))
    if not ok:
        raise HTTPException(status_code=500, detail='Bild konnte nicht erstellt werden')
    numbers = ','.join(r.number for r in results)
    return Response(jpg.tobytes(), media_type='image/jpeg', headers={'X-Bib-Numbers': numbers})
