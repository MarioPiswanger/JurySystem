"""Start number (bib) recognition: YOLO finds the bib, PaddleOCR reads the digits."""
import os
import re
import threading
from dataclasses import dataclass, asdict

import cv2
import numpy as np
from ultralytics import YOLO
from paddleocr import PaddleOCR

# custom bib model (single class "bib"); if missing we fall back to person detection
BIB_MODEL = os.getenv('BIB_MODEL', '/usr/src/app/models/custom/bib.pt')
PERSON_MODEL = os.getenv('PERSON_MODEL', '/usr/src/app/models/yolo11n.pt')
DET_CONF = float(os.getenv('DET_CONF', '0.35'))
OCR_MIN_SCORE = float(os.getenv('OCR_MIN_SCORE', '0.5'))
MIN_DIGITS = int(os.getenv('MIN_DIGITS', '1'))
MAX_DIGITS = int(os.getenv('MAX_DIGITS', '4'))
OCR_DET_MODEL = os.getenv('OCR_DET_MODEL', 'PP-OCRv5_mobile_det')
OCR_REC_MODEL = os.getenv('OCR_REC_MODEL', 'PP-OCRv5_mobile_rec')

PERSON_CLASS = 0  # COCO class id of "person"


@dataclass
class BibResult:
    number: str
    confidence: float      # OCR confidence of the chosen text line
    detConfidence: float   # YOLO confidence of the bib / person box
    box: list[int]         # [x1, y1, x2, y2] in original image coordinates
    rawText: list[str]     # all text lines read inside the box

    def toDict(self) -> dict:
        return asdict(self)


def createOcr() -> PaddleOCR:
    return PaddleOCR(
        text_detection_model_name=OCR_DET_MODEL,
        text_recognition_model_name=OCR_REC_MODEL,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


class BibRecognizer:
    def __init__(self):
        self.bibMode = os.path.isfile(BIB_MODEL)
        self.yolo = YOLO(BIB_MODEL if self.bibMode else PERSON_MODEL)
        self.ocr = createOcr()
        # paddle predictors are not thread safe
        self.lock = threading.Lock()

    @property
    def mode(self) -> str:
        return 'bib' if self.bibMode else 'person'

    def recognize(self, image: np.ndarray) -> list[BibResult]:
        with self.lock:
            boxes = self.detect(image)
            if not boxes:
                # no detection: try the whole image (e.g. close-up photo of a bib)
                h, w = image.shape[:2]
                boxes = [([0, 0, w, h], 0.0)]
            results = []
            for box, detConf in boxes:
                crop = self.cropRegion(image, box)
                if crop.size == 0:
                    continue
                found = self.readNumber(crop)
                if found is not None:
                    number, score, lines = found
                    results.append(BibResult(number, round(score, 3), round(detConf, 3), box, lines))
        return dedupe(results)

    def detect(self, image: np.ndarray) -> list[tuple[list[int], float]]:
        classes = None if self.bibMode else [PERSON_CLASS]
        prediction = self.yolo.predict(image, conf=DET_CONF, classes=classes, verbose=False)[0]
        xyxy = prediction.boxes.xyxy.cpu().numpy().astype(int).tolist()
        conf = prediction.boxes.conf.cpu().numpy().tolist()
        return list(zip(xyxy, conf))

    def cropRegion(self, image: np.ndarray, box: list[int]) -> np.ndarray:
        h, w = image.shape[:2]
        x1, y1, x2, y2 = box
        if self.bibMode:
            # small margin so digits at the border are not cut off
            padX, padY = int((x2 - x1) * 0.08), int((y2 - y1) * 0.08)
            x1, y1, x2, y2 = x1 - padX, y1 - padY, x2 + padX, y2 + padY
        elif (y2 - y1) > 0:
            # bibs are worn on the torso: skip head and legs
            height = y2 - y1
            y1, y2 = y1 + int(height * 0.15), y1 + int(height * 0.70)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        crop = image[y1:y2, x1:x2]
        # OCR works poorly on tiny crops
        if crop.size and crop.shape[0] < 64:
            scale = 64 / crop.shape[0]
            crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        return crop

    def readNumber(self, crop: np.ndarray) -> tuple[str, float, list[str]] | None:
        res = self.ocr.predict(crop)[0]
        texts, scores, polys = res['rec_texts'], res['rec_scores'], res['rec_polys']
        best, bestRank = None, 0.0
        for text, score, poly in zip(texts, scores, polys):
            digits = re.sub(r'\D', '', text)
            if not (MIN_DIGITS <= len(digits) <= MAX_DIGITS) or score < OCR_MIN_SCORE:
                continue
            # the start number is usually the biggest text on the bib
            height = float(np.ptp(np.asarray(poly)[:, 1]))
            rank = score * height
            if rank > bestRank:
                best, bestRank = (digits, float(score)), rank
        if best is None:
            return None
        return best[0], best[1], list(texts)


def dedupe(results: list[BibResult]) -> list[BibResult]:
    """Keep only the most confident result per number."""
    byNumber: dict[str, BibResult] = {}
    for r in results:
        if r.number not in byNumber or r.confidence > byNumber[r.number].confidence:
            byNumber[r.number] = r
    return sorted(byNumber.values(), key=lambda r: r.box[0])


def annotate(image: np.ndarray, results: list[BibResult]) -> np.ndarray:
    out = image.copy()
    for r in results:
        x1, y1, x2, y2 = r.box
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 200, 0), 3)
        label = f'{r.number} ({r.confidence:.2f})'
        cv2.putText(out, label, (x1, max(25, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 0), 2)
    return out
