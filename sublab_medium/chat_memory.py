"""Sublab Medium - memory you choose: the `compress` command.

    python -m sublab_medium.chat_memory                # scripted run A vs B + probes
    python -m sublab_medium.chat_memory --interactive  # type `compress`, `tokens`, `state`, `quit`

A Session owns what is sent. Uncompressed, that is the system message plus every
turn. After `compress`, the turns are replaced by one validated state object and
the conversation continues from it. A summary that fails to parse or validate
never replaces the history.
"""

from __future__ import annotations

import argparse
import json

from jsonschema import Draft202012Validator

from hw2common import chat, count_tokens, load_json, md_table, parse_json, save_output

POLICY = load_json("policy.json")
SCRIPT = load_json("chat_script.json")
STATE_SCHEMA = load_json("memory_state.schema.json")
STATE_VALIDATOR = Draft202012Validator(STATE_SCHEMA)
COMPRESS_MARKER = "<compress>"

# The assistant gets the rule but NOT the records: everything it knows about the
# applicant has to come from the conversation (or the state), which is what the
# probes measure.
SYSTEM = f"""\
You are the assistant at a grant office, chatting with one applicant.

The grant rule: {POLICY["rule_human"]}
Amounts: band 1 = 250000 KZT, band 2 = 150000 KZT. Required documents: "transcript", "id_card".

You do not have the applicant records in this chat. Work only from what the applicant
has told you in this conversation (or from the saved conversation state, if one is given),
and say when you would need the record to confirm something.

Reply to every message with exactly one JSON object and nothing else:
{{"applicant_id": string or null, "found": boolean, "decision": "granted"|"refused"|"more_info"|"not_found",
  "amount": integer, "missing_documents": [strings], "reason": string}}
"reason" is your actual reply to the applicant: answer what they asked, in plain words.
"found" is true once the applicant has identified themselves with an id."""

COMPRESS_PROMPT = """\
You compress a conversation between a grant-office assistant and an applicant into ONE
JSON object that will REPLACE the conversation. After this, the assistant will see only
this object - anything you leave out is gone for good.

Return exactly this shape and nothing else:
{
  "applicant_id": string or null - null if the conversation never established it,
  "topic": string - what the conversation is about, one line,
  "facts": [strings] - things the APPLICANT stated (name, id, documents sent, income band,
           family members, ...). Not things the assistant worked out.,
  "decisions": [strings] - what the assistant has concluded or told the applicant
               (eligibility status, amount quoted, documents still missing),
  "constraints": [strings] - conditions on how or when something can happen
                 (days they can come, deadlines, requirements they set),
  "open_questions": [strings] - things the applicant asked that were NOT answered yet,
  "language": string - the language(s) the applicant writes in
}

Rules:
- Keep every specific value verbatim: ids, numbers, amounts, document names, days of the week.
- A detail mentioned once is as important as one repeated; do not drop it for being minor.
- Nothing may be invented. A fact that was never said is not a fact.
- Arrays are empty [] rather than omitted."""


class Session:
    def __init__(self):
        self.turns: list[dict] = []  # user/assistant messages since the last compress
        self.state: dict | None = None
        self.log: list[dict] = []  # one entry per call: what was sent, what it cost

    def system_content(self) -> str:
        if self.state is None:
            return SYSTEM
        return (
            SYSTEM
            + "\n\nThe earlier part of this conversation was compressed. This saved state is "
            "everything you know about it:\n"
            + json.dumps(self.state, ensure_ascii=False, indent=2)
        )

    def messages(self) -> list[dict]:
        return [{"role": "system", "content": self.system_content()}] + self.turns

    def ask(self, text: str, remember: bool = True, label: str = "turn") -> str:
        msgs = self.messages() + [{"role": "user", "content": text}]
        reply, usage = chat(msgs)
        self.log.append(
            {"label": label, "kind": "turn", "sent_messages": len(msgs),
             "local_tokens": count_tokens(msgs), **usage}
        )
        if remember:
            self.turns += [{"role": "user", "content": text}, {"role": "assistant", "content": reply}]
        return reply

    def compress(self, label: str = "compress") -> tuple[bool, str]:
        """Summarise the conversation into a validated state. Returns (ok, message)."""
        transcript = []
        if self.state is not None:
            transcript.append("PREVIOUS SAVED STATE:\n" + json.dumps(self.state, ensure_ascii=False))
        for m in self.turns:
            who = "APPLICANT" if m["role"] == "user" else "ASSISTANT"
            transcript.append(f"{who}: {m['content']}")
        msgs = [
            {"role": "system", "content": COMPRESS_PROMPT},
            {"role": "user", "content": "Conversation to compress:\n\n" + "\n\n".join(transcript)},
        ]
        reply, usage = chat(msgs)
        self.log.append(
            {"label": label, "kind": "compress", "sent_messages": len(msgs),
             "local_tokens": count_tokens(msgs), **usage}
        )
        obj = parse_json(reply)
        if obj is None:
            return False, "summary did not parse as JSON - history KEPT, nothing replaced.\n" + reply
        errors = sorted(STATE_VALIDATOR.iter_errors(obj), key=str)
        if errors:
            msg = "; ".join(e.message for e in errors[:5])
            return False, f"summary failed the schema ({msg}) - history KEPT, nothing replaced."
        before = count_tokens(self.messages())
        self.state, self.turns = obj, []
        after = count_tokens(self.messages())
        return True, f"compressed: context {before} -> {after} tokens (local estimate)."


def probe_hit(reply: str, expect: list[str]) -> bool:
    obj = parse_json(reply)
    text = (obj.get("reason", "") + " " + json.dumps(obj, ensure_ascii=False)) if obj else reply
    return any(s.lower() in text.lower() for s in expect)


