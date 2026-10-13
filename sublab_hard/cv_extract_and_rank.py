"""Sublab Hard - stories in, CVs out, the best candidate by code.

    python -m sublab_hard.cv_extract_and_rank

1. extract: one call per story -> a CV record, validated against CV_SCHEMA,
   then re-checked in code (GPA conversion, publication count).
2. score:   one call per CV -> three 0-5 scores and nothing it has to compute.
   The weighted total and the winner are computed here, in code.
3. prose:   a separate call asking, in prose, who should win.
"""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from hw2common import DATA, chat, load_json, md_table, parse_json, save_output

RUBRIC = load_json("candidate_rubric.json")
STORIES = {p.stem: p.read_text(encoding="utf-8") for p in sorted((DATA / "candidates").glob("story-*.md"))}
WEIGHTS = {c["id"]: c["weight"] for c in RUBRIC["criteria"]}

_nstr = {"type": ["string", "null"]}
_nnum = {"type": ["number", "null"]}
_nint = {"type": ["integer", "null"]}

CV_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_id": {"type": "string"},
        "full_name": _nstr,
        "story_language": {"type": "string"},
        "degree": _nstr,
        "graduation_year": _nint,
        "gpa_original": _nnum,
        "gpa_original_scale": _nnum,
        "gpa_4_scale": _nnum,
        "languages": {"type": "array", "items": {"type": "string"}},
        "published_outputs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"title_or_topic": {"type": "string"}, "venue": _nstr, "year": _nint,
                               "status": {"enum": ["published", "accepted"]},
                               "peer_reviewed": {"type": ["boolean", "null"]}},
                "required": ["title_or_topic", "venue", "year", "status", "peer_reviewed"],
            },
        },
        "published_peer_reviewed_count": _nint,
        "unpublished_outputs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"title_or_topic": {"type": "string"},
                               "status": {"enum": ["submitted", "under_review", "in_preparation", "in_press",
                                                   "planned", "not_peer_reviewed", "other"]}},
                "required": ["title_or_topic", "status"],
            },
        },
        "experience_periods": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"role": {"type": "string"}, "organisation": _nstr, "start": _nstr, "end": _nstr,
                               "months": _nint, "countable": {"type": "boolean"}, "relevant": {"type": "boolean"},
                               "note": _nstr},
                "required": ["role", "start", "end", "months", "countable", "relevant"],
            },
        },
        "total_countable_months": _nint,
        "ambiguities": {
            "type": "array",
            "items": {"type": "object", "properties": {"field": {"type": "string"}, "issue": {"type": "string"},
                                                       "kind": {"enum": ["contradiction", "unclear"]}},
                      "required": ["field", "issue", "kind"]},
        },
        "evidence": {"type": "object", "additionalProperties": {"type": "string"}},
    },
    "required": ["candidate_id", "full_name", "story_language", "degree", "graduation_year", "gpa_original",
                 "gpa_original_scale", "gpa_4_scale", "languages", "published_outputs",
                 "published_peer_reviewed_count", "unpublished_outputs", "experience_periods",
                 "total_countable_months", "ambiguities", "evidence"],
    "additionalProperties": False,
}
CV_VALIDATOR = Draft202012Validator(CV_SCHEMA)

