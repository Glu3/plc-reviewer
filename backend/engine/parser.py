# backend/engine/parser.py
from lxml import etree
from dataclasses import dataclass, asdict

@dataclass
class Rung:
    number:  int
    text:    str    # the instruction text from CDATA

def parse_routine_from_file(file_path: str) -> tuple[str, list[Rung]]:
    """
    Parse a .L5X file that contains a single Routine element.
    Returns the routine name and list of rungs.
    """
    with open(file_path, "rb") as f:
        content = f.read()

    return parse_routine_from_bytes(content)


def parse_routine_from_bytes(content: bytes) -> tuple[str, list[Rung]]:
    """
    Parse a .L5X file from raw bytes.
    Returns the routine name and list of rungs.
    """
    tree = etree.fromstring(content)

    # Handle both cases:
    # 1. Root element IS the Routine
    # 2. Routine is nested inside RSLogix5000Content
    if tree.tag == "Routine":
        routine_el = tree
    else:
        routine_el = tree.find(".//Routine")

    if routine_el is None:
        raise ValueError("No Routine element found in file")

    routine_name = routine_el.get("Name", "Unknown")
    rungs = []

    for index, rung_el in enumerate(routine_el.findall(".//Rung")):
        text_el = rung_el.find("Text")
        text    = (text_el.text or "").strip() if text_el is not None else ""
        rungs.append(Rung(number=index + 1, text=text))

    return routine_name, rungs


def rungs_to_dict(rungs: list[Rung]) -> list[dict]:
    """Convert rung objects to plain dicts for JSON storage."""
    return [asdict(r) for r in rungs]