# bib-ocr – Startnummern-Erkennung

FastAPI-Dienst, der Startnummern auf Fotos erkennt.

1. **YOLO** (ultralytics) findet die Startnummer im Bild
   - `models/bib.pt` vorhanden → eigenes Bib-Modell (1 Klasse `bib`)
   - sonst → vortrainiertes `yolo11n.pt`, erkennt Personen und schneidet den Oberkörper aus
   - nichts gefunden → das ganze Bild wird gelesen (Nahaufnahme einer Startnummer)
2. **PaddleOCR** (PP-OCRv5 mobile) liest den Text im Ausschnitt; behalten wird die größte
   reine Ziffernfolge (`MIN_DIGITS`..`MAX_DIGITS`), Sponsor-Text wird ignoriert.

## API

| Methode | Pfad                 | Beschreibung                                           |
| ------- | -------------------- | ------------------------------------------------------ |
| GET     | `/`                  | Upload-Seite zum Ausprobieren (deutsch)                |
| GET     | `/health`            | Status und Modus (`bib` / `person`)                    |
| POST    | `/detect`            | Multipart-Feld `image` → JSON mit erkannten Nummern    |
| POST    | `/detect/annotated`  | wie oben, liefert JPEG mit Boxen, Nummern im Header `X-Bib-Numbers` |

```shell
curl -F "image=@foto.jpg" https://bib.localhost/detect
```
```json
{"mode": "person", "timeMs": 337,
 "numbers": [{"number": "137", "confidence": 1.0, "detConfidence": 0.91,
              "box": [250, 180, 550, 420], "rawText": ["SPORTUNION", "137"]}]}
```

## Konfiguration (Umgebungsvariablen)

| Variable        | Default                              |
| --------------- | ------------------------------------ |
| `BIB_MODEL`     | `/usr/src/app/models/custom/bib.pt`  |
| `PERSON_MODEL`  | `/usr/src/app/models/yolo11n.pt`     |
| `DET_CONF`      | `0.35`                               |
| `OCR_MIN_SCORE` | `0.5`                                |
| `MIN_DIGITS` / `MAX_DIGITS` | `1` / `4`                |

## Tests

```shell
python -m pytest tests/bib_ocr_test.py -v
```

- Die Regeln zur Auswahl der Nummer (`src/bibrules.py`) werden ohne YOLO/Paddle getestet.
- Läuft der Dienst (`BIB_OCR_URL`, Default `https://bib.localhost`), wird jedes Foto in
  `tests/data/bib/` an `/detect` geschickt. Der Dateiname ist die erwartete Nummer,
  z. B. `1587.png` oder `1587_lagos.jpg`. Neue Testfotos einfach dort ablegen.

## Eigenes Bib-Modell trainieren

Der Personen-Fallback funktioniert ohne Training, ein eigenes Modell ist aber genauer
(mehrere Athleten, Nummern am Rücken, kleine Nummern). Bilder mit z. B. Roboflow oder
CVAT als YOLO-Datensatz mit einer Klasse `bib` annotieren, dann:

```shell
yolo detect train data=bibs/data.yaml model=yolo11n.pt epochs=100 imgsz=640
cp runs/detect/train/weights/best.pt backend/bib-ocr/models/bib.pt
```

Der Ordner `models/` wird in den Container gemountet, nach einem Neustart läuft der Dienst
im Modus `bib`.
