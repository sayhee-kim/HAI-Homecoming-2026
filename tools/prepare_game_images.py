from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PEOPLE_PATH = ROOT / "people.json"
OUTPUT_DIR = ROOT / "assets" / "processed"
TARGET = (450, 600)
MANUAL_CUTS = {
    "assets/people/001-윤병동.jpg": (0.235, 0.305, 0.415),
    "assets/people/003-채민석.jpg": (None, None, 0.477),
    "assets/people/005-유진오.jpg": (None, None, 0.486),
    "assets/people/006-김태형.jpg": (None, None, 0.495),
    "assets/people/008-이상경.jpg": (None, None, 0.508),
    "assets/people/009-김용채.jpg": (0.268, 0.338, 0.443),
    "assets/people/010-김민재.jpg": (None, None, 0.453),
    "assets/people/014-김주현.jpg": (None, None, 0.466),
    "assets/people/015-이정환.jpg": (0.258, 0.333, 0.418),
    "assets/people/017-김민태.jpg": (0.318, None, 0.493),
    "assets/people/019-이용민.jpg": (None, None, 0.44),
    "assets/people/020-박승영.jpg": (None, None, 0.463),
    "assets/people/022-한주환.jpg": (None, None, 0.467),
    "assets/people/023-주나라.jpg": (0.292, 0.362, 0.452),
    "assets/people/024-임우리.jpg": (0.3, 0.37, 0.455),
    "assets/people/025-김세희.jpg": (0.31, 0.383, 0.488),
    "assets/people/030-정의일.jpg": (0.303, 0.373, 0.478),
    "assets/people/031-이찬.jpg": (None, None, 0.498),
    "assets/people/033-김형민.png": (None, None, 0.488),
    "assets/people/034-김수지.png": (None, None, 0.469),
    "assets/people/040-하종문.gif": (0.35, 0.42, 0.53),
    "assets/people/042-윤명백.jpg": (None, None, 0.524),
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def detect_face(image: Image.Image) -> tuple[int, int, int, int] | None:
    cv_image = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(cv_image, scaleFactor=1.08, minNeighbors=4, minSize=(45, 45))
    if len(faces) == 0:
        return None
    return max((tuple(map(int, face)) for face in faces), key=lambda item: item[2] * item[3])


def detect_eye_center(image: Image.Image, face: tuple[int, int, int, int] | None) -> float | None:
    if face is None:
        return None

    gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    x, y, w, h = face
    roi = gray[y : y + round(h * 0.58), x : x + w]
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    eyes = cascade.detectMultiScale(
        roi,
        scaleFactor=1.06,
        minNeighbors=5,
        minSize=(22, 14),
        maxSize=(90, 60),
    )
    if len(eyes) < 2:
        return None

    centers = sorted(
        [(x + ex + ew / 2, y + ey + eh / 2) for ex, ey, ew, eh in eyes],
        key=lambda item: item[0],
    )
    best_pair: tuple[tuple[float, float], tuple[float, float]] | None = None
    best_score = float("inf")
    for left_index, left in enumerate(centers):
        for right in centers[left_index + 1 :]:
            horizontal_gap = right[0] - left[0]
            vertical_gap = abs(right[1] - left[1])
            if horizontal_gap < w * 0.18 or horizontal_gap > w * 0.7:
                continue
            score = vertical_gap + abs(horizontal_gap - w * 0.36) * 0.2
            if score < best_score:
                best_score = score
                best_pair = (left, right)
    if best_pair is None:
        return None

    return (best_pair[0][1] + best_pair[1][1]) / 2 / image.height


def crop_to_portrait(image: Image.Image, face: tuple[int, int, int, int] | None) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    target_ratio = TARGET[0] / TARGET[1]

    cx = width / 2
    cy = height * 0.5
    if width / height > target_ratio:
        crop_h = height
        crop_w = round(crop_h * target_ratio)
    else:
        crop_w = width
        crop_h = round(crop_w / target_ratio)

    left = round(cx - crop_w / 2)
    top = round(cy - crop_h / 2)
    left = max(0, min(width - crop_w, left))
    top = max(0, min(height - crop_h, top))

    cropped = image.crop((left, top, left + crop_w, top + crop_h))
    resized = cropped.resize(TARGET, Image.Resampling.LANCZOS)
    corrected = ImageOps.autocontrast(resized, cutoff=0.5)
    corrected = ImageEnhance.Contrast(corrected).enhance(1.06)
    corrected = ImageEnhance.Color(corrected).enhance(1.04)
    corrected = corrected.filter(ImageFilter.UnsharpMask(radius=1.15, percent=115, threshold=3))
    return corrected


def cuts_from_face(processed: Image.Image) -> dict[str, list[float]]:
    # Homepage photos are low-resolution thumbnails, so full landmark detection is unreliable.
    # This uses the detected face box as the main anchor and the eye pair when it is stable.
    face = detect_face(processed)
    if face is None:
        brow_top, eye_top, nose_top, mouth_top, mouth_bottom = 0.18, 0.285, 0.39, 0.57, 0.82
    else:
        _, y, _, h = face
        face_top = y / processed.height
        face_h = h / processed.height
        eye_center = detect_eye_center(processed, face)
        if eye_center is None:
            eye_center = face_top + face_h * 0.41

        brow_top = eye_center - face_h * 0.2
        eye_top = eye_center - face_h * 0.08
        nose_top = eye_center + face_h * 0.095
        mouth_top = eye_center + face_h * 0.285
        mouth_bottom = eye_center + face_h * 0.515

        brow_top = clamp(brow_top, 0.12, 0.35)
        eye_top = clamp(eye_top, brow_top + 0.06, 0.45)
        nose_top = clamp(nose_top, eye_top + 0.07, 0.58)
        mouth_top = clamp(mouth_top, nose_top + 0.11, 0.72)
        mouth_bottom = clamp(mouth_bottom, mouth_top + 0.12, 0.92)

    return {
        "brow": [0.0, round(eye_top, 3)],
        "eyes": [round(eye_top, 3), round(nose_top, 3)],
        "nose": [round(nose_top, 3), round(mouth_top, 3)],
        "mouth": [round(mouth_top, 3), 1.0],
    }


def apply_manual_cuts(person: dict[str, str], cuts: dict[str, list[float]]) -> dict[str, list[float]]:
    manual = MANUAL_CUTS.get(person.get("rawImage", ""))
    if manual is None:
        return cuts

    eye_top, nose_top, mouth_top = manual
    if eye_top is not None:
        cuts["brow"][1] = eye_top
        cuts["eyes"][0] = eye_top
    if nose_top is not None:
        cuts["eyes"][1] = nose_top
        cuts["nose"][0] = nose_top
    if mouth_top is not None:
        cuts["nose"][1] = mouth_top
        cuts["mouth"][0] = mouth_top
    cuts["mouth"][1] = 1.0
    return cuts


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    people = json.loads(PEOPLE_PATH.read_text(encoding="utf-8"))

    for index, person in enumerate(people, start=1):
        source = ROOT / person["rawImage"] if person.get("rawImage") else ROOT / person["image"]
        image = Image.open(source)
        face = detect_face(image)
        processed = crop_to_portrait(image, face)
        output = OUTPUT_DIR / f"{index:03d}-{re.sub(r'[^0-9A-Za-z가-힣]+', '-', person['name']).strip('-')}.jpg"
        processed.save(output, quality=94, optimize=True)

        person["image"] = output.relative_to(ROOT).as_posix()
        person["segments"] = apply_manual_cuts(person, cuts_from_face(processed))
        person["sourceQuality"] = "site-thumb-upscaled"

    PEOPLE_PATH.write_text(json.dumps(people, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"processed={len(people)}")
    print(f"output={OUTPUT_DIR}")


if __name__ == "__main__":
    main()