EXTRACT_PROMPT = f"""\
You turn one scholarship applicant's written story into a structured CV record.
Reply with exactly one JSON object and nothing else, matching this JSON Schema:
{json.dumps(CV_SCHEMA, indent=1)}

RULES - follow every one of them:
1. NULL, NEVER ESTIMATE. A fact the story does not state is null. Never estimate, infer or
   guess. No GPA stated means gpa_original, gpa_original_scale and gpa_4_scale are all null -
   not inferred from honours, "distinction", the degree, the university or the tone.
2. GPA SCALE. If the GPA is on a scale other than 4.0, record the original value and its scale
   in gpa_original / gpa_original_scale, and convert linearly: gpa_4_scale = gpa_original /
   gpa_original_scale * 4, rounded to 2 decimals. A GPA on 4.0 is recorded with scale 4.0 and
   copied as is.
3. PUBLISHED MEANS PUBLISHED. A paper counts as published only when the story says published or
   accepted. "Submitted", "under review", "in preparation", "planned", "in press", posters and
   talks are NOT published: put them in unpublished_outputs and do not count them.
   PEER REVIEW IS STATED, NOT ASSUMED. peer_reviewed is true only when the story says the venue
   is peer-reviewed / refereed; if the story does not say, it is null - a "student conference",
   "proceedings" or "journal" is not evidence of peer review on its own.
   published_peer_reviewed_count = the number of items in published_outputs with peer_reviewed
   true (0 if there are none).
4. CONTRADICTIONS ARE NOT RESOLVED. If the story gives two different values for the same field
   (two GPAs, two graduation years, months that do not match the dates), do not pick one and do
   not average: the field is null, and the contradiction goes in ambiguities with both values
   quoted, kind "contradiction". A hedge like "I think it was" next to another value is a
   contradiction. A value that is merely vague or relative (e.g. "last year" with no date) is
   null with kind "unclear" - that is missing information, not a contradiction.
5. MONTHS, NOT JOBS. Count months of relevant work or internship. Overlapping periods count once.
   A period with no dates and no stated month count is not countable (countable=false, months=null).
   An ongoing period ("continuing today", "since X") counts only the month total the story itself
   states - do not compute months up to today's date. Part-time months count as months.
   total_countable_months = sum of months of countable, relevant periods, without overlaps.
6. EVIDENCE. For every non-null field you fill (full_name, degree, graduation_year, gpa_original,
   gpa_4_scale, languages, published_peer_reviewed_count, total_countable_months), put a short
   verbatim quote from the story in evidence under that field name. The quote stays in the
   story's original language.
7. LANGUAGE. The story may be in English, Kazakh or Russian. Field values (degree, roles, statuses)
   are written in English; names are transliterated as written by the applicant if in Latin
   script, otherwise kept as written. story_language names the language of the story.
8. candidate_id is the id given to you in the message (e.g. "story-03")."""

SCORE_PROMPT = f"""\
You score one scholarship candidate against a fixed rubric, from their extracted CV record.

Rubric criteria:
{json.dumps(RUBRIC["criteria"], indent=1, ensure_ascii=False)}

Counting rules:
{json.dumps(RUBRIC["counting_rules"], indent=1, ensure_ascii=False)}

Score each criterion with an integer from 0 to 5, using the what_0_means / what_5_means anchors and
interpolating between them. A null gpa_4_scale scores 0 on academic, as the rubric's GPA rule says.
Do NOT compute a weighted total, a rank or a winner - that is done elsewhere.

Reply with exactly one JSON object and nothing else:
{{"academic": int 0-5, "research": int 0-5, "experience": int 0-5,
  "justification": {{"academic": str, "research": str, "experience": str}}}}"""

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        **{k: {"type": "integer", "minimum": 0, "maximum": 5} for k in WEIGHTS},
        "justification": {"type": "object"},
    },
    "required": list(WEIGHTS),
}
SCORE_VALIDATOR = Draft202012Validator(SCORE_SCHEMA)

TRAPS = {
    "no GPA": lambda cv: cv.get("gpa_original") is None and cv.get("gpa_4_scale") is None,
    "other GPA scale": lambda cv: cv.get("gpa_original_scale") not in (None, 4, 4.0),
    "unpublished paper": lambda cv: len(cv.get("unpublished_outputs") or []) > 0,
    "contradiction": lambda cv: any(a.get("kind") == "contradiction" for a in cv.get("ambiguities") or []),
}


