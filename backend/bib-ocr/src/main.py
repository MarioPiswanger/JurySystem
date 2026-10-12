import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from recognizer import BibRecognizer, annotate

MAX_UPLOAD_BYTES = 15 * 1024 * 1024

recognizer: BibRecognizer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global recognizer
    # loading YOLO + PaddleOCR takes a few seconds, do it once at startup
    recognizer = await run_in_threadpool(BibRecognizer)
    yield


api = FastAPI(title='Bib OCR', lifespan=lifespan)


async def decodeImage(image: UploadFile) -> np.ndarray:
    data = await image.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail='image too large')
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail='invalid image')
    return img


@api.get('/health')
async def health():
    return {'status': 'ok', 'mode': recognizer.mode if recognizer else 'loading'}


@api.post('/detect')
async def detect(image: UploadFile = File(...)):
    img = await decodeImage(image)
    start = time.perf_counter()
    results = await run_in_threadpool(recognizer.recognize, img)
    return {
        'mode': recognizer.mode,
        'timeMs': round((time.perf_counter() - start) * 1000),
        'numbers': [r.toDict() for r in results],
    }


@api.post('/detect/annotated')
async def detectAnnotated(image: UploadFile = File(...)):
    img = await decodeImage(image)
    results = await run_in_threadpool(recognizer.recognize, img)
    ok, jpg = cv2.imencode('.jpg', annotate(img, results))
    if not ok:
        raise HTTPException(status_code=500, detail='encoding failed')
    numbers = ','.join(r.number for r in results)
    return Response(jpg.tobytes(), media_type='image/jpeg', headers={'X-Bib-Numbers': numbers})
