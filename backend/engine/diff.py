# backend/engine/diff.py
import difflib
from dataclasses import dataclass
from typing import Literal
from engine.parser import Rung

@dataclass
class Deviation:
    deviation_type: Literal["missing_routine", "missing_rung",
                             "modified_rung", "extra_rung"]
    program:        str
    rung_number:    int | None      # reference rung number
    reference_text: str | None
    actual_text:    str | None
    similarity:     float
    diff_lines:     list[str]


def compare_routine(
    program_name:    str,
    reference_rungs: list[dict],
    actual_rungs:    list[Rung] | None
) -> list[Deviation]:
    """
    Compare a program's PreState rungs against the reference.
    Uses sequence-aware diffing so deleted/inserted rungs don't
    cause a cascade of false modified_rung findings.
    """

    # Case: routine completely missing
    if actual_rungs is None:
        return [Deviation(
            deviation_type = "missing_routine",
            program        = program_name,
            rung_number    = None,
            reference_text = None,
            actual_text    = None,
            similarity     = 0.0,
            diff_lines     = [],
        )]

    ref_texts = [r["text"] for r in reference_rungs]
    act_texts = [r.text   for r in actual_rungs]

    # SequenceMatcher finds the best alignment between the two lists
    # opcodes tell us what changed: equal / replace / delete / insert
    matcher = difflib.SequenceMatcher(None, ref_texts, act_texts, autojunk=False)
    deviations = []

    for opcode, ref_start, ref_end, act_start, act_end in matcher.get_opcodes():

        if opcode == "equal":
            # These rungs match exactly — no deviation
            continue

        elif opcode == "delete":
            # Rungs exist in reference but are missing from actual
            for i in range(ref_start, ref_end):
                deviations.append(Deviation(
                    deviation_type = "missing_rung",
                    program        = program_name,
                    rung_number    = reference_rungs[i]["number"],
                    reference_text = reference_rungs[i]["text"],
                    actual_text    = None,
                    similarity     = 0.0,
                    diff_lines     = [],
                ))

        elif opcode == "insert":
            # Rungs exist in actual but not in reference
            for j in range(act_start, act_end):
                deviations.append(Deviation(
                    deviation_type = "extra_rung",
                    program        = program_name,
                    rung_number    = actual_rungs[j].number,
                    reference_text = None,
                    actual_text    = actual_rungs[j].text,
                    similarity     = 0.0,
                    diff_lines     = [],
                ))

        elif opcode == "replace":
            # Some rungs changed — pair them up best we can
            ref_block = ref_texts[ref_start:ref_end]
            act_block = act_texts[act_start:act_end]

            # Pair each ref rung with the closest actual rung
            inner = difflib.SequenceMatcher(None, ref_block, act_block, autojunk=False)

            for inner_op, rs, re, as_, ae in inner.get_opcodes():
                if inner_op == "equal":
                    continue

                elif inner_op == "replace":
                    for k in range(max(re - rs, ae - as_)):
                        ri = ref_start + rs + k
                        ai = act_start + as_ + k

                        if ri < ref_end and ai < act_end:
                            # Modified rung — exists in both but different
                            ref_text = reference_rungs[ri]["text"]
                            act_text = actual_rungs[ai].text
                            similarity = difflib.SequenceMatcher(
                                None, ref_text, act_text
                            ).ratio()
                            diff = list(difflib.unified_diff(
                                ref_text.splitlines(),
                                act_text.splitlines(),
                                fromfile = f"reference/rung_{reference_rungs[ri]['number']}",
                                tofile   = f"{program_name}/rung_{actual_rungs[ai].number}",
                                lineterm = "",
                            ))
                            deviations.append(Deviation(
                                deviation_type = "modified_rung",
                                program        = program_name,
                                rung_number    = reference_rungs[ri]["number"],
                                reference_text = ref_text,
                                actual_text    = act_text,
                                similarity     = round(similarity, 3),
                                diff_lines     = diff,
                            ))
                        elif ri < ref_end:
                            deviations.append(Deviation(
                                deviation_type = "missing_rung",
                                program        = program_name,
                                rung_number    = reference_rungs[ri]["number"],
                                reference_text = reference_rungs[ri]["text"],
                                actual_text    = None,
                                similarity     = 0.0,
                                diff_lines     = [],
                            ))
                        elif ai < act_end:
                            deviations.append(Deviation(
                                deviation_type = "extra_rung",
                                program        = program_name,
                                rung_number    = actual_rungs[ai].number,
                                reference_text = None,
                                actual_text    = actual_rungs[ai].text,
                                similarity     = 0.0,
                                diff_lines     = [],
                            ))

                elif inner_op == "delete":
                    for k in range(rs, re):
                        ri = ref_start + k
                        deviations.append(Deviation(
                            deviation_type = "missing_rung",
                            program        = program_name,
                            rung_number    = reference_rungs[ri]["number"],
                            reference_text = reference_rungs[ri]["text"],
                            actual_text    = None,
                            similarity     = 0.0,
                            diff_lines     = [],
                        ))

                elif inner_op == "insert":
                    for k in range(as_, ae):
                        ai = act_start + k
                        deviations.append(Deviation(
                            deviation_type = "extra_rung",
                            program        = program_name,
                            rung_number    = actual_rungs[ai].number,
                            reference_text = None,
                            actual_text    = actual_rungs[ai].text,
                            similarity     = 0.0,
                            diff_lines     = [],
                        ))

    return deviations