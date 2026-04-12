# backend/main.py
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, get_db
from engine.parser import parse_routine_from_bytes, rungs_to_dict
from engine.diff import compare_routine
from engine.zip_scanner import scan_zip
from lxml import etree
from typing import Optional
from fastapi import Query
from engine.project_comparator import compare_projects
import models
import uuid

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="PLC Reviewer")

# Allow the React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

@app.post("/project/upload")
async def upload_project(
    file: UploadFile = File(...),
    version_label: str = "v1",
    db: Session = Depends(get_db)
):
    """
    Upload a Rockwell project ZIP file.
    Scans all programs, extracts PreState routines and tags,
    stores everything in the database.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="File must be a .zip file"
        )

    content = await file.read()

    # Scan the ZIP
    try:
        scanned = scan_zip(content, version_label)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to scan ZIP: {str(e)}"
        )

    # Save project record
    project = models.Project(
        name          = scanned.name,
        version_label = version_label,
        zip_filename  = file.filename,
        program_count = len(scanned.programs),
    )
    db.add(project)
    db.flush()  # get the project.id before adding programs

    # Save all programs
    ph_count = op_count = up_count = other_count = 0
    prestate_count = 0

    for sp in scanned.programs:
        program = models.Program(
            project_id       = project.id,
            program_name     = sp.program_name,
            unit             = sp.unit,
            program_type     = sp.program_type,
            number           = sp.number,
            description_name = sp.description_name,
            has_prestate     = sp.has_prestate,
            prestate_rungs   = sp.prestate_rungs,
            tags             = sp.tags,
        )
        db.add(program)
        db.flush()  # get program.id before adding routines

        # Save all routines for this program
        for sr in sp.routines:
            routine = models.Routine(
                program_id   = program.id,
                routine_name = sr.routine_name,
                routine_type = sr.routine_type,
                rung_count   = len(sr.rungs),
                rungs        = sr.rungs,
            )
            db.add(routine)

        if sp.program_type == "PH": ph_count += 1
        elif sp.program_type == "OP": op_count += 1
        elif sp.program_type == "UP": up_count += 1
        else: other_count += 1

        if sp.has_prestate:
            prestate_count += 1

    db.commit()

    return {
        "project_id":    str(project.id),
        "project_name":  scanned.name,
        "version_label": version_label,
        "zip_filename":  file.filename,
        "summary": {
            "total_programs":   len(scanned.programs),
            "with_prestate":    prestate_count,
            "phases_PH":        ph_count,
            "operations_OP":    op_count,
            "unit_procedures_UP": up_count,
            "other":            other_count,
        },
        "programs": [
            {
                "name":         sp.program_name,
                "unit":         sp.unit,
                "type":         sp.program_type,
                "has_prestate": sp.has_prestate,
                "rung_count":   len(sp.prestate_rungs),
                "tag_count":    len(sp.tags),
                "routine_count": len(sp.routines),
            }
            for sp in scanned.programs
        ]
    }

@app.post("/project/{project_id}/review")
async def review_project(
    project_id: str,
    program_types: list[str] = None,
    units: list[str] = None,
    db: Session = Depends(get_db)
):
    """
    Review all PreState routines in a project against the reference.
    Optionally filter by program_types (PH, OP, UP) and units (AI1, VC1 etc).
    """
    from engine.diff import compare_routine

    # Load reference
    ref = db.query(models.ReferenceRoutine).filter_by(
        reference_id="prestate_reference_v1"
    ).first()

    if not ref:
        raise HTTPException(
            status_code=400,
            detail="No reference routine found. Upload a reference first."
        )

    # Load programs from this project
    query = db.query(models.Program).filter(
        models.Program.project_id == project_id,
        models.Program.has_prestate == True
    )

    if program_types:
        query = query.filter(models.Program.program_type.in_(program_types))

    if units:
        query = query.filter(models.Program.unit.in_(units))

    programs = query.all()

    if not programs:
        raise HTTPException(
            status_code=404,
            detail="No programs found matching the filter criteria"
        )

    # Create review record
    review = models.Review(
        filename = f"project:{project_id}",
        status   = "running",
    )
    db.add(review)
    db.commit()

    # Run diff against each program
    all_findings = []

    for program in programs:
        from engine.parser import Rung
        from engine.zip_scanner import normalise_rung_text

        # Normalise the reference rungs — replace the reference program name
        # with the same placeholder used when the ZIP was scanned
        # so rung 2 POVR instruction does not generate false deviations
        normalised_ref_rungs = [
            {
                "number": r["number"],
                "text": normalise_rung_text(r["text"], "DS3_AI1_OP1010Purge")
            }
            for r in ref.rungs
        ]

        actual_rungs = [
            Rung(number=r["number"], text=r["text"])
            for r in (program.prestate_rungs or [])
        ]

        deviations = compare_routine(
            program_name    = program.program_name,
            reference_rungs = normalised_ref_rungs,
            actual_rungs    = actual_rungs,
        )

        for dev in deviations:
            finding = models.Finding(
                review_id = review.id,
                rule_id   = "ST-010",
                severity  = "critical" if dev.deviation_type in (
                    "missing_routine", "missing_rung"
                ) else "warning",
                program   = program.program_name,
                location  = (
                    f"Program:{program.program_name} / Routine:PreState"
                    + (f" / Rung:{dev.rung_number}" if dev.rung_number else "")
                ),
                message   = _build_message(dev),
                evidence  = "\n".join(dev.diff_lines) if dev.diff_lines else dev.actual_text or "",
                fix       = _build_fix(dev),
            )
            db.add(finding)
            all_findings.append(finding)

    review.status = "complete"
    db.commit()

    # Group findings by program for the response
    findings_by_program = {}
    for f in all_findings:
        if f.program not in findings_by_program:
            findings_by_program[f.program] = []
        findings_by_program[f.program].append({
            "deviation_type": f.evidence,
            "severity":       f.severity,
            "location":       f.location,
            "message":        f.message,
            "fix":            f.fix,
        })

    return {
        "review_id":        str(review.id),
        "project_id":       project_id,
        "programs_reviewed": len(programs),
        "total_findings":   len(all_findings),
        "findings_by_program": findings_by_program,
    }

@app.post("/project/compare")
async def compare_two_projects(
    project_a_id:   str,
    project_ref_id: str,
    routine_name:   str = "PrestateRoutine",
    normalise:      bool = True,
    program_types:  Optional[list[str]] = Query(default=None),
    units:          Optional[list[str]] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Compare a specific routine between two uploaded projects.
    Programs matched by full name.
    Flags added/removed programs and rung-level differences.
    """
    # Load programs from project A
    query_a = db.query(models.Program).filter(
        models.Program.project_id == project_a_id
    )
    if program_types:
        query_a = query_a.filter(models.Program.program_type.in_(program_types))
    if units:
        query_a = query_a.filter(models.Program.unit.in_(units))
    programs_a = query_a.all()

    # Load programs from reference project
    query_ref = db.query(models.Program).filter(
        models.Program.project_id == project_ref_id
    )
    if program_types:
        query_ref = query_ref.filter(models.Program.program_type.in_(program_types))
    if units:
        query_ref = query_ref.filter(models.Program.unit.in_(units))
    programs_ref = query_ref.all()

    if not programs_a and not programs_ref:
        raise HTTPException(
            status_code=404,
            detail="No programs found for one or both projects."
        )

    # Run comparison
    findings = compare_projects(
        programs_a   = programs_a,
        programs_ref = programs_ref,
        routine_name = routine_name,
        normalise    = normalise,
        db           = db,
    )

    # Build summary
    summary = {
        "identical":              sum(1 for f in findings if f.finding_type == "identical"),
        "programs_added":         sum(1 for f in findings if f.finding_type == "program_added"),
        "programs_removed":       sum(1 for f in findings if f.finding_type == "program_removed"),
        "routine_missing_in_a":   sum(1 for f in findings if f.finding_type == "routine_missing_in_a"),
        "routine_missing_in_ref": sum(1 for f in findings if f.finding_type == "routine_missing_in_ref"),
        "rungs_modified":         sum(1 for f in findings if f.finding_type == "rung_modified"),
        "rungs_added":            sum(1 for f in findings if f.finding_type == "rung_added"),
        "rungs_removed":          sum(1 for f in findings if f.finding_type == "rung_removed"),
    }

    return {
        "project_a_id":   project_a_id,
        "project_ref_id": project_ref_id,
        "routine_name":   routine_name,
        "normalise":      normalise,
        "programs_in_a":  len(programs_a),
        "programs_in_ref":len(programs_ref),
        "total_findings": len([f for f in findings if f.finding_type != "identical"]),
        "summary":        summary,
        "findings": [
            {
                "finding_type": f.finding_type,
                "program_name": f.program_name,
                "routine_name": f.routine_name,
                "severity":     f.severity,
                "rung_number":  f.rung_number,
                "message":      f.message,
                "evidence":     f.evidence,
                "fix":          f.fix,
            }
            for f in findings
            if f.finding_type != "identical"  # exclude clean programs from response
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