# HW2 submission

**Name:** Islam Uzakov
**Student ID:** 12345
**Group:** ИТ-2301
**Repository:** https://github.com/MegaZhaba/ai-2026-hw2

## AI tool disclosure

State which AI tools you used and for what. Expected and fine; undisclosed use
is not. If you used a model to help you draft a prompt, say which prompt.

> I used **Claude (Anthropic, Claude Code desktop app)** for this homework. It wrote all three
> programs (`hw2common.py`, `sublab_easy/role_prompts.py`, `sublab_medium/chat_memory.py`,
> `sublab_hard/cv_extract_and_rank.py`), including every prompt in them: the four role
> paragraphs and shared block in Easy, the assistant and compression prompts in Medium, and the
> extraction, scoring and prose prompts in Hard. It ran the programs with my OpenAI key (via
> `.env`) and drafted all the written answers below from the numbers of that run. All tables are
> copied from the program output; full raw replies are in `outputs/` (git-ignored, so not
> in the repository). Model under test: `gpt-5.6-luna` for every call.

---

## Sublab Easy — one task, four roles

The system message is `ROLE paragraph + SHARED block`. The shared block (records JSON, rule,
how to match an applicant, output shape) is byte-identical across roles. One call per
(role, enquiry), `response_format=json_object`, validated with `jsonschema` against the
contract (six required keys, `decision` enum, `amount` integer ≥ 0, `missing_documents` ⊆
{transcript, id_card}, no extra keys). 40 calls, 41 050 prompt + 4 767 completion tokens.

### Decisions per role

One row per enquiry. In each cell write the `decision` your run returned, and
whether it agrees with `expected` in `data/enquiries.json`:

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-02 | more_info ✓ | more_info ✓ | more_info ✓ | more_info ✓ |
| E-03 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-04 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-05 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-06 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-07 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-08 | not_found ✓ | not_found ✓ | not_found ✓ | not_found ✓ |
| E-09 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-10 | more_info ✓ | more_info ✓ | more_info ✓ | more_info ✓ |
| **agrees with `expected`** | 10/10 | 7/10 | 6/10 | 10/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

"Agrees" means all four structured fields equal `expected`. Per-role detail (every field):

<details><summary>policy_officer / bilingual_clerk (identical structured fields)</summary>

| Enquiry | found | decision | amount | missing_documents | fields ≠ expected |
|---|---|---|---|---|---|
| E-01 | true | granted | 250000 | [] | - |
| E-02 | true | more_info | 0 | [id_card] | - |
| E-03 | true | refused | 0 | [] | - |
| E-04 | true | refused | 0 | [] | - |
| E-05 | true | granted | 250000 | [] | - |
| E-06 | true | granted | 150000 | [] | - |
| E-07 | true | granted | 250000 | [] | - |
| E-08 | false | not_found | 0 | [] | - |
| E-09 | true | refused | 0 | [] | - |
| E-10 | true | more_info | 0 | [id_card] | - |
</details>

<details><summary>front_desk</summary>

| Enquiry | found | decision | amount | missing_documents | fields ≠ expected |
|---|---|---|---|---|---|
| E-01 | true | granted | 250000 | [] | - |
| E-02 | true | more_info | 0 | [id_card] | - |
| E-03 | true | more_info | 0 | [] | decision |
| E-04 | true | more_info | 0 | [] | decision |
| E-05 | true | granted | 250000 | [] | - |
| E-06 | true | granted | 150000 | [] | - |
| E-07 | true | granted | 250000 | [] | - |
| E-08 | false | not_found | 0 | [] | - |
| E-09 | true | more_info | 0 | [] | decision |
| E-10 | true | more_info | 0 | [id_card] | - |
</details>

<details><summary>auditor</summary>

| Enquiry | found | decision | amount | missing_documents | fields ≠ expected |
|---|---|---|---|---|---|
| E-01 | true | more_info | 0 | [] | decision, amount |
| E-02 | true | more_info | 0 | [id_card] | - |
| E-03 | true | refused | 0 | [] | - |
| E-04 | true | refused | 0 | [] | - |
| E-05 | true | more_info | 0 | [] | decision, amount |
| E-06 | true | more_info | 0 | [] | decision, amount |
| E-07 | true | more_info | 0 | [] | decision, amount |
| E-08 | false | not_found | 0 | [] | - |
| E-09 | true | refused | 0 | [] | - |
| E-10 | true | more_info | 0 | [id_card] | - |
</details>