def run_script(compress: bool) -> dict:
    s = Session()
    calls = []  # one row per script position
    state_snapshot, compress_msg = None, None
    for i, turn in enumerate(SCRIPT["conversation"], start=1):
        if turn == COMPRESS_MARKER:
            if not compress:
                calls.append({"pos": i, "turn": turn, "skipped": True})
                continue
            ok, compress_msg = s.compress(label=f"pos {i}")
            print(f"  [{i:2}] <compress> -> {compress_msg}")
            state_snapshot = s.state if ok else None
            calls.append({"pos": i, "turn": turn, **s.log[-1], "ok": ok})
            continue
        reply = s.ask(turn, label=f"pos {i}")
        calls.append({"pos": i, "turn": turn, **s.log[-1], "reply": reply})
        print(f"  [{i:2}] sent {s.log[-1]['prompt_tokens']} tokens ({s.log[-1]['sent_messages']} msgs)")

    probes = []
    for p in SCRIPT["probes"]:
        # each probe is asked against the same end-of-conversation context, and
        # not remembered, so one probe's answer cannot leak into the next
        reply = s.ask(p["question"], remember=False, label=p["id"])
        hit = probe_hit(reply, p["expect_contains"])
        probes.append({**p, "reply": reply, "retrieved": hit, "prompt_tokens": s.log[-1]["prompt_tokens"]})
        print(f"  {p['id']}: {'retrieved' if hit else 'LOST'}")
    return {"calls": calls, "probes": probes, "state": state_snapshot, "compress_msg": compress_msg}


def reason_of(reply: str) -> str:
    obj = parse_json(reply)
    return obj.get("reason", reply) if obj else reply


def scripted():
    print("== Run A: never compressed")
    a = run_script(compress=False)
    print("== Run B: compressed at the <compress> turn")
    b = run_script(compress=True)
    save_output("medium_results.json", {"A": a, "B": b})

    def cell(c):
        if c.get("skipped"):
            return "— (skipped)"
        tag = " (compress call)" if c["turn"] == COMPRESS_MARKER else ""
        return f"{c['prompt_tokens']}{tag}"

    def tokens(run):
        return [c["prompt_tokens"] for c in run["calls"] if not c.get("skipped")]

    rows = [[c1["pos"], cell(c1), cell(c2)] for c1, c2 in zip(a["calls"], b["calls"])]
    def chat_tokens(run):
        return [c["prompt_tokens"] for c in run["calls"] if not c.get("skipped") and c["turn"] != COMPRESS_MARKER]

    rows.append(["**peak**", max(tokens(a)), max(tokens(b))])
    rows.append(["peak, conversation calls only", max(chat_tokens(a)), max(chat_tokens(b))])
    rows.append(["after the marker (calls 11–12)", sum(chat_tokens(a)[-2:]), sum(chat_tokens(b)[-2:])])
    rows.append(["**total for the run**", sum(tokens(a)), sum(tokens(b))])
    print("\n### Tokens per call (prompt tokens sent, as reported by the API)\n")
    print(md_table(["Call", "A — never compressed", "B — compressed at the `compress` turn"], rows))

    print("\n### Probes after the conversation\n")
    prow = []
    for pa, pb in zip(a["probes"], b["probes"]):
        prow.append([pa["id"], pa["tests"], "yes" if pa["retrieved"] else "**no**", reason_of(pa["reply"]),
                     "yes" if pb["retrieved"] else "**no**", reason_of(pb["reply"])])
    prow.append(["**retrieved**", "", f"{sum(p['retrieved'] for p in a['probes'])}/5", "",
                 f"{sum(p['retrieved'] for p in b['probes'])}/5", ""])
    print(md_table(["Probe", "Tests", "A retrieved?", "A answer", "B retrieved?", "B answer"], prow))
    print(f"\nProbe prompt tokens: A ≈ {a['probes'][0]['prompt_tokens']}, B ≈ {b['probes'][0]['prompt_tokens']}")

    print("\n### The state my compression produced\n")
    print(json.dumps(b["state"], ensure_ascii=False, indent=2) if b["state"] else f"(compression failed: {b['compress_msg']})")
    print("\nFull transcripts saved to outputs/medium_results.json")


def interactive():
    s = Session()
    print("Grant office chat. Commands: compress, tokens, state, history, quit")
    while True:
        try:
            text = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        cmd = text.lower()
        if cmd in ("quit", "exit"):
            break
        if cmd == "tokens":
            if not s.log:
                print("no calls yet")
            else:
                last = s.log[-1]
                print(f"last call ({last['kind']}): sent {last['prompt_tokens']} prompt tokens "
                      f"in {last['sent_messages']} messages, got {last['completion_tokens']} back")
            print(f"next call would send ≈ {count_tokens(s.messages())} tokens before your message "
                  f"({len(s.turns)} turns kept, state {'present' if s.state else 'absent'})")
            continue
        if cmd == "state":
            print(json.dumps(s.state, ensure_ascii=False, indent=2) if s.state else "no state yet")
            continue
        if cmd == "history":
            for m in s.turns:
                print(f"  {m['role']}: {m['content'][:120]}")
            continue
        if cmd == "compress":
            ok, msg = s.compress()
            print(("OK " if ok else "FAILED ") + msg)
            if ok:
                print(json.dumps(s.state, ensure_ascii=False, indent=2))
            continue
        reply = s.ask(text)
        print(f"office> {reason_of(reply)}")
        print(f"        [sent {s.log[-1]['prompt_tokens']} tokens; raw: {reply}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interactive", action="store_true")
    args = ap.parse_args()
    interactive() if args.interactive else scripted()


if __name__ == "__main__":
    main()
