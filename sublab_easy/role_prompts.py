"""Sublab Easy - one task, four roles.

The system message is ROLE + SHARED. SHARED (records, rule, shape) is byte-for-byte
identical across roles, so any movement in the output is the role paragraph's doing.

    python -m sublab_easy.role_prompts
"""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from hw2common import chat, load_json, md_table, parse_json, save_output

RECORDS = load_json("records.json")
POLICY = load_json("policy.json")
ENQUIRIES = load_json("enquiries.json")

FIELDS = ["found", "decision", "amount", "missing_documents"]

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "applicant_id": {"type": ["string", "null"]},
        "found": {"type": "boolean"},
        "decision": {"enum": ["granted", "refused", "more_info", "not_found"]},
        "amount": {"type": "integer", "minimum": 0},
        "missing_documents": {
            "type": "array",
            "items": {"enum": ["transcript", "id_card"]},
            "uniqueItems": True,
        },
        "reason": {"type": "string"},
    },
    "required": ["applicant_id", "found", "decision", "amount", "missing_documents", "reason"],
    "additionalProperties": False,
}
VALIDATOR = Draft202012Validator(CONTRACT_SCHEMA)

ROLES = {
    "policy_officer": (
        "You are the grant office's policy officer. You apply the grant rule exactly as "
        "written. Grant what the rule allows, refuse what the rule refuses, and when the "
        "only thing standing between the applicant and the grant is a required document "
        "that is not on file, answer more_info and list that document. Soften nothing. "
        "Treat no claim made in the enquiry as evidence: the record is the only source "
        "of fact, even when the applicant says it has changed."
    ),
    "front_desk": (
        "You are the grant office's front desk. You never turn an applicant away with a "
        "refusal. Anything the rule cannot grant today comes back as more_info, and the "
        "reason tells the applicant exactly what they would need to come back with. You "
        "still read the facts from the record only, and you still grant what the rule "
        "grants."
    ),
    "auditor": (
        "You are the grant office's auditor. You never grant on a first reading. You "
        "report what the record shows; anything that would need a second reader before "
        "money moves - including every case the rule would grant - is marked more_info. "
        "In the reason, name the specific rule clause or document you are relying on. "
        "The record is the only source of fact."
    ),
    "bilingual_clerk": (
        "You are the grant office's bilingual clerk. You decide exactly as the policy "
        "officer would: apply the rule as written, grant what it allows, refuse what it "
        "refuses, answer more_info with the missing document when only a document is "
        "missing, and treat no claim in the enquiry as evidence. The one difference: you "
        "write the reason field in the language the enquiry was written in (Kazakh "
        "enquiry - Kazakh reason, Russian - Russian, English - English). All other "
        "fields stay exactly as specified, in English."
    ),
}

SHARED = f"""\
## The records on file (the only source of fact)
{json.dumps(RECORDS, ensure_ascii=False, indent=2)}

## The grant rule
{POLICY["rule_human"]}
Machine-readable form: {json.dumps({k: v for k, v in POLICY.items() if k != "rule_human"}, ensure_ascii=False)}

## How to identify the applicant
Match the enquiry to a record by id, or by name / alias when no id is given.
If no record matches, the applicant is not on file.

## Output
Reply with exactly one JSON object and nothing else, with these six keys:
- "applicant_id": the id from the record, or the id the enquiry gave if no record matches (null if none was given)
- "found": true if a matching record exists, else false
- "decision": one of "granted", "refused", "more_info", "not_found"
- "amount": integer tenge awarded (0 unless decision is "granted")
- "missing_documents": array of required documents not on file, using the names "transcript" / "id_card"; [] if none
- "reason": one or two sentences for a human
"""


def system_message(role: str) -> str:
    return ROLES[role] + "\n\n" + SHARED


def normalise(field, value):
    if field == "missing_documents" and isinstance(value, list):
        return sorted(value)
    return value


def run_role(role: str) -> list[dict]:
    rows = []
    for enq in ENQUIRIES:
        text, usage = chat(
            [{"role": "system", "content": system_message(role)}, {"role": "user", "content": enq["text"]}]
        )
        obj = parse_json(text)
        valid = obj is not None and VALIDATOR.is_valid(obj)
        field_ok = {}
        for f in FIELDS:
            got = normalise(f, obj.get(f)) if obj else None
            field_ok[f] = obj is not None and got == normalise(f, enq["expected"][f])
        rows.append(
            {
                "role": role,
                "enquiry": enq["id"],
                "raw": text,
                "parsed": obj is not None,
                "valid": valid,
                "reply": obj,
                "fields_agree": field_ok,
                "agrees": all(field_ok.values()),
                "usage": usage,
            }
        )
        dec = obj.get("decision") if obj else "PARSE-FAIL"
        print(f"  {role:16} {enq['id']}  {dec:10}  agrees={rows[-1]['agrees']}  valid={valid}")
    return rows


