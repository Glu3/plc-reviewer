# backend/engine/project_comparator.py
from dataclasses import dataclass, field
from typing import Literal
from engine.diff import compare_routine
from engine.zip_scanner import normalise_rung_text
from engine.parser import Rung

@dataclass
class ComparisonFinding:
    finding_type:   Literal[
        "program_added", "program_removed",
        "routine_missing_in_a", "routine_missing_in_ref",
        "rung_added", "rung_removed", "rung_modified",
        "identical"
    ]
    program_name:   str
    routine_name:   str
    severity:       str
    rung_number:    int | None
    message:        str
    evidence:       str
    fix:            str


def compare_projects(
    programs_a:    list,   # list of models.Program from project A
    programs_ref:  list,   # list of models.Program from project Ref
    routine_name:  str,    # e.g. "PrestateRoutine"
    normalise:     bool,   # whether to normalise program name in rung text
    db,                    # database session
) -> list[ComparisonFinding]:
    """
    Compare a specific routine across two projects.
    Programs matched by full name.
    """
    import models

    # Build lookup by program name
    map_a   = {p.program_name: p for p in programs_a}
    map_ref = {p.program_name: p for p in programs_ref}

    all_names = sorted(set(map_a.keys()) | set(map_ref.keys()))
    findings  = []

    for program_name in all_names:
        in_a   = program_name in map_a
        in_ref = program_name in map_ref

        # Program only in A — added
        if in_a and not in_ref:
            findings.append(ComparisonFinding(
                finding_type = "program_added",
                program_name = program_name,
                routine_name = routine_name,
                severity     = "warning",
                rung_number  = None,
                message      = f"Program '{program_name}' exists in Project A but not in Reference.",
                evidence     = "",
                fix          = "Verify if this program should exist in the reference project.",
            ))
            continue

        # Program only in Ref — removed
        if in_ref and not in_a:
            findings.append(ComparisonFinding(
                finding_type = "program_removed",
                program_name = program_name,
                routine_name = routine_name,
                severity     = "warning",
                rung_number  = None,
                message      = f"Program '{program_name}' exists in Reference but not in Project A.",
                evidence     = "",
                fix          = "Verify if this program was intentionally removed from Project A.",
            ))
            continue

        # Program exists in both — compare the specific routine
        program_a   = map_a[program_name]
        program_ref = map_ref[program_name]

        # Load routines from DB
        routine_a = db.query(models.Routine).filter_by(
            program_id   = program_a.id,
            routine_name = routine_name,
        ).first()

        routine_ref = db.query(models.Routine).filter_by(
            program_id   = program_ref.id,
            routine_name = routine_name,
        ).first()

        # Routine missing in A
        if not routine_a and routine_ref:
            findings.append(ComparisonFinding(
                finding_type = "routine_missing_in_a",
                program_name = program_name,
                routine_name = routine_name,
                severity     = "critical",
                rung_number  = None,
                message      = f"Routine '{routine_name}' exists in Reference/{program_name} but not in A/{program_name}.",
                evidence     = "",
                fix          = f"Add '{routine_name}' routine to '{program_name}' in Project A.",
            ))
            continue

        # Routine missing in Ref
        if routine_a and not routine_ref:
            findings.append(ComparisonFinding(
                finding_type = "routine_missing_in_ref",
                program_name = program_name,
                routine_name = routine_name,
                severity     = "warning",
                rung_number  = None,
                message      = f"Routine '{routine_name}' exists in A/{program_name} but not in Reference/{program_name}.",
                evidence     = "",
                fix          = f"Verify if '{routine_name}' should exist in Reference.",
            ))
            continue

        # Both missing — skip
        if not routine_a and not routine_ref:
            continue

        # Both exist — run rung diff
        rungs_a   = routine_a.rungs   or []
        rungs_ref = routine_ref.rungs or []

        # Apply normalisation if requested
        if normalise:
            rungs_ref_prepared = rungs_ref   # already normalised during scan
            rungs_a_prepared   = rungs_a     # already normalised during scan
        else:
            # Denormalise — restore __PROGRAM__ back to actual name
            rungs_ref_prepared = [
                {"number": r["number"],
                 "text": r["text"].replace("__PROGRAM__", program_name)}
                for r in rungs_ref
            ]
            rungs_a_prepared = [
                {"number": r["number"],
                 "text": r["text"].replace("__PROGRAM__", program_name)}
                for r in rungs_a
            ]

        actual_rungs = [
            Rung(number=r["number"], text=r["text"])
            for r in rungs_a_prepared
        ]

        deviations = compare_routine(
            program_name    = program_name,
            reference_rungs = rungs_ref_prepared,
            actual_rungs    = actual_rungs,
        )

        if not deviations:
            findings.append(ComparisonFinding(
                finding_type = "identical",
                program_name = program_name,
                routine_name = routine_name,
                severity     = "info",
                rung_number  = None,
                message      = f"'{routine_name}' in '{program_name}' is identical in both projects.",
                evidence     = "",
                fix          = "",
            ))
            continue

        for dev in deviations:
            import difflib
            findings.append(ComparisonFinding(
                finding_type = _map_deviation_type(dev.deviation_type),
                program_name = program_name,
                routine_name = routine_name,
                severity     = "critical" if dev.deviation_type in (
                    "missing_routine", "missing_rung"
                ) else "warning",
                rung_number  = dev.rung_number,
                message      = _build_message(dev, routine_name),
                evidence     = "\n".join(dev.diff_lines) if dev.diff_lines else dev.actual_text or "",
                fix          = _build_fix(dev, routine_name),
            ))

    return findings


def _map_deviation_type(deviation_type: str) -> str:
    mapping = {
        "missing_rung":   "rung_removed",
        "extra_rung":     "rung_added",
        "modified_rung":  "rung_modified",
        "missing_routine":"routine_missing_in_a",
    }
    return mapping.get(deviation_type, deviation_type)


def _build_message(dev, routine_name: str) -> str:
    if dev.deviation_type == "missing_rung":
        return f"'{routine_name}' rung {dev.rung_number} exists in Reference but not in Project A."
    elif dev.deviation_type == "extra_rung":
        return f"'{routine_name}' rung {dev.rung_number} exists in Project A but not in Reference."
    elif dev.deviation_type == "modified_rung":
        return f"'{routine_name}' rung {dev.rung_number} differs between projects (similarity: {dev.similarity:.0%})."
    return "Unknown deviation."


def _build_fix(dev, routine_name: str) -> str:
    if dev.deviation_type == "missing_rung":
        return f"Add rung {dev.rung_number} to Project A / '{routine_name}'. Reference text: {(dev.reference_text or '')[:120]}"
    elif dev.deviation_type == "extra_rung":
        return f"Remove rung {dev.rung_number} from Project A / '{routine_name}', or add it to Reference."
    elif dev.deviation_type == "modified_rung":
        return f"Restore rung {dev.rung_number} in Project A / '{routine_name}' to match Reference, or raise a deviation request."
    return ""