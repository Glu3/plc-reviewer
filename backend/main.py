# backend/main.py
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import engine, get_db
from engine.parser import parse_routine_from_bytes, rungs_to_dict
import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="PLC Reviewer")


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
    """
    Upload a .L5X file to use as the reference PreState routine.
    Parses the rungs and stores them in the database.
    """
    content = await file.read()

    # Parse the file
    try:
        routine_name, rungs = parse_routine_from_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    # Store in database — replace if already exists
    existing = db.query(models.ReferenceRoutine).filter_by(
        reference_id="prestate_reference_v1"
    ).first()

    if existing:
        existing.rungs       = rungs_to_dict(rungs)
        existing.raw_xml     = content.decode("utf-8", errors="replace")
        existing.routine_name= routine_name
        existing.description = description
        existing.version    += 1
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
        "action":       action,
        "routine_name": routine_name,
        "rung_count":   len(rungs),
        "reference_id": "prestate_reference_v1",
        "rungs_preview": [
            {"number": r.number, "text": r.text[:60] + "..."}
            for r in rungs[:3]   # show first 3 rungs as preview
        ]
    }