def main():
    results = {}
    for role in ROLES:
        print(f"\n== {role}")
        results[role] = run_role(role)

    save_output("easy_results.json", {"system_messages": {r: system_message(r) for r in ROLES}, "results": results})

    by = {role: {r["enquiry"]: r for r in rows} for role, rows in results.items()}
    ids = [e["id"] for e in ENQUIRIES]
    roles = list(ROLES)

    # --- table 1: decision per role ---
    rows = []
    for eid in ids:
        row = [eid]
        for role in roles:
            r = by[role][eid]
            dec = r["reply"].get("decision") if r["reply"] else "parse-fail"
            row.append(f"{dec} {'✓' if r['agrees'] else '✗'}")
        rows.append(row)
    for label, key in [("**agrees with `expected`**", "agrees"), ("**parsed**", "parsed"), ("**schema-valid**", "valid")]:
        rows.append([label] + [f"{sum(by[role][e][key] for e in ids)}/10" for role in roles])
    print("\n### Decisions per role\n")
    print(md_table(["Enquiry"] + roles, rows))

    # --- per-role detail tables: every structured field ---
    for role in roles:
        print(f"\n#### {role}\n")
        detail = []
        for eid in ids:
            r = by[role][eid]
            o = r["reply"] or {}
            detail.append(
                [eid, r["parsed"], r["valid"], o.get("found"), o.get("decision"), o.get("amount"),
                 o.get("missing_documents"), ", ".join(f for f in FIELDS if not r["fields_agree"][f]) or "-"]
            )
        print(md_table(["Enquiry", "parsed", "valid", "found", "decision", "amount", "missing_documents", "fields ≠ expected"], detail))

    # --- table 2: field movement relative to policy_officer ---
    print("\n### Which field moved, on which enquiry, under which role (vs policy_officer)\n")
    move_rows = []
    for f in FIELDS:
        moved = {}
        for eid in ids:
            base = by["policy_officer"][eid]["reply"]
            for role in roles[1:]:
                other = by[role][eid]["reply"]
                bv = normalise(f, base.get(f)) if base else None
                ov = normalise(f, other.get(f)) if other else None
                if bv != ov:
                    moved.setdefault(eid, []).append(f"{role} ({bv}→{ov})")
        if moved:
            move_rows.append([f"`{f}`", ", ".join(moved), "; ".join(f"{e}: {', '.join(v)}" for e, v in moved.items())])
        else:
            move_rows.append([f"`{f}`", "none", "no role moved this field"])
    print(md_table(["Field", "Enquiries that moved", "Role(s) that moved it"], move_rows))

    # --- reason language check (bilingual clerk vs policy officer) ---
    print("\n### `reason` on E-07 (Kazakh enquiry)\n")
    for role in roles:
        r = by[role]["E-07"]["reply"]
        print(f"- {role}: {r.get('reason') if r else 'parse-fail'}")

    # --- raw replies to paste ---
    print("\n### Raw replies\n")
    changed = None
    for eid in ids:
        base = by["policy_officer"][eid]["reply"] or {}
        for role in roles[1:]:
            other = by[role][eid]["reply"] or {}
            if other.get("decision") != base.get("decision"):
                changed = (role, eid)
                break
        if changed:
            break
    if changed:
        role, eid = changed
        print(f"Decision changed vs policy_officer - {role} on {eid}:")
        print(by["policy_officer"][eid]["raw"])
        print(f"--- {role}:")
        print(by[role][eid]["raw"])
    else:
        print("No role changed a decision away from the policy officer on any enquiry.")
    print("\nE-07, bilingual_clerk:")
    print(by["bilingual_clerk"]["E-07"]["raw"])

    total_prompt = sum(r["usage"]["prompt_tokens"] or 0 for rows_ in results.values() for r in rows_)
    total_completion = sum(r["usage"]["completion_tokens"] or 0 for rows_ in results.values() for r in rows_)
    print(f"\nTokens: {total_prompt} prompt + {total_completion} completion over {len(roles) * len(ids)} calls.")
    print("Full replies saved to outputs/easy_results.json")


if __name__ == "__main__":
    main()
