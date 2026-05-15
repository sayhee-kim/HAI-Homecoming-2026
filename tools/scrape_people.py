from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets" / "people"
DATA_PATH = ROOT / "people.json"
BASE = "https://hai.snu.ac.kr"
USER_AGENT = "Mozilla/5.0"
NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def norm_name(value: str) -> str:
    return re.sub(r"[\s._·\-()]+", "", unicodedata.normalize("NFKC", value).lower())


def fetch_html(url: str) -> BeautifulSoup:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    html = urlopen(request, timeout=25).read().decode("utf-8", "replace")
    return BeautifulSoup(html, "html.parser")


def download(url: str, path: Path) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    request = Request(url, headers={"User-Agent": USER_AGENT})
    path.write_bytes(urlopen(request, timeout=30).read())


def safe_filename(name: str, index: int, suffix: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", name).strip("-")
    return f"{index:03d}-{slug or 'person'}{suffix}"


def extract_people_from_list(table: str) -> list[dict[str, str]]:
    people: list[dict[str, str]] = []
    seen_pages: set[str] = set()
    pages = [f"{BASE}/bbs/board.php?bo_table={table}"]

    while pages:
        url = pages.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        soup = fetch_html(url)

        for link in soup.find_all("a", href=True):
            href = urljoin(url, link["href"])
            if f"bo_table={table}" in href and "page=" in href and href not in seen_pages:
                pages.append(href)

        for item in soup.select("li"):
            image = item.select_one(".img img")
            if not image or not image.get("src"):
                continue
            text = item.get_text(" ", strip=True)
            match = re.search(r"View Publications\s+(.+?)\s*\((.+?)\)\s*(.+?)\s+Research field", text)
            if not match:
                continue

            english_name = re.sub(r"\s+", " ", match.group(1)).strip()
            korean_name = re.sub(r"\s+", " ", match.group(2)).strip()
            role = re.sub(r"^\d+", "", match.group(3)).strip()
            if korean_name.lower() in {"visiting student", "ph.d. student", "m.s. student"}:
                korean_name = english_name
            role = re.split(r"\s+(Doctoral Dissertation|Master's Thesis|Research field)\s+", role)[0].strip()
            people.append(
                {
                    "name": korean_name,
                    "englishName": english_name,
                    "role": role or ("Alumni" if table == "sub2_3" else "Member"),
                    "group": "alumni" if table == "sub2_3" else "current",
                    "imageUrl": urljoin(BASE, image["src"]),
                }
            )
    return people


def extract_professor() -> dict[str, str]:
    soup = fetch_html(f"{BASE}/bbs/board.php?bo_table=sub2_1")
    image = soup.find("img", src=re.compile(r"professor", re.I))
    return {
        "name": "윤병동",
        "englishName": "Byeng D. Youn",
        "role": "Professor",
        "group": "professor",
        "imageUrl": urljoin(BASE, image["src"] if image else "/images/sub/professor.jpg"),
    }


def read_shared_strings(zip_file: ZipFile) -> list[str]:
    root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in item.findall(".//a:t", NS)) for item in root.findall("a:si", NS)]


def read_cell(cell: ET.Element, shared: list[str]) -> str:
    value = cell.find("a:v", NS)
    text = "" if value is None else value.text or ""
    if cell.attrib.get("t") == "s" and text:
        text = shared[int(text)]
    return text.strip()


def participant_names_from_xlsx(path: Path) -> set[str]:
    with ZipFile(path) as zip_file:
        shared = read_shared_strings(zip_file)
        sheet = ET.fromstring(zip_file.read("xl/worksheets/sheet1.xml"))

    rows: list[list[str]] = []
    for row in sheet.findall(".//a:sheetData/a:row", NS):
        cells: dict[int, str] = {}
        for cell in row.findall("a:c", NS):
            column = re.sub(r"\d+", "", cell.attrib.get("r", ""))
            number = 0
            for char in column:
                number = number * 26 + ord(char) - 64
            cells[number - 1] = read_cell(cell, shared)
        if cells:
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)])

    names: set[str] = set()
    for row in rows:
        # Homecoming sheet layout:
        # B/C = current members name/attendance, H/I = alumni name/attendance.
        for name_index, status_index in ((1, 2), (7, 8)):
            name = row[name_index].strip() if len(row) > name_index else ""
            status = row[status_index].strip().lower() if len(row) > status_index else ""
            if name and status in {"o", "○", "yes", "y"}:
                names.add(name)
    return {norm_name(name) for name in names}


def find_participant_filter() -> set[str] | None:
    candidates = sorted([*ROOT.glob("*.xlsx"), *(ROOT / "input").glob("*.xlsx")], key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    return participant_names_from_xlsx(candidates[0])


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    people = [extract_professor()]
    people.extend(extract_people_from_list("sub2_2"))
    people.extend(extract_people_from_list("sub2_3"))

    filters = find_participant_filter()
    if filters:
        people = [
            person
            for person in people
            if norm_name(person["name"]) in filters or norm_name(person["englishName"]) in filters
        ]

    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for person in people:
        key = norm_name(person["name"]) or norm_name(person["englishName"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(person)

    for index, person in enumerate(deduped, start=1):
        suffix = Path(person["imageUrl"].split("?")[0]).suffix or ".jpg"
        filename = safe_filename(person["name"] or person["englishName"], index, suffix)
        path = ASSET_DIR / filename
        download(person["imageUrl"], path)
        person["image"] = path.relative_to(ROOT).as_posix()
        person.pop("imageUrl", None)

    DATA_PATH.write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"people={len(deduped)}")
    print(f"output={DATA_PATH}")
    if filters:
        print("filtered_by=input/*.xlsx")
    else:
        print("no participant xlsx found; used all professor/current/alumni records")


if __name__ == "__main__":
    main()
