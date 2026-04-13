# backend/engine/agent.py
import os
import json
from openai import OpenAI
from sqlalchemy.orm import Session
import models
from engine.project_comparator import compare_projects
from engine.parser import Rung

client = OpenAI(
    api_key  = os.getenv("GITHUB_TOKEN"),
    base_url = "https://models.inference.ai.azure.com",
)

MODEL = "gpt-4.1-mini"

SYSTEM_PROMPT = """You are a PLC code review assistant specialising in Rockwell
Automation projects. You help engineers analyse and compare PLC programs written
in Ladder Diagram (LD) and Structured Text (ST).

You have access to these tools:
- list_projects: see all uploaded projects
- list_routines: see routines available in a project
- prestate_review: check PreState compliance across all programs in a project
- compare_projects: compare any routine between two uploaded project versions

BEHAVIOUR RULES:
1. Always call list_projects first if the user wants to compare or review but
   has not provided project IDs. Show the results clearly.
2. When you receive tool results, explain them in plain engineering language.
   Never dump raw JSON. Highlight the most important findings first.
3. If a tool returns an error, explain what went wrong and what the user needs
   to do to fix it.
4. For rung differences, explain what the ladder logic change means functionally
   when you can determine it — e.g. XIO vs XIC reverses a contact condition.
5. Ask clarifying questions when you need more information. Do not assume.
6. Keep responses concise. Use bullet points for multiple findings.
7. Remember the full conversation — answer follow-up questions from previous
   results without calling tools again unless new data is needed.
8. When the user uploads a project you will be notified automatically —
   acknowledge it and suggest what they can do next."""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": """List all projects currently uploaded in the system.
            Call this first when the user wants to compare projects or run a review.""",
            "parameters": {
                "type":       "object",
                "properties": {},
                "required":   []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_routines",
            "description": """List all unique routine names available in a project.
            Call this when the user wants to compare a specific routine but has not
            named it yet.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type":        "string",
                        "description": "UUID of the project to list routines for."
                    }
                },
                "required": ["project_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "prestate_review",
            "description": """Compare the PrestateRoutine in every program of a project
            against the stored reference PrestateRoutine. Use this when the user wants
            to check PreState compliance. Applies rung normalisation by default.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type":        "string",
                        "description": "UUID of the project to review."
                    },
                    "program_types": {
                        "type":  "array",
                        "items": {"type": "string", "enum": ["PH", "OP", "UP"]},
                        "description": "Optional filter by program type."
                    },
                    "units": {
                        "type":  "array",
                        "items": {"type": "string"},
                        "description": "Optional filter by unit e.g. AI1, VC1."
                    }
                },
                "required": ["project_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_projects",
            "description": """Compare a specific routine between two uploaded projects.
            Programs matched by full name. Flags added/removed programs and rung differences.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_a_id": {
                        "type":        "string",
                        "description": "UUID of Project A."
                    },
                    "project_ref_id": {
                        "type":        "string",
                        "description": "UUID of the Reference project."
                    },
                    "routine_name": {
                        "type":        "string",
                        "description": "Routine name e.g. PrestateRoutine, Running, CommonLogic."
                    },
                    "normalise": {
                        "type":        "boolean",
                        "description": "Replace program name with __PROGRAM__ before comparing."
                    },
                    "program_types": {
                        "type":  "array",
                        "items": {"type": "string", "enum": ["PH", "OP", "UP"]},
                        "description": "Optional filter by program type."
                    },
                    "units": {
                        "type":  "array",
                        "items": {"type": "string"},
                        "description": "Optional filter by unit."
                    }
                },
                "required": ["project_a_id", "project_ref_id", "routine_name", "normalise"]
            }
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict, db: Session) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        if tool_name == "list_projects":
            projects = db.query(models.Project).order_by(
                models.Project.uploaded_at.desc()
            ).all()
            if not projects:
                return "No projects uploaded yet."
            result = []
            for p in projects:
                result.append({
                    "id":            str(p.id),
                    "name":          p.name,
                    "version_label": p.version_label,
                    "program_count": p.program_count,
                    "uploaded_at":   p.uploaded_at.isoformat(),
                })
            return json.dumps(result)

        elif tool_name == "list_routines":
            from sqlalchemy import distinct
            routines = db.query(
                distinct(models.Routine.routine_name)
            ).join(
                models.Program,
                models.Routine.program_id == models.Program.id
            ).filter(
                models.Program.project_id == tool_input["project_id"]
            ).all()
            names = sorted([r[0] for r in routines])
            if not names:
                return "No routines found for this project."
            return json.dumps(names)

        elif tool_name == "prestate_review":
            from engine.diff import compare_routine
            from engine.zip_scanner import normalise_rung_text

            ref = db.query(models.ReferenceRoutine).filter_by(
                reference_id="prestate_reference_v1"
            ).first()
            if not ref:
                return "Error: No reference routine found. Please upload a reference PreState routine first using the Upload Reference tab."

            query = db.query(models.Program).filter(
                models.Program.project_id == tool_input["project_id"],
                models.Program.has_prestate == True
            )
            if tool_input.get("program_types"):
                query = query.filter(
                    models.Program.program_type.in_(tool_input["program_types"])
                )
            if tool_input.get("units"):
                query = query.filter(
                    models.Program.unit.in_(tool_input["units"])
                )
            programs = query.all()

            if not programs:
                return "No programs found matching the filter criteria."

            all_findings = []
            for program in programs:
                normalised_ref = [
                    {"number": r["number"],
                     "text": normalise_rung_text(r["text"], "DS3_AI1_OP1010Purge")}
                    for r in ref.rungs
                ]
                actual_rungs = [
                    Rung(number=r["number"], text=r["text"])
                    for r in (program.prestate_rungs or [])
                ]
                deviations = compare_routine(
                    program_name    = program.program_name,
                    reference_rungs = normalised_ref,
                    actual_rungs    = actual_rungs,
                )
                for dev in deviations:
                    all_findings.append({
                        "program":        program.program_name,
                        "deviation_type": dev.deviation_type,
                        "rung_number":    dev.rung_number,
                        "similarity":     dev.similarity,
                    })

            return json.dumps({
                "programs_reviewed": len(programs),
                "total_findings":    len(all_findings),
                "findings":          all_findings[:50],
            })

        elif tool_name == "compare_projects":
            query_a = db.query(models.Program).filter(
                models.Program.project_id == tool_input["project_a_id"]
            )
            query_ref = db.query(models.Program).filter(
                models.Program.project_id == tool_input["project_ref_id"]
            )
            if tool_input.get("program_types"):
                query_a   = query_a.filter(models.Program.program_type.in_(tool_input["program_types"]))
                query_ref = query_ref.filter(models.Program.program_type.in_(tool_input["program_types"]))
            if tool_input.get("units"):
                query_a   = query_a.filter(models.Program.unit.in_(tool_input["units"]))
                query_ref = query_ref.filter(models.Program.unit.in_(tool_input["units"]))

            programs_a   = query_a.all()
            programs_ref = query_ref.all()

            findings = compare_projects(
                programs_a   = programs_a,
                programs_ref = programs_ref,
                routine_name = tool_input["routine_name"],
                normalise    = tool_input["normalise"],
                db           = db,
            )

            summary = {
                "identical":              sum(1 for f in findings if f.finding_type == "identical"),
                "programs_added":         sum(1 for f in findings if f.finding_type == "program_added"),
                "programs_removed":       sum(1 for f in findings if f.finding_type == "program_removed"),
                "rungs_modified":         sum(1 for f in findings if f.finding_type == "rung_modified"),
                "rungs_added":            sum(1 for f in findings if f.finding_type == "rung_added"),
                "rungs_removed":          sum(1 for f in findings if f.finding_type == "rung_removed"),
            }

            non_identical = [
                {
                    "finding_type": f.finding_type,
                    "program_name": f.program_name,
                    "rung_number":  f.rung_number,
                    "message":      f.message,
                    "evidence":     f.evidence[:200] if f.evidence else "",
                }
                for f in findings
                if f.finding_type != "identical"
            ]

            return json.dumps({
                "summary":        summary,
                "total_findings": len(non_identical),
                "findings":       non_identical[:50],
            })

        else:
            return f"Unknown tool: {tool_name}"

    except Exception as e:
        return f"Tool error: {str(e)}"


def run_agent(messages: list, db: Session) -> str:
    """
    Run the agent loop with tool calling using OpenAI-compatible API.
    messages: full conversation history
    Returns the final text response.
    """
    # Convert to OpenAI message format
    openai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in messages:
        openai_messages.append({"role": m["role"], "content": m["content"]})

    while True:
        response = client.chat.completions.create(
            model    = MODEL,
            messages = openai_messages,
            tools    = TOOLS,
        )

        choice = response.choices[0]

        # If the model wants to use a tool
        if choice.finish_reason == "tool_calls":
            # Add assistant message with tool calls
            openai_messages.append(choice.message)

            # Execute each tool call
            for tool_call in choice.message.tool_calls:
                tool_input = json.loads(tool_call.function.arguments)
                result     = execute_tool(tool_call.function.name, tool_input, db)

                openai_messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      result,
                })

        else:
            # Final text response
            return choice.message.content or "I encountered an issue generating a response."