def code_checks(cv: dict) -> list[str]:
    """What the code re-derives instead of trusting the model. Returns notes; may fix cv in place."""
    notes = []
    o, s, g4 = cv.get("gpa_original"), cv.get("gpa_original_scale"), cv.get("gpa_4_scale")
    if o is not None and s:
        expect = round(o / s * 4, 2)
        if g4 is None or abs(g4 - expect) > 0.01:
            notes.append(f"gpa_4_scale {g4} != {o}/{s}*4 = {expect}; code set it to {expect}")
            cv["gpa_4_scale"] = expect
    if g4 is not None and not 0 <= g4 <= 4:
        notes.append(f"gpa_4_scale {g4} outside 0-4; set to null")
        cv["gpa_4_scale"] = None
    # count only what is both published/accepted AND stated as peer-reviewed
    counted = sum(1 for p in cv.get("published_outputs") or []
                  if p.get("status") in ("published", "accepted") and p.get("peer_reviewed") is True)
    if cv.get("published_peer_reviewed_count") != counted:
        notes.append(f"published count {cv.get('published_peer_reviewed_count')} != {counted} listed; code used {counted}")
        cv["published_peer_reviewed_count"] = counted
    months = sum(p["months"] or 0 for p in cv.get("experience_periods") or [] if p.get("countable") and p.get("relevant"))
    if cv.get("total_countable_months") is not None and cv["total_countable_months"] != months:
        notes.append(f"total_countable_months {cv['total_countable_months']} != sum of periods {months} "
                     "(may be overlap - kept model value, flagged)")
    return notes


def nulls(cv: dict) -> list[str]:
    keys = ["full_name", "degree", "graduation_year", "gpa_original", "gpa_original_scale", "gpa_4_scale",
            "published_peer_reviewed_count", "total_countable_months"]
    return [k for k in keys if cv.get(k) is None]


def extract(cid: str, story: str) -> dict:
    text, usage = chat([
        {"role": "system", "content": EXTRACT_PROMPT},
        {"role": "user", "content": f"Candidate id: {cid}\n\nStory:\n\n{story}"},
    ])
    cv = parse_json(text)
    errors = [e.message for e in CV_VALIDATOR.iter_errors(cv)] if cv is not None else ["did not parse"]
    checks = code_checks(cv) if cv is not None else []
    return {"raw": text, "cv": cv, "parsed": cv is not None, "valid": cv is not None and not errors,
            "errors": errors[:5], "code_checks": checks, "usage": usage}


def score(cv: dict) -> dict:
    slim = {k: v for k, v in cv.items() if k != "evidence"}
    text, usage = chat([
        {"role": "system", "content": SCORE_PROMPT},
        {"role": "user", "content": json.dumps(slim, ensure_ascii=False, indent=1)},
    ])
    obj = parse_json(text)
    valid = obj is not None and SCORE_VALIDATOR.is_valid(obj)
    return {"raw": text, "scores": obj, "valid": valid, "usage": usage}


def weighted(scores: dict) -> float:
    return round(sum(WEIGHTS[k] * scores[k] for k in WEIGHTS), 2)


def prose_winner() -> str:
    stories = "\n\n".join(f"===== {cid} =====\n{s}" for cid, s in STORIES.items())
    text, _ = chat([
        {"role": "system", "content": "You advise a scholarship committee. Answer in plain prose, in English."},
        {"role": "user", "content":
            "One funded scholarship place, six candidates. Here is the rubric the committee uses:\n"
            + json.dumps(RUBRIC, ensure_ascii=False, indent=1)
            + "\n\nAnd here are the six applications:\n\n" + stories
            + "\n\nWhich candidate should win, and why? Name the winner and the runner-up in a short paragraph."},
    ], json_mode=False)
    return text


