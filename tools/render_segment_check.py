from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PEOPLE_PATH = ROOT / "people.json"
OUTPUT_PATH = ROOT / "segment_check_site_only.jpg"
THUMBNAIL_SIZE = (180, 240)
LABEL_HEIGHT = 34
COLS = 6
LINES = (
    ("brow", "#e53e3e"),
    ("eyes", "#3182ce"),
    ("nose", "#38a169"),
)


def load_font() -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 14)
    except OSError:
        return ImageFont.load_default()


def main() -> None:
    people = json.loads(PEOPLE_PATH.read_text(encoding="utf-8"))
    rows = (len(people) + COLS - 1) // COLS
    thumb_width, thumb_height = THUMBNAIL_SIZE
    canvas = Image.new("RGB", (COLS * thumb_width, rows * (thumb_height + LABEL_HEIGHT)), "white")
    draw = ImageDraw.Draw(canvas)
    font = load_font()

    for index, person in enumerate(people):
        left = index % COLS * thumb_width
        top = index // COLS * (thumb_height + LABEL_HEIGHT)
        image = Image.open(ROOT / person["image"]).convert("RGB").resize(THUMBNAIL_SIZE)
        canvas.paste(image, (left, top))

        for key, color in LINES:
            y = top + round(person["segments"][key][1] * thumb_height)
            draw.line((left, y, left + thumb_width, y), fill=color, width=2)

        draw.text((left + 4, top + thumb_height + 6), person["name"], fill="black", font=font)

    canvas.save(OUTPUT_PATH, quality=92)
    print(f"saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
