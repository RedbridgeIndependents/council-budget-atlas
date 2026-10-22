"""Small, dependency-free readers for the published ODS and XLSX tables."""

from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def ods(path):
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    sheets = {}
    for table in root.iter(TABLE + "table"):
        rows = []
        for row in table.findall(TABLE + "table-row"):
            cells = []
            for cell in row:
                if cell.tag not in (TABLE + "table-cell", TABLE + "covered-table-cell"):
                    continue
                text = " ".join("".join(p.itertext()) for p in cell.iter(TEXT + "p"))
                value = cell.get(OFFICE + "value")
                if value is not None:
                    number = float(value)
                    value = int(number) if number.is_integer() else number
                else:
                    value = text.strip()
                repeat = int(cell.get(TABLE + "number-columns-repeated", "1"))
                cells.extend([value] * min(repeat, max(0, 600 - len(cells))))
            while cells and cells[-1] == "":
                cells.pop()
            repeat = int(row.get(TABLE + "number-rows-repeated", "1"))
            if cells:
                rows.extend([cells] * min(repeat, 1000))
            else:
                rows.append([])
        sheets[table.get(TABLE + "name")] = rows
    return sheets


def xlsx(path):
    with ZipFile(path) as archive:
        strings = [
            "".join(item.itertext())
            for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall(X + "si")
        ]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in relations}
        result = {}
        for sheet in workbook.find(X + "sheets"):
            rid = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = targets[rid]
            target = target.lstrip("/") if target.startswith("/") else "xl/" + target
            root = ET.fromstring(archive.read(target))
            rows = []
            for row in root.iter(X + "row"):
                row_number = int(row.get("r"))
                rows.extend([[]] * (row_number - len(rows) - 1))
                cells = []
                for cell in row:
                    letters = re.match(r"[A-Z]+", cell.get("r")).group()
                    column = 0
                    for letter in letters:
                        column = column * 26 + ord(letter) - 64
                    cells.extend([""] * (column - len(cells)))
                    value = cell.find(X + "v")
                    if value is None:
                        inline = cell.find(X + "is")
                        value = "".join(inline.itertext()) if inline is not None else ""
                    elif cell.get("t") == "s":
                        value = strings[int(value.text)]
                    else:
                        number = float(value.text)
                        value = int(number) if number.is_integer() else number
                    cells[column - 1] = value
                rows.append(cells)
            result[sheet.get("name")] = rows
        return result


if __name__ == "__main__":
    import sys

    path = Path(sys.argv[1])
    data = ods(path) if path.suffix == ".ods" else xlsx(path)
    if len(sys.argv) == 2:
        print([(name, len(rows)) for name, rows in data.items()])
    else:
        for index, row in enumerate(data[sys.argv[2]]):
            if len(sys.argv) < 4 or sys.argv[3].lower() in str(row).lower():
                print(index + 1, row)