def main():
    out = {"extract_prompt": EXTRACT_PROMPT, "score_prompt": SCORE_PROMPT, "candidates": {}}

    print("== Part 1: extraction")
    for cid, story in STORIES.items():
        r = extract(cid, story)
        out["candidates"][cid] = {"extraction": r}
        print(f"  {cid}: parsed={r['parsed']} valid={r['valid']} {r['errors'] or ''} {r['code_checks'] or ''}")

    rows = []
    for cid, c in out["candidates"].items():
        r = c["extraction"]
        cv = r["cv"] or {}
        traps = [t for t, f in TRAPS.items() if cv and f(cv)]
        amb = "; ".join(f"[{a.get('kind')}] {a['field']}: {a['issue']}" for a in cv.get("ambiguities") or [])
        rows.append([cid, "yes" if r["parsed"] else "no", "yes" if r["valid"] else f"no ({'; '.join(r['errors'])})",
                     ", ".join(nulls(cv)) or "none", ", ".join(traps) or "none",
                     "; ".join(r["code_checks"]) or "-", amb or "-"])
    print("\n### Part 1 — extraction\n")
    print(md_table(["Story", "Parsed?", "Valid?", "Fields that came back `null`", "Traps hit",
                    "Code corrections", "Ambiguities recorded"], rows))

    print("\n### Key extracted fields\n")
    krows = []
    for cid, c in out["candidates"].items():
        cv = c["extraction"]["cv"] or {}
        krows.append([cid, cv.get("full_name"), cv.get("degree"), cv.get("graduation_year"),
                      f"{cv.get('gpa_original')}/{cv.get('gpa_original_scale')}", cv.get("gpa_4_scale"),
                      cv.get("published_peer_reviewed_count"), len(cv.get("unpublished_outputs") or []),
                      cv.get("total_countable_months"), ", ".join(cv.get("languages") or [])])
    print(md_table(["Story", "name", "degree", "grad year", "GPA (orig/scale)", "gpa_4_scale", "published",
                    "unpublished", "months", "languages"], krows))

    print("\n### story-06 extraction\n")
    print(json.dumps(out["candidates"]["story-06"]["extraction"]["cv"], ensure_ascii=False, indent=2))

    print("\n== Part 2: scoring")
    ranking = []
    for cid, c in out["candidates"].items():
        cv = c["extraction"]["cv"]
        if cv is None:
            print(f"  {cid}: no CV to score")
            continue
        s = score(cv)
        c["scoring"] = s
        if not s["valid"]:
            print(f"  {cid}: score reply invalid: {s['raw'][:200]}")
            continue
        total = weighted(s["scores"])
        c["weighted_total"] = total
        ranking.append((total, cid))
        print(f"  {cid}: {[s['scores'][k] for k in WEIGHTS]} -> {total}")

    ranking.sort(key=lambda r: (-r[0], r[1]))
    srows = []
    for cid, c in out["candidates"].items():
        sc = (c.get("scoring") or {}).get("scores") or {}
        srows.append([cid] + [sc.get(k, "-") for k in WEIGHTS] + [c.get("weighted_total", "-")])
    print("\n### Part 2 — scores and the winner\n")
    print(md_table(["Candidate", "academic (0–5)", "research (0–5)", "experience (0–5)", "weighted total (code)"], srows))

    print("\nRanking (code): " + " > ".join(f"{cid} ({t})" for t, cid in ranking))
    if ranking:
        top = [cid for t, cid in ranking if t == ranking[0][0]]
        winner_names = [f"{cid} ({out['candidates'][cid]['extraction']['cv'].get('full_name')})" for cid in top]
        print(f"**Winner, computed by my code:** {' and '.join(winner_names)} with {ranking[0][0]}"
              + (" — TIE, the rubric does not break it" if len(top) > 1 else ""))
        if len(ranking) > 1:
            gap = round(ranking[0][0] - ranking[1][0], 2)
            print(f"Gap between #1 and #2: {gap}" + ("  (within 0.05 - too close to call on these scores)" if gap <= 0.05 else ""))
        out["ranking"] = ranking

    print("\n== Prose: which candidate should win? (separate call)\n")
    prose = prose_winner()
    out["prose_answer"] = prose
    print(prose)

    for c in out["candidates"].values():
        c["extraction"].pop("raw", None) if c["extraction"]["parsed"] else None
    save_output("hard_results.json", out)
    print("\nFull records saved to outputs/hard_results.json")


if __name__ == "__main__":
    main()
