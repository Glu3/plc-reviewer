# backend/main.py
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, get_db
from engine.parser import parse_routine_from_bytes, rungs_to_dict
from engine.diff import compare_routine
from lxml import etree
import models
import uuid

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="PLC Reviewer")

# Allow the React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "message": "PLC Reviewer API running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/reference")
async def upload_reference(
    file: UploadFile = File(...),
    description: str = "PreState reference routine",
    db: Session = Depends(get_db)
):
    content = await file.read()
    try:
        routine_name, rungs = parse_routine_from_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    existing = db.query(models.ReferenceRoutine).filter_by(
        reference_id="prestate_reference_v1"
    ).first()

    if existing:
        existing.rungs        = rungs_to_dict(rungs)
        existing.raw_xml      = content.decode("utf-8", errors="replace")
        existing.routine_name = routine_name
        existing.description  = description
        existing.version     += 1
        db.commit()
        action = "updated"
    else:
        ref = models.ReferenceRoutine(
            reference_id  = "prestate_reference_v1",
            routine_name  = routine_name,
            rungs         = rungs_to_dict(rungs),
            raw_xml       = content.decode("utf-8", errors="replace"),
            description   = description,
        )
        db.add(ref)
        db.commit()
        action = "created"

    return {
        "action":        action,
        "routine_name":  routine_name,
        "rung_count":    len(rungs),
        "reference_id":  "prestate_reference_v1",
        "rungs_preview": [
            {"number": r.number, "text": r.text[:60] + "..."}
            for r in rungs[:3]
        ]
    }


@app.post("/review")
async def review_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a .L5X project file. 
    Finds every Program, extracts its PreState routine,
    compares against the reference, returns all deviations.
    """
    content = await file.read()

    # Load the reference from database
    ref = db.query(models.ReferenceRoutine).filter_by(
        reference_id="prestate_reference_v1"
    ).first()

    if not ref:
        raise HTTPException(
            status_code=400,
            detail="No reference routine found. Upload a reference first via POST /reference."
        )

    # Parse the uploaded file
    try:
        tree = etree.fromstring(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML: {str(e)}")

    # Create a review record
    review_id = str(uuid.uuid4())
    review = models.Review(
        id       = review_id,
        filename = file.filename,
        status   = "running",
    )
    db.add(review)
    db.commit()

    # Find all Programs in the file
    programs = tree.findall(".//Program")

    # If no Programs found, treat the file as a single routine file
    # (like your Prestate.l5x which has no Program wrapper)
    if not programs:
        routine_name = ref.routine_name
        _, actual_rungs = parse_routine_from_bytes(content)
        program_name = file.filename.replace(".l5x", "").replace(".L5X", "")
        deviations = compare_routine(program_name, ref.rungs, actual_rungs)
        all_deviations = deviations
        programs_checked = [program_name]
    else:
        all_deviations = []
        programs_checked = []

        for program_el in programs:
            program_name = program_el.get("Name", "Unknown")
            programs_checked.append(program_name)

            # Find PreState routine inside this program
            routine_name = ref.routine_name
            routine_el = program_el.find(
                f".//Routine[@Name='{routine_name}']"
            )

            if routine_el is None:
                # Routine missing entirely from this program
                all_deviations += compare_routine(program_name, ref.rungs, None)
            else:
                # Parse the rungs from this routine
                routine_xml = etree.tostring(routine_el)
                _, actual_rungs = parse_routine_from_bytes(routine_xml)
                all_deviations += compare_routine(
                    program_name, ref.rungs, actual_rungs
                )

    # Save findings to database
    for dev in all_deviations:
        finding = models.Finding(
            review_id = review_id,
            rule_id   = "ST-010",
            severity  = "critical" if dev.deviation_type in (
                            "missing_routine", "missing_rung"
                        ) else "warning",
            program   = dev.program,
            location  = (
                f"Program:{dev.program} / Routine:{ref.routine_name}"
                + (f" / Rung:{dev.rung_number}" if dev.rung_number else "")
            ),
            message   = _build_message(dev),
            evidence  = "\n".join(dev.diff_lines) if dev.diff_lines else dev.actual_text or "",
            fix       = _build_fix(dev),
        )
        db.add(finding)

    review.status = "complete"
    db.commit()

    # Build the response
    return {
        "review_id":       review_id,
        "filename":        file.filename,
        "status":          "complete",
        "programs_checked": programs_checked,
        "total_deviations": len(all_deviations),
        "findings": [
            {
                "program":        dev.program,
                "deviation_type": dev.deviation_type,
                "severity":       "critical" if dev.deviation_type in (
                                      "missing_routine", "missing_rung"
                                  ) else "warning",
                "rung_number":    dev.rung_number,
                "message":        _build_message(dev),
                "similarity":     dev.similarity,
                "diff":           dev.diff_lines,
                "fix":            _build_fix(dev),
            }
            for dev in all_deviations
        ]
    }


def _build_message(dev) -> str:
    if dev.deviation_type == "missing_routine":
        return f"Program '{dev.program}' is missing the PreState routine entirely."
    elif dev.deviation_type == "missing_rung":
        return f"Program '{dev.program}' / PreState is missing rung {dev.rung_number} from the reference."
    elif dev.deviation_type == "modified_rung":
        return f"Program '{dev.program}' / PreState rung {dev.rung_number} differs from reference (similarity: {dev.similarity:.0%})."
    elif dev.deviation_type == "extra_rung":
        return f"Program '{dev.program}' / PreState has an extra rung {dev.rung_number} not in reference."
    return "Unknown deviation."


def _build_fix(dev) -> str:
    if dev.deviation_type == "missing_routine":
        return f"Add a PreState routine to program '{dev.program}' using the reference template."
    elif dev.deviation_type == "missing_rung":
        return f"Insert rung {dev.rung_number} into '{dev.program}'/PreState. Reference: {(dev.reference_text or '')[:120]}"
    elif dev.deviation_type == "modified_rung":
        return f"Restore rung {dev.rung_number} in '{dev.program}'/PreState to match the reference, or raise a deviation request."
    elif dev.deviation_type == "extra_rung":
        return f"Remove extra rung {dev.rung_number} from '{dev.program}'/PreState, or raise a deviation request to add it to the reference."
    return ""