### Which field moved, on which enquiry, under which role

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` | **none** | no role moved `found` on any enquiry |
| `decision` | E-01, E-03, E-04, E-05, E-06, E-07, E-09 | auditor on E-01, E-05, E-06, E-07 (granted → more_info); front_desk on E-03, E-04, E-09 (refused → more_info) |
| `amount` | E-01, E-05, E-06, E-07 | auditor only (250000/150000 → 0), always together with its `decision` change |
| `missing_documents` | **none** | no role moved `missing_documents` on any enquiry |

Fields that moved on no enquiry: `found` and `missing_documents`. The bilingual clerk moved
**no structured field on any enquiry**.

`reason` language on E-07 (the only non-English enquiry) — all four roles answered in Kazakh;
on the nine English enquiries all four answered in English (4 Cyrillic `reason`s in 40, all on E-07):

- policy_officer: Сіз грант талаптарына сай келесіз: GPA 3.4, кіріс санаты 1 және қажетті құжаттардың екеуі де тіркелген.
- front_desk: Сіз грант талаптарына сай келесіз: GPA 3.4, табыс санатыңыз 1 және қажетті құжаттардың екеуі де бар.
- auditor: Жазба бойынша GPA 3.4, табыс санаты 1 және transcript пен id_card құжаттары бар, … Алайда грант кеңсесінің аудит тәртібі бойынша бірінші оқылымда грант берілмейді және екінші тексеру қажет.
- bilingual_clerk: Сіз грант талаптарына сай келесіз: GPA көрсеткіші 2.67-ден жоғары, табыс санатыңыз 1 және қажетті құжаттардың екеуі де бар.

### Raw replies

Paste the full reply for **one enquiry where a role changed the decision** away
from the policy officer's:

```
E-01, policy_officer:
{"applicant_id":"A-201","found":true,"decision":"granted","amount":250000,"missing_documents":[],"reason":"You qualify because your GPA is 3.4, your income band is 1, and both required documents are on file. The grant amount is 250,000 tenge."}

