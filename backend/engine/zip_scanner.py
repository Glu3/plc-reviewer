# backend/engine/zip_scanner.py
import zipfile
import re
from io import BytesIO
from lxml import etree
from dataclasses import dataclass, field

@dataclass
class ScannedRoutine:
    routine_name: str
    routine_type: str
    rungs:        list[dict]   

@dataclass
class ScannedProgram:
    program_name:     str
    unit:             str
    program_type:     str
    number:           str
    description_name: str
    has_prestate:     bool
    prestate_rungs:   list[dict]   # kept for backward compatibility
    tags:             list[dict]
    routines:         list[ScannedRoutine] = field(default_factory=list)


@dataclass
class ScannedProject:
    name:     str
    programs: list[ScannedProgram] = field(default_factory=list)

 


def parse_program_name(name: str) -> dict:
    """
    Parse DS3_AI1_PH1101Agit into components.
    Pattern: {Project}_{Unit}_{Type}{Number}{Description}
    """
    parts = name.split("_")

    if len(parts) < 3:
        return {
            "unit": "",
            "program_type": "",
            "number": "",
            "description_name": name,
        }

    unit = parts[1] if len(parts) > 1 else ""

    # Third segment contains type + number + description
    # e.g. PH1101Agit → type=PH, number=1101, description=Agit
    type_segment = "_".join(parts[2:])
    match = re.match(r'^(PH|OP|UP|CM)(\d+)(.*)', type_segment)

    if match:
        return {
            "unit":             unit,
            "program_type":     match.group(1),
            "number":           match.group(2),
            "description_name": match.group(3),
        }

    return {
        "unit":             unit,
        "program_type":     "",
        "number":           "",
        "description_name": type_segment,
    }


def extract_routine_from_xml(xml_bytes: bytes) -> tuple[str, str, list[dict]]:
    """
    Extract routine name, type and rungs from a routine XML file.
    Returns (routine_name, routine_type, rungs).
    """
    try:
        tree = etree.fromstring(xml_bytes)

        if tree.tag == "Routine":
            routine_el = tree
        else:
            routine_el = tree.find(".//Routine")

        if routine_el is None:
            return ("Unknown", "RLL", [])

        routine_name = routine_el.get("Name", "Unknown")
        routine_type = routine_el.get("Type", "RLL")

        rungs = []
        for index, rung_el in enumerate(routine_el.findall(".//Rung")):
            text_el = rung_el.find("Text")
            text = (text_el.text or "").strip() if text_el is not None else ""
            rungs.append({"number": index + 1, "text": text})

        return (routine_name, routine_type, rungs)

    except Exception:
        return ("Unknown", "RLL", [])


def extract_tag_from_xml(xml_bytes: bytes) -> dict | None:
    """Extract tag name and value from a tag XML file."""
    try:
        tree = etree.fromstring(xml_bytes)

        if tree.tag != "Tag":
            return None

        name      = tree.get("Name", "")
        data_type = tree.get("DataType", "")
        tag_type  = tree.get("TagType", "Base")

        # Skip alias tags — they have no value
        if tag_type == "Alias":
            return {
                "name":      name,
                "data_type": data_type,
                "tag_type":  tag_type,
                "value":     None,
            }

        # Get value from Decorated format
        value = None
        data_el = tree.find(".//Data[@Format='Decorated']")
        if data_el is not None:
            dv = data_el.find(".//DataValue")
            if dv is not None:
                value = dv.get("Value")

        return {
            "name":      name,
            "data_type": data_type,
            "tag_type":  tag_type,
            "value":     value,
        }

    except Exception:
        return None


def scan_zip(zip_bytes: bytes, version_label: str = "v1") -> ScannedProject:
    """
    Main entry point. Scans a ZIP file and returns a ScannedProject
    containing all programs with their routines and tags.
    """
    zf = zipfile.ZipFile(BytesIO(zip_bytes))
    all_paths = zf.namelist()

    # Find the RSLogix5000Content/Programs root
    # Works regardless of what the ZIP top-level folder is named
    programs_root = None
    for path in all_paths:
        if "RSLogix5000Content/Programs/" in path:
            idx = path.index("RSLogix5000Content/Programs/")
            programs_root = path[:idx + len("RSLogix5000Content/Programs/")]
            break

    if programs_root is None:
        raise ValueError("No RSLogix5000Content/Programs/ folder found in ZIP")

    # Detect project name from folder structure
    project_name = programs_root.split("/")[0] if "/" in programs_root else "Unknown"

    # Find all unique program folders
    program_folders = set()
    for path in all_paths:
        if path.startswith(programs_root):
            remainder = path[len(programs_root):]
            if "/" in remainder:
                program_folder = remainder.split("/")[0]
                if program_folder:
                    program_folders.add(program_folder)

    scanned_programs = []

    for program_folder in sorted(program_folders):
        parsed = parse_program_name(program_folder)

        # Scan ALL routines in this program
        routines_prefix = f"{programs_root}{program_folder}/Routines/"
        scanned_routines = []
        prestate_rungs = []
        has_prestate = False
        tags = []

        for path in all_paths:
            if path.startswith(routines_prefix) and path.endswith(".xml"):
                try:
                    xml_bytes = zf.read(path)
                    routine_name, routine_type, rungs = extract_routine_from_xml(xml_bytes)

                    # Normalise rung text for all routines
                    normalised_rungs = [
                        {
                            "number": r["number"],
                            "text": normalise_rung_text(r["text"], program_folder)
                        }
                        for r in rungs
                    ]

                    scanned_routines.append(ScannedRoutine(
                        routine_name = routine_name,
                        routine_type = routine_type,
                        rungs        = normalised_rungs,
                    ))

                    # Keep prestate_rungs for backward compatibility
                    if routine_name == "PrestateRoutine":
                        has_prestate = True
                        prestate_rungs = normalised_rungs

                except Exception:
                    pass

        scanned_programs.append(ScannedProgram(
            program_name     = program_folder,
            unit             = parsed["unit"],
            program_type     = parsed["program_type"],
            number           = parsed["number"],
            description_name = parsed["description_name"],
            has_prestate     = has_prestate,
            prestate_rungs   = prestate_rungs,
            tags             = tags,
            routines         = scanned_routines,
        ))

    return ScannedProject(
        name     = project_name,
        programs = scanned_programs,
    )

def normalise_rung_text(text: str, program_name: str) -> str:
    """Replace hardcoded program name with placeholder before comparison."""
    return text.replace(program_name, "__PROGRAM__")