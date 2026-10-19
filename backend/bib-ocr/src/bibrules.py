"""Pure rules for choosing the start number, kept free of OCR/YOLO imports so they can be unit tested."""
import re


def torsoRange(y1: int, y2: int, imageHeight: int) -> tuple[int, int]:
    """Vertical range of a person box where the bib is worn (skip head and legs)."""
    height = y2 - y1
    # person cut off by the bottom edge: the bib sits lower in the box, keep it all
    bottom = y2 if y2 >= imageHeight - 2 else y1 + int(height * 0.70)
    return y1 + int(height * 0.15), bottom


def pickNumber(texts, scores, polys, minDigits: int, maxDigits: int,
               minScore: float) -> tuple[str, float] | None:
    """Choose the start number among the OCR text lines, or None."""
    best, bestRank = None, 0.0
    for text, score, poly in zip(texts, scores, polys):
        digits = re.sub(r'\D', '', text)
        if not (minDigits <= len(digits) <= maxDigits) or score < minScore:
            continue
        # skip mixed lines like "10km RUN": the bib number is (almost) only digits
        letters = len(re.sub(r'[\W\d_]', '', text))
        if letters > len(digits) / 3:
            continue
        # the start number is usually the biggest text on the bib
        ys = [point[1] for point in poly]
        rank = score * float(max(ys) - min(ys))
        if rank > bestRank:
            best, bestRank = (digits, float(score)), rank
    return best