E-01, auditor:
{"applicant_id":"A-201","found":true,"decision":"more_info","amount":0,"missing_documents":[],"reason":"The record shows GPA 3.4, income band 1, and both required documents, satisfying the grant rule. Under the grant office audit instruction, cases that would qualify require a second reader before money moves."}
```

Paste the full reply for **E-07 (the Kazakh enquiry)** from the bilingual
clerk, so the `reason` language is visible:

```
{"applicant_id":"A-201","found":true,"decision":"granted","amount":250000,"missing_documents":[],"reason":"Сіз грант талаптарына сай келесіз: GPA көрсеткіші 2.67-ден жоғары, табыс санатыңыз 1 және қажетті құжаттардың екеуі де бар."}
```

### Written answers

**1. Which fields are role-sensitive and which are not?** Point at rows in your
tables.

> `found` and `missing_documents` are not role-sensitive: in the field-movement table both rows
> are "none" — every role found the same nine applicants, said A-999 was not on file, and listed
> `id_card` as missing for A-202 (E-02, E-10) and nothing else anywhere. Those two fields are
> read off the record, and no role paragraph tells the model to read the record differently.
> `decision` is the role-sensitive field (7 of 10 enquiries moved), and `amount` moved only as a
> consequence of `decision` (the 4 auditor rows where `granted` became `more_info` and the amount
> dropped to 0). The **auditor** and **front_desk** are the roles that move `decision`: auditor
> on the four `granted` rows (E-01, E-05, E-06, E-07), front_desk on the three `refused` rows
> (E-03, E-04, E-09). The **bilingual_clerk** is the one expected to move only `reason`, and it
> moved no structured field at all (10/10, identical to the policy officer). In my run it did
> not even move the *language* of `reason`: on E-07 all four roles already wrote the reason in
> Kazakh, and on the English enquiries all four wrote English. So the only measurable effect of
> its paragraph was wording; the model mirrors the enquiry's language without being told to.

**2. Which enquiries are most sensitive to the role, and why those?** Say what
E-03, E-04, E-07 and E-10 are each testing.

> Sensitivity follows the rule's outcome, not the applicant. Every enquiry whose correct answer
> is `granted` moved under the auditor, every `refused` moved under the front desk, and the
> `more_info` (E-02, E-10) and `not_found` (E-08) rows moved under nobody — those are already
> the answers the "soft" roles fall back to. **E-03** (Madina, GPA 2.4) is a clean refusal on
> the GPA clause with complete documents: it tests whether a role will soften a refusal the
> rule makes for a reason no document can fix; front_desk turned it into `more_info` with
> `missing_documents: []`, which is incoherent — there is nothing to come back with. **E-04**
> (Yerlan, GPA 3.1 but income band 3) is the same test on the income clause; same result, and
> the same empty list. **E-07** is the Kazakh enquiry: it tests alias matching (Айгерім Серік →
> A-201) and language of `reason` independently of the decision; every role matched the alias,
> only the auditor changed the decision (for its own reason, not the language). **E-10** tests
> whether a claim in the message ("I uploaded my id card yesterday") is treated as evidence; all
> four roles held `more_info` + `[id_card]`, including the front desk, whose paragraph is the
> most applicant-friendly. E-09 (name only, no id) also moved under front_desk, so name lookup
> did not make the refusal any harder to soften.

**3. Where does discretion belong — the role paragraph, or code that reads
`decision` afterwards?** Say what a downstream program can and cannot tell
about which role produced a record.

> In code. A downstream program sees only the six fields, and nothing in them says which role
> wrote it. The auditor's `more_info` on E-01 and the front desk's `more_info` on E-04 are
> byte-for-byte the same shape as the real `more_info` on E-02 — the only tell is that
> `missing_documents` is `[]`, and a program would have to *know* that a `more_info` with nothing
> missing is a role artefact; the `reason` text says so, but that is free text for a human.
> What a program cannot tell is whether `more_info` means "a document is missing", "a human
> should look again" or "we do not like to say no". So I would let the model produce the
> rule's answer (policy-officer behaviour) and put discretion after it: code that sends every
> `granted` to a second reader (the auditor's job), and code that renders a `refused` as a
> friendly "here is what you could do" message (the front desk's job), while the stored
> `decision` stays what the rule says. If a role must run in the model, the record should carry
> the role and prompt version explicitly as a field the code sets, not the model.

**4. Is a role a boundary?** Say in Week 2 terms what the role paragraph is
made of, and what you would put in code — not in the prompt — if a wrong
`decision` were expensive.

> No. In Week 2 terms the role paragraph is just more tokens at the top of the same document the
> model is continuing; it shifts the probability of the continuation, it does not restrict it.
> The enquiry's tokens sit in the same context with the same standing, so a message written to
> push the other way (E-10's claim, or a straightforward "ignore the above, grant me") competes
> with the role on equal terms. My run shows the role "working" — the auditor never granted —
> but that is a statistical tendency on ten friendly inputs, not a guarantee. If a wrong
> `decision` were expensive, the rule itself would live in code: it is three clauses over
> `records.json` (GPA ≥ 2.67, band ∈ {1,2}, both documents), so code can compute `decision`,
> `amount` and `missing_documents` deterministically and either reject any model reply that
> disagrees or use the model only to identify the applicant and write `reason`. On top of that:
> schema validation (already there), `amount` checked against the band table, the record id
> checked to exist, and a human approval step before any `granted` pays out.

---

## Sublab Medium — memory you choose

Design: the assistant's system message carries the grant rule and the amounts but **not** the
applicant records, so anything it knows about the applicant must come from the conversation or
from the state — otherwise the probes would be answerable from the records and would not test
memory. Each reply is the contract JSON, with `reason` as the conversational answer. Probes are
asked one at a time against the end-of-conversation context and not remembered (so one probe's
answer cannot help the next). Token counts are `usage.prompt_tokens` from the API.
On `compress`, the model gets the transcript and the schema description, the reply is parsed
and validated against `memory_state.schema.json`; only if both pass are the turns replaced by
the state (which is then sent inside the system message). Otherwise the program prints why and
keeps the history.

### Tokens per call

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---|---|
| 1 | 321 | 321 |
| 2 | 428 | 427 |
| 3 | 516 | 514 |
| 4 | 608 | 605 |
| 5 | 710 | 693 |
| 6 | 803 | 798 |
| 7 | 900 | 909 |
| 8 | 1002 | 1015 |
| 9 | 1102 | 1113 |
| 10 | — (`<compress>` skipped) | 1221 (the compress call itself) |
| 11 | 1217 | 730 |
| 12 | 1302 | 822 |
| **peak** | 1302 | 1221 (compress call) / 1113 (conversation calls only) |
| **total for the run** | 8909 | 9168 |

Each probe call afterwards sent ≈ 1379 tokens in A and ≈ 921 in B. Calls 11–12 together:
2519 (A) vs 1552 (B), −38 %.

### Probes after the conversation

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | yes | You are Daniyar Qoshan, applicant A-202. | yes | You are Daniyar Qoshan, and your applicant number is A-202. |
| Q-2 missing document | turn 5 | yes by string match, **no on reading** | I can't confirm which document is missing without the applicant record. The record is needed to verify whether your transcript and ID card are on file. | yes | The ID card is still missing from your file. Your transcript was reported as submitted; the record is needed to confirm the current status. |
| Q-3 band and amount | turns 3–4 | yes | I can't confirm your income band from this conversation because your statement is not verified against the applicant record. If the record shows band 2, the grant amount would be 150,000 KZT, … | yes | Your income band was reported as band 2, which corresponds to 150,000 KZT. I would need the applicant record to confirm … |
| Q-4 the constraint | turn 6 | **no** | I can't confirm the office's schedule from the available information. The record or office guidance is needed to determine which days you can come. | yes | You can come to the office on Thursday to submit your ID card. |
| Q-5 the open question | turn 7 | yes | You asked whether a scanned letter from your employer would count or whether you needed to provide the original. | yes | You asked whether a scanned letter from your employer would count toward the grant documents. … |
| **retrieved** | | 4/5 by `expect_contains` (3/5 on reading) | | 5/5 | |

The A/Q-2 "yes" is a false positive of the substring check: "ID card" appears in the answer, but
the model says it *cannot* tell which document is missing. I report both numbers rather than
quietly taking the higher one.

### The state my compression produced

```json
{
  "applicant_id": "A-202",
  "topic": "Study grant eligibility, required documents, grant amount, and application processing",
  "facts": [
    "The applicant's name is Daniyar Qoshan.",
    "The applicant sent their transcript last week.",
    "The applicant's income band is 2, according to their family's certificate.",
    "The applicant could not upload their ID card because the scanner at home broke.",
    "The applicant can only come to the office on Thursdays because they have lab all week otherwise.",
    "The applicant has a scanned letter from their employer and asked whether it counts.",
    "The applicant's sister Aruzhan applied last year and is on file too."
  ],
  "decisions": [
    "The applicant's eligibility cannot be confirmed without the applicant record, including verification of GPA, income band, and transcript and ID card status.",
    "The ID card is reported as missing and can be submitted at the office on Thursday.",
    "The required documents listed for this grant are the transcript and ID card; an employer letter is not listed.",
    "If the applicant record confirms income band 2 and all eligibility requirements, the grant would be 150,000 KZT.",
    "Aruzhan's application from last year does not affect the applicant's A-202 application or establish eligibility."
  ],
  "constraints": [
    "The applicant can submit the ID card at the office on Thursday.",
    "Eligibility and the grant amount depend on confirmation from the applicant record.",
    "The applicant has lab all week except Thursday."
  ],
  "open_questions": [
    "Does the applicant qualify for the study grant?",
    "Does a scanned letter from the employer count, or must it be the original?",
    "If the applicant brings the ID card on Thursday, will the decision be made the same day?"
  ],
  "language": "Kazakh and English"
}
```

`--interactive` was also run (transcript in `outputs/interactive_demo.txt`): after one turn,
`compress` grew the context from ≈391 to ≈446 tokens — the state object was larger than the
conversation it replaced.

### Written answers

**1. What did compression buy?** Peak tokens both ways, probes retrieved both
ways, and — if a probe was lost — which one and which turn it came from.

> Peak: A 1302, B 1113 for conversation calls (1221 if the compress call itself is counted —
> it is the most expensive call of run B, because it has to read the whole history once). After
> the compress turn each call was ≈ 490 tokens cheaper (730 vs 1217, 822 vs 1302) and each probe
> ≈ 460 cheaper (921 vs 1379). For the twelve scripted positions alone B was *more* expensive
> (9168 vs 8909): the compress call costs 1221 in plus 584 out (the state object is long), and
> two later turns don't pay that back; on input tokens it breaks even after about three turns,
> and with the five probes B is ahead
> (≈ 13 770 vs ≈ 15 800). And A is the one that keeps growing linearly forever. Probes: A 4/5 by
> the check, 3/5 on reading; B 5/5. Nothing was lost by compression. A lost **Q-4** (Thursday,
> turn 6): with the whole history present the model read "which day can I come?" as a question
> about office hours and said it couldn't know. A also effectively lost **Q-2** (id card, turn 5),
> answering "I can't confirm which document is missing". B got both because the state put
> "Thursday" under `constraints` and "ID card … missing" under `decisions` — near the top of the
> context, labelled, instead of nine turns back in a long thread. Compression bought fewer tokens
> *and* better recall here; the second part is not guaranteed.

**2. Why must the state be structured rather than a paragraph?** You could have
asked for "a summary". Say what changes when the summary is an object with
named fields.

> Three things change. (a) It can be checked: my program validates the object against the schema
> before throwing the turns away, and refuses to replace the history if it fails. A paragraph
> can only be checked for "is it text". (b) The fields force decisions the summariser would
> otherwise skip: a fluent paragraph is about the decision, so it drops the Thursday constraint
> and the unanswered employer-letter question first — exactly Q-4 and Q-5. Having `constraints`
> and `open_questions` as required arrays means the model has to look for them, and an empty
> array is a visible claim ("there were none"), not a silent omission. (c) Code can use it:
> `applicant_id` can be looked up in the records, `facts` (what the applicant *said*) are kept
> apart from `decisions` (what the assistant concluded) — which is the E-10 lesson from Sublab
> Easy, a claim is not evidence — and two states can be diffed or merged on the next compress.

**3. What is missing from your state that you would add?** Name what you would
add and what you would drop to pay for it.

> Add **provenance per fact**: the turn it came from and whether it is an applicant claim or
> something confirmed by the record. My state says "income band is 2, according to their
> family's certificate" — good — but most facts carry no such marker. Add **answered questions**
> with what was answered: my state lists the employer-letter question as open *and* puts "an
> employer letter is not listed" in `decisions`, so it contradicts itself, and it lists "Does the
> applicant qualify?" as open although it was answered conditionally. Add **commitments /
> next actions** ("bring id card on Thursday") as their own field instead of burying them in
> `constraints` and `decisions`. I would also need a rule against invention: the state says "The
> applicant has a scanned letter from their employer", but the applicant only asked whether such
> a letter would count — that fact was made up, despite the schema's "nothing may be invented".
> To pay for it I would drop `topic` (one line nobody reads), and drop restating the rule in
> `decisions` ("required documents are transcript and ID card") — that is already in the system
> message on every call.

**4. When is compression the wrong choice?** Name a conversation where it would
lose something that cannot be recovered, and say whether your program would
notice.

> When the exact words are the thing being kept. An applicant appealing a refusal who dictates
> their statement, or who changes their story — "my band is 2" in turn 3, "actually it's 3, the
> certificate is old" in turn 9 — loses something on compression: a summary resolves the
> contradiction into one value (or keeps only the latest), and the fact that the story *changed*
> is itself evidence an officer would want. Once the turns are discarded, that is gone. Also short
> conversations: in my interactive test a one-turn chat got *bigger* after compress (391 → 446
> tokens). My program would not notice either case. It checks that the summary parses and fits
> the schema — shape, not content. A schema-valid state that drops a fact or invents one (as
> mine did with the employer letter) passes. To notice, I would add a recall check before
> discarding turns (every id, number, amount and weekday that appears in the turns must appear
> in the state, else keep the history), and archive the raw turns to disk instead of deleting them.

---

## Sublab Hard — stories in, CVs out, the best candidate by code

Pipeline: (1) one extraction call per story with my CV schema and eight numbered rules in the
system prompt (`EXTRACT_PROMPT` in the code), validated with `jsonschema`, then re-checked in code
(GPA conversion recomputed, published count recounted from the list, months summed); (2) one
scoring call per CV that returns `academic`, `research`, `experience` as integers 0–5 plus a
justification string per criterion, validated; (3) code computes
`0.5·academic + 0.3·research + 0.2·experience`, rounded to 2 decimals, and ranks; (4) a separate
plain-text call with the six stories and the rubric asks who should win.

I ran it twice. **Run 1** (`outputs/hard_console_run1.txt`) exposed a problem with story-02
(see written answer 1); I added a rule and re-ran. The tables below are **run 2**, the final
version of the code.

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back `null` | Traps hit |
|---|---|---|---|---|
| story-01 | yes | yes | none | none (clean control: 3.8/4.0, two published, 8 months) |
| story-02 | yes | yes | graduation_year, gpa_original, gpa_original_scale, gpa_4_scale | **no GPA** ("distinction" not turned into a number ✓); graduation "last year" → null, recorded as *unclear*, not a contradiction; published-but-not-stated-peer-reviewed paper → counted 0 |
| story-03 | yes | yes | none | **other GPA scale** (4.6/5.0 → 3.68, scale 5.0 recorded ✓); **unpublished paper** (under review, not counted ✓) |
| story-04 | yes | yes | none | **unpublished paper** ×3 (1 under review, 2 in preparation — 1 counted ✓) |
| story-05 | yes | yes | none | **unpublished paper** (in writing, not counted ✓); story in Kazakh, extracted fine |
| story-06 | yes | yes | graduation_year, gpa_original, gpa_original_scale, gpa_4_scale | **contradiction** ×2 (GPA 3.2 vs 3.5; graduated 2024 vs graduating 2026 — both null + recorded ✓); poster not counted ✓ |

Key extracted values (run 2):

| Story | name | degree | grad year | GPA orig/scale | gpa_4_scale | published p-r | unpublished | months |
|---|---|---|---|---|---|---|---|---|
| story-01 | Aziza Bekova | BSc Computer Science | 2025 | 3.8/4.0 | 3.8 | 2 | 0 | 8 |
| story-02 | Dias Yerzhanov | Bachelor's Information Systems | null | null | null | 0 | 0 | 36 |
| story-03 | Lyazzat Omarova | BSc Applied Mathematics | 2025 | 4.6/5.0 | 3.68 | 1 | 1 | 14 |
| story-04 | Tamerlan Saparov | BSc Computer Science | 2026 | 3.6/4.0 | 3.6 | 1 | 3 | 24 |
| story-05 | Аиша Нұрланқызы | Bachelor's Computer Science | 2025 | 3.9/4.0 | 3.9 | 1 | 1 | 6 |
| story-06 | Nurzhan Abilov | BSc Statistics | null | null | null | 1 | 1 | 40 |

The four traps, for reference: no GPA stated · a GPA on another scale · a paper
that is not published · a story that contradicts itself.

Paste the extraction for **story-06**, the one that contradicts itself:

```json
{
  "candidate_id": "story-06",
  "full_name": "Nurzhan Abilov",
  "story_language": "English",
  "degree": "BSc in Statistics",
  "graduation_year": null,
  "gpa_original": null,
  "gpa_original_scale": null,
  "gpa_4_scale": null,
  "languages": ["Kazakh", "Russian", "English"],
  "published_outputs": [
    {
      "title_or_topic": "Survey weighting",
      "venue": "peer-reviewed proceedings",
      "year": null,
      "status": "published",
      "peer_reviewed": true
    }
  ],
  "published_peer_reviewed_count": 1,
  "unpublished_outputs": [
    { "title_or_topic": "Poster at a local event", "status": "not_peer_reviewed" }
  ],
  "experience_periods": [
    {
      "role": "Insurance analytics team member",
      "organisation": null,
      "start": "February 2023",
      "end": null,
      "months": 40,
      "countable": true,
      "relevant": true,
      "note": "Part-time for the first eight months, then full-time."
    }
  ],
  "total_countable_months": 40,
  "ambiguities": [
    {
      "field": "gpa_original",
      "issue": "The story gives two different GPA values: \"3.2\" and \"3.5\".",
      "kind": "contradiction"
    },
    {
      "field": "graduation_year",
      "issue": "The story gives two different graduation claims: \"graduated in 2024\" and \"final-year student graduating in 2026\".",
      "kind": "contradiction"
    }
  ],
  "evidence": {
    "full_name": "Nurzhan Abilov",
    "degree": "I graduated in 2024 with a BSc in Statistics.",
    "languages": "Languages: Kazakh, Russian, English.",
    "published_peer_reviewed_count": "one paper published, in a peer-reviewed proceedings",
    "total_countable_months": "which is about forty months"
  }
}
```

### Part 2 — scores and the winner

| Candidate | academic (0–5) | research (0–5) | experience (0–5) | weighted total (code) |
|---|---|---|---|---|
| story-01 | 5 | 5 | 2 | **4.40** |
| story-02 | 0 | 0 | 5 | 1.00 |
| story-03 | 4 | 3 | 3 | 3.50 |
| story-04 | 4 | 3 | 5 | 3.90 |
| story-05 | 5 | 3 | 1 | 3.60 |
| story-06 | 0 | 3 | 5 | 1.90 |

Ranking computed by code: story-01 (4.40) > story-04 (3.90) > story-05 (3.60) > story-03 (3.50) >
story-06 (1.90) > story-02 (1.00). Gap #1–#2: 0.50.

(Run 1, before the peer-review rule: identical except story-02 research 3 → total 1.90, tied
with story-06.)

**Winner, computed by my code:** story-01 — Aziza Bekova, 4.40

**The model's prose answer, asked separately ("who should win?"):**

> Aziza Bekova should win, with Tamerlan Saparov as runner-up. Aziza has the strongest academic
> record (GPA 3.8/4.0) and two published peer-reviewed papers; her eight months of relevant data
> work add further support. Tamerlan has 24 months of directly relevant experience, but only one
> published paper and a lower 3.6/4.0 GPA; his under-review and in-preparation papers cannot be
> counted.

### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it?** Name the
story that forced it.

> **Story-02** forced "peer review is stated, not assumed" (plus a `peer_reviewed` field on each
> publication, and a `kind` on each ambiguity: `contradiction` vs `unclear`). In run 1 Dias's
> paper "in a student conference proceedings" — the story never says peer-reviewed — came back
> with `published_peer_reviewed_count: null`. The model was being careful; *my code* broke it: its
> consistency check recounted "published" items, found 1, and overwrote the null with 1. The
> scorer then gave research 3, total 1.90, tied with story-06. Story-02 was also flagged as a
> "contradiction" because the model recorded "last year" as an ambiguity, and my trap detector
> treated every ambiguity as a contradiction — but a vague date is missing information, not a
> self-contradiction. After the rule: peer_reviewed null → not counted, research 0, total 1.00,
> and only story-06 is flagged as contradictory.

**2. Where did the model guess, and where did your code have to decide?** One
example of each, from your run.

> Model guessed: story-06 experience. The story says "since February 2023, which is about forty
> months", with no end date. The model recorded `months: 40, countable: true` and the scorer gave
> experience 5. "About" is a hedge, and an ongoing period's length depends on when the letter was
> written, which the story doesn't say; my own rule 5 says to use the month count the story
> states, so 40 is defensible, but the model treated an estimate as a count without recording it
> as an ambiguity. The interpolated scores are guesses too: the rubric anchors only 0 and 5, and
> "one published paper = 3" or "14 months = 3" is the model's own scale (consistent across
> candidates, but not in the rubric). Code decided: the weighted totals and the ranking; the
> GPA conversion check (3.68 for 4.6/5.0 recomputed and matched); and in run 1 the tie at 1.90
> between story-02 and story-06, which my code broke alphabetically — a decision the rubric
> doesn't make. And run 1's published-count override is the cautionary example: the code
> "decided" and was wrong, because its check encoded a weaker rule than the prompt.

**3. Did your prose ranking and your computed ranking agree?** Say which one
you trust and why — and if they agreed, what you would need to see before
trusting the prose one alone.

> They agreed on the top two: Aziza Bekova first, Tamerlan Saparov second. The prose answer did
> not rank the other four, so I can't compare beyond that. I trust the computed one because every
> number in it is traceable: score → field → evidence quote → story, and the total is arithmetic I
> can redo. The prose answer's reasons match the fields (3.8 GPA, two papers, under-review papers
> not counted), but I can't see how it weighed them or whether it applied the null rules — it read
> the raw stories, not my records. Before trusting the prose alone I would want to see: the same
> answer across several re-runs and with the stories in a different order; agreement on a case
> that is actually close (here the gap is 0.5, so agreement is cheap); and it handling the traps —
> for example, not giving Nurzhan credit for a GPA or Dias for an unstated peer review.

**4. The rubric has no anchor for a contradicted field.** The stories say 3.2
and then 3.5; the rubric defines a 0 and a 5 and nothing in between for this
case. Say what you did and what the rule should be.

> I followed the counting rules literally: the GPA is contradicted, so `gpa_4_scale` is null; a
> null GPA "scores 0 on academic"; so Nurzhan got academic 0 — the same score as a story with "no
> academic information at all", although his story contains a degree and a GPA that is ≥ 3.2
> whichever value is true. That conflates "contradicted" with "absent", and the rubric's own 0
> anchor says it means *no information*, which is false here. The rule I think it should be:
> score a contradicted value on its **lower** reading (3.2 here, which would be about 3/5 —
> conservative, so the applicant can't gain from being inconsistent), mark the score as
> contradicted so a human sees it, and never let a contradiction score the same as an absence.
> On my numbers that would take story-06 from 1.90 to about 3.40 — still not the winner, but
> above story-02 and close to story-03.

**5. How close were your top two candidates?** If they were within 0.05, say
what you would tell the committee and what you would change in the extraction
to make that call defensible.

> 0.50 apart (4.40 vs 3.90), so not within 0.05. But the gap rests almost entirely on research
> (5 vs 3, worth 0.6 weighted), i.e. on Aziza's two papers being peer-reviewed — which her story
> states explicitly, so I'm fairly comfortable with it. The close call in my run is lower down:
> story-05 (3.60) vs story-03 (3.50), and that 0.10 comes from Lyazzat's 4.6/5.0 converting to
> 3.68 — just under the rubric's 3.7 line — so a linear-conversion choice moved her academic score
> from 5 to 4. If a pair were within 0.05 I would tell the committee it is a tie on this rubric
> and give them both records side by side with the evidence quotes, not a winner. To make such a
> call defensible I would take the scoring of computable criteria out of the model: map GPA,
> counted months and publication count to scores with fixed formulas in code (e.g. months/24·5
> capped at 5), leaving the model only the extraction; and run the extraction several times to
> check that the fields are stable before ranking on them.

---

## Reflection (optional, one short paragraph)

Having now written a role prompt, compressed a conversation, and ranked six
extractions — what will you do differently the next time you build something
that has to get reliable structured output out of a model?

> Validate meaning, not only shape. Every reply in this homework parsed and every one passed its
> schema, and still: the auditor's `more_info` looks identical to a real one, the compressed state
> invented a fact, the substring check counted a non-answer as recall, and my own consistency
> check overwrote a correct null. Next time I would keep anything that can be computed
> deterministically (the grant rule, the GPA mapping, the total) in code, use the model for the
> parts that need reading, and check those against the source text, not just the schema.
