import json
import os
import ssl
import sys
import unittest
import uuid
import urllib.error
import urllib.parse
import urllib.request

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend", "bib-ocr", "src"))

from bibrules import pickNumber, torsoRange

# photos named after the expected start number, e.g. "1587.png" or "1587_lagos.jpg"
IMAGE_DIR = os.path.join(os.path.dirname(__file__), "data", "bib")
BIB_OCR_URL = os.getenv("BIB_OCR_URL", "https://bib.localhost")


def box(top: int, bottom: int) -> list[list[int]]:
    return [[0, top], [100, top], [100, bottom], [0, bottom]]


class TestPickNumber(unittest.TestCase):
    def pick(self, texts, scores, polys):
        return pickNumber(texts, scores, polys, minDigits=1, maxDigits=4, minScore=0.5)

    def test_ignores_mixed_text_line(self):
        # "10km RUN" contains digits but is no start number
        result = self.pick(["10kmRUN", "1587"], [0.99, 0.95], [box(0, 40), box(50, 90)])
        self.assertEqual(result[0], "1587")

    def test_prefers_biggest_number(self):
        result = self.pick(["2026", "1587"], [0.99, 0.98], [box(0, 10), box(20, 80)])
        self.assertEqual(result[0], "1587")

    def test_rejects_low_score(self):
        self.assertIsNone(self.pick(["1587"], [0.3], [box(0, 50)]))

    def test_rejects_too_many_digits(self):
        self.assertIsNone(self.pick(["123456"], [0.99], [box(0, 50)]))

    def test_strips_separators(self):
        self.assertEqual(self.pick(["15-87"], [0.9], [box(0, 50)])[0], "1587")

    def test_nothing_found(self):
        self.assertIsNone(self.pick(["SPORTUNION"], [0.99], [box(0, 50)]))


class TestTorsoRange(unittest.TestCase):
    def test_full_person_skips_head_and_legs(self):
        self.assertEqual(torsoRange(0, 1000, imageHeight=1200), (150, 700))

    def test_person_cut_off_at_bottom_keeps_lower_part(self):
        # runner photo: person box ends at the image border, the bib is near the bottom
        self.assertEqual(torsoRange(150, 678, imageHeight=678), (229, 678))


def openUrl(path: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 60):
    url = urllib.parse.urlsplit(BIB_OCR_URL)
    headers = dict(headers or {})
    netloc = url.netloc
    # Windows does not resolve *.localhost (curl and browsers do): go to 127.0.0.1, traefik routes by Host
    if url.hostname.endswith(".localhost"):
        headers["Host"] = url.netloc
        netloc = "127.0.0.1" + (f":{url.port}" if url.port else "")
    request = urllib.request.Request(f"{url.scheme}://{netloc}{path}", data=data, headers=headers)
    # local traefik uses a self-signed certificate
    return urllib.request.urlopen(request, timeout=timeout, context=ssl._create_unverified_context())


def postImage(path: str) -> dict:
    boundary = uuid.uuid4().hex
    with open(path, "rb") as f:
        data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{os.path.basename(path)}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    with openUrl("/detect", body, headers) as response:
        return json.load(response)


def serviceReachable() -> bool:
    try:
        with openUrl("/health", timeout=5) as response:
            return json.load(response).get("status") == "ok"
    except (urllib.error.URLError, OSError, ValueError):
        return False


@unittest.skipUnless(serviceReachable(), f"bib-ocr service not reachable at {BIB_OCR_URL}")
class TestBibOcrService(unittest.TestCase):
    def test_recognizes_sample_images(self):
        images = sorted(f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png")))
        self.assertTrue(images, f"no sample images in {IMAGE_DIR}")
        for name in images:
            expected = name.split("_")[0].split(".")[0]
            with self.subTest(image=name):
                numbers = [n["number"] for n in postImage(os.path.join(IMAGE_DIR, name))["numbers"]]
                self.assertIn(expected, numbers)


if __name__ == "__main__":
    unittest.main()
