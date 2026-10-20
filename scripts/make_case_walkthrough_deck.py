"""Write the slides of a deck that walks one case through the four strategies, question by question.

Each strategy gets a section slide, one slide per question it asked, and a slide for its stop
and diagnosis. Every question slide shows the strategy's flow diagram (the record viewer's
diagrams, re-laid out for a 1920 x 1080 slide) with the nodes and edges of that step in the
accent colour, and an In/Out card with what the step read and returned, taken from the run
record. The full question, answer and rationale go in the speaker notes.

The output is the `project/` folder of a deck made from the Claude Slides artifact type:
`project/slides/<id>.html` for every slide and `project/order.json` with the slide ids in deck
order (for `project/deck.json`, which is written by hand with the design system's record).

    python scripts/make_case_walkthrough_deck.py --record records/strategies_272_16it.json \
        --eval records/strategies_272_16it.eval.json --case PMC10625821_01 --out <deck folder>
"""

from __future__ import annotations

import argparse
import json
import re
from html import escape
from pathlib import Path

# Presentation Design tokens.
CANVAS, WARM, WHITE = "#F3F2EE", "#E5CABB", "#FFFFFF"
INK, MUTED, RULE, ACCENT = "#141413", "#5E5D59", "#DDDCD6", "#D97757"
TEAL_SOFT, GREY = "#B3DFE2", "#ECEDEE"
SERIF, SANS, COND = "'Newsreader', Georgia, serif", "'DM Sans', Arial, sans-serif", "'Barlow Condensed', 'DM Sans', Arial, sans-serif"

STRATEGIES = ["hypothesis", "knowledge", "channel", "sequence"]
TITLES = {"hypothesis": "1. Hypothesis-driven", "knowledge": "2. Knowledge-driven", "channel": "3. Channel-based", "sequence": "4. Sequence-based"}
SHORT = {"hypothesis": "Hypothesis-driven", "knowledge": "Knowledge-driven", "channel": "Channel-based", "sequence": "Sequence-based"}
PROMISE = {
    "hypothesis": "Ask what separates the leading diagnoses",
    "knowledge": "Ask what the clinical picture is missing",
    "channel": "Interview first, then examine if unsure",
    "sequence": "Open, narrow the list, then confirm",
}
SOURCE = {"case_study": "from the case study", "literature": "synthesized from the literature", "unanswerable": "unanswerable"}

# --- diagram geometry (host coordinates; the host is 1120 x 714 at the slide body's top left) ----

HOST_W, HOST_H = 1120, 714
C0, C1 = 470, 920
BOX = (160, 52)  # half width, half height
DEC = (170, 80)
PILL = (100, 40)
ENV_RIGHT = 180
Q_LABEL = ENV_RIGHT + 16


def loop_diagram(o, R=(80, 330, 580)):
    return {
        "env": (R[0] - 52, R[1] + 52),
        "nodes": {
            "ask": ("box", C0, R[0], o["ask"]),
            "upd": ("box", C0, R[1], o["upd"]),
            "stop": ("dec", C1, R[1], o["stop"]),
            "dx": ("box", C1, R[2], ("Final differential", "LLM · up to 10, ranked")),
            "end": ("pill", C0, R[2], ("Diagnosis", "")),
        },
        "edges": {
            "query": [(C0 - 160, R[0]), (ENV_RIGHT, R[0])],
            "answer": [(ENV_RIGHT, R[1]), (C0 - 160, R[1])],
            "toStop": [(C0 + 160, R[1]), (C1 - 170, R[1])],
            "no": [(C1, R[1] - 80), (C1, R[0]), (C0 + 160, R[0])],
            "yes": [(C1, R[1] + 80), (C1, R[2] - 52)],
            "toEnd": [(C1 - 160, R[2]), (C0 + 100, R[2])],
        },
        "labels": {
            "query": (Q_LABEL, R[0] - 42, "Query"),
            "answer": (Q_LABEL, R[1] - 42, "Answer"),
            "no": (C1 + 14, (R[0] + R[1] - 80) // 2 - 15, "no"),
            "yes": (C1 + 14, (R[1] + 80 + R[2] - 52) // 2 - 15, "yes"),
        },
    }


R = [70, 255, 440, 625]
DIAGRAMS = {
    "hypothesis": loop_diagram({
        "ask": ("Pick the question", "LLM · splits the top two"),
        "upd": ("Update differential", "LLM · probabilities"),
        "stop": ("Leader ≥ 80% and", "lead ≥ 30 points?"),
    }),
    "knowledge": loop_diagram({
        "ask": ("Ask what is missing", "LLM · names no diagnosis"),
        "upd": ("Recognise patterns", "LLM · findings → patterns"),
        "stop": ("A pattern with", "nothing missing?"),
    }),
    "channel": {
        "env": (R[0] - 52, R[1] + 52),
        "nodes": {
            "ask": ("box", C0, R[0], ("Ask in the channel", "LLM ×2 · ask, classify")),
            "more": ("dec", C0, R[1], ("Channel", "used up?")),
            "conf": ("box", C1, R[1], ("Diagnose and rate", "LLM · confidence")),
            "sure": ("dec", C1, R[2], ("Confident, or no", "channel left?")),
            "sw": ("box", C0, R[2], ("Switch channel", "Code · interview → exam")),
            "dx": ("box", C1, R[3], ("Final differential", "LLM · up to 10, ranked")),
            "end": ("pill", C0, R[3], ("Diagnosis", "")),
        },
        "edges": {
            "query": [(C0 - 160, R[0]), (ENV_RIGHT, R[0])],
            "answer": [(ENV_RIGHT, R[1]), (C0 - 170, R[1])],
            "no": [(C0, R[1] - 80), (C0, R[0] + 52)],
            "yes": [(C0 + 170, R[1]), (C1 - 160, R[1])],
            "toSure": [(C1, R[1] + 52), (C1, R[2] - 80)],
            "sureNo": [(C1 - 170, R[2]), (C0 + 160, R[2])],
            "back": [(C0 - 160, R[2]), (196, R[2]), (196, R[0] + 30), (C0 - 160, R[0] + 30)],
            "sureYes": [(C1 + 170, R[2]), (1106, R[2]), (1106, R[3]), (C1 + 160, R[3])],
            "toEnd": [(C1 - 160, R[3]), (C0 + 100, R[3])],
        },
        "labels": {
            "query": (Q_LABEL + 12, R[0] - 42, "Query"),
            "answer": (Q_LABEL + 12, R[1] - 42, "Answer"),
            "no": (C0 + 14, 132, "no"),
            "yes": (C0 + 184, R[1] - 42, "yes"),
            "sureNo": (C0 + 174, R[2] - 42, "no"),
            "back": (208, 330, "ask"),
            "sureYes": (1046, 530, "yes"),
        },
    },
    "sequence": {
        "env": (R[0] - 52, R[2] + 52),
        "nodes": {
            "open": ("box", C0, R[0], ("Opening questions", "Phase 1 · LLM")),
            "draft": ("box", C1, R[0], ("Draft differential", "Phase 1 · LLM · up to 5")),
            "refine": ("box", C0, R[1], ("Ask, then prune", "Phase 2 · LLM ×2")),
            "confirm": ("box", C0, R[2], ("Test the leader", "Phase 3 · LLM ×2")),
            "dx": ("box", C1, R[2], ("Final differential", "LLM · up to 10, ranked")),
            "end": ("pill", C1, R[3], ("Diagnosis", "")),
        },
        "edges": {
            **{f"q{i}": [(C0 - 160, R[i] - 14), (ENV_RIGHT, R[i] - 14)] for i in range(3)},
            **{f"a{i}": [(ENV_RIGHT, R[i] + 14), (C0 - 160, R[i] + 14)] for i in range(3)},
            "toDraft": [(C0 + 160, R[0]), (C1 - 160, R[0])],
            "toRefine": [(C1, R[0] + 52), (C1, R[1]), (C0 + 160, R[1])],
            "toFinal": [(C0, R[1] + 52), (C0, R[2] - 52)],
            "toDx": [(C0 + 160, R[2]), (C1 - 160, R[2])],
            "toEnd": [(C1, R[2] + 52), (C1, R[3] - 40)],
        },
        "labels": {
            "q0": (Q_LABEL, R[0] - 56, "Query"),
            "a0": (Q_LABEL, R[0] + 22, "Answer"),
            "toDraft": (C0 + 176, R[0] - 42, "after 4"),
            "toRefine": (C1 + 14, 150, "list ready"),
            "toFinal": (C0 + 14, 330, "≤ 2 left or 12 asked"),
            "toDx": (C0 + 176, R[2] - 42, "settled"),
        },
    },
}


def svg(d, nodes_on, edges_on):
    """The diagram's lines and diamonds; boxes and text are slide elements over it."""
    parts = [
        f'<svg aria-label="Flow diagram" style="position:absolute;left:0px;top:0px" width="{HOST_W}" height="{HOST_H}" viewBox="0 0 {HOST_W} {HOST_H}">',
        "<defs>",
        f'<marker id="hi" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="16" markerHeight="16" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,1 L10,5 L0,9 Z" fill="{INK}"/></marker>',
        f'<marker id="ha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="22" markerHeight="22" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,1 L10,5 L0,9 Z" fill="{ACCENT}"/></marker>',
        "</defs>",
    ]
    # Inactive edges first, so the lit path paints over the ones it crosses.
    for on in (False, True):
        for eid, pts in d["edges"].items():
            if (eid in edges_on) != on:
                continue
            color, width, head = (ACCENT, 6, "ha") if on else (INK, 2.5, "hi")
            p = " ".join(f"{x},{y}" for x, y in pts)
            parts.append(f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round" marker-end="url(#{head})"/>')
    for nid, (kind, x, y, _) in d["nodes"].items():
        if kind != "dec":
            continue
        fill = ACCENT if nid in nodes_on else WHITE
        hw, hh = DEC
        parts.append(f'<polygon points="{x - hw},{y} {x},{y - hh} {x + hw},{y} {x},{y + hh}" fill="{fill}" stroke="{INK}" stroke-width="{3 if nid in nodes_on else 2.5}" stroke-linejoin="round"/>')
    parts.append("</svg>")
    return "".join(parts)


def p(text, style):
    return f'<p style="{style}">{escape(text)}</p>'


def diagram_host(name, nodes_on, edges_on):
    d = DIAGRAMS[name]
    top, bottom = d["env"]
    out = [f'<div style="position:relative;width:{HOST_W}px;height:{HOST_H}px;flex:none">', svg(d, nodes_on, edges_on)]
    out.append(
        f'<div style="position:absolute;left:0px;top:{top}px;width:{ENV_RIGHT}px;height:{bottom - top}px;background:{GREY};border:3px dashed {INK};border-radius:24px;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:8px">'
        + p("Simulated environment", f"font-size:24px;font-weight:500;line-height:30px;text-align:center;color:{INK}")
        + "</div>"
    )
    for nid, (kind, x, y, (title, sub)) in d["nodes"].items():
        on = nid in nodes_on
        if kind == "dec":
            hw, hh = DEC
            out.append(p(f"{title}\n{sub}", "").replace("\n", "<br>").replace(
                '<p style="">',
                f'<p style="position:absolute;left:{x - 130}px;top:{y - 34}px;width:260px;height:68px;font-size:24px;font-weight:500;line-height:34px;text-align:center;color:{INK}">',
            ))
            continue
        if kind == "pill":
            hw, hh = PILL
            bg, fg = (ACCENT, INK) if on else (INK, WHITE)
            out.append(
                f'<div style="position:absolute;left:{x - hw}px;top:{y - hh}px;width:{2 * hw}px;height:{2 * hh}px;background:{bg};border:3px solid {INK};border-radius:40px;display:flex;flex-direction:column;justify-content:center;align-items:center">'
                + p(title, f"font-size:28px;font-weight:500;line-height:34px;text-align:center;color:{fg}")
                + "</div>"
            )
            continue
        hw, hh = BOX
        llm = sub.startswith("LLM") or " LLM" in sub
        bg = ACCENT if on else (TEAL_SOFT if llm else WHITE)
        out.append(
            f'<div style="position:absolute;left:{x - hw}px;top:{y - hh}px;width:{2 * hw}px;height:{2 * hh}px;background:{bg};border:3px solid {INK};border-radius:24px;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:2px">'
            + p(title, f"font-size:28px;font-weight:500;line-height:34px;text-align:center;color:{INK}")
            + p(sub, f"font-size:24px;line-height:30px;text-align:center;color:{INK if on else MUTED}")
            + "</div>"
        )
    for eid, (x, y, text) in d["labels"].items():
        on = eid in edges_on
        out.append(p(text, f"position:absolute;left:{x}px;top:{y}px;width:{max(60, 15 * len(text))}px;font-size:24px;font-weight:{700 if on else 400};line-height:30px;color:{INK if on else MUTED}"))
    out.append("</div>")
    return "".join(out)


# --- text ---------------------------------------------------------------------------------------


def pct(x):
    return f"{round(100 * (x or 0))}%"


def plain(name):
    """A diagnosis name without its parenthetical asides."""
    return " ".join(re.sub(r"\s*\([^)]*\)", "", name or "").split()) or (name or "")


def cut(text, n):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def card(sections):
    """sections: [(label, [lines], emphasis)]"""
    out = [f'<div style="flex:1;align-self:stretch;display:flex;flex-direction:column;gap:16px;background:{WHITE};border:3px solid {INK};border-radius:24px;padding:28px 36px">']
    for label, lines, strong in sections:
        block = [p(label, f"font-size:24px;font-weight:700;line-height:30px;color:{MUTED}")]
        for line in lines:
            block.append(p(line, f"font-size:24px;font-weight:{500 if strong else 400};line-height:32px;color:{INK}"))
        out.append('<div style="display:flex;flex-direction:column;gap:6px">' + "".join(block) + "</div>")
    out.append("</div>")
    return "".join(out)


def slide(sid, title, description, body, notes):
    return (
        f'<section id="{sid}" data-transition="fade" style="background:{CANVAS};color:{INK};font-family:{SANS};padding:96px;display:flex;flex-direction:column;gap:40px">'
        '<div style="display:flex;flex-direction:column;gap:24px">'
        + p(title, f"font-family:{SERIF};font-size:56px;font-weight:500;line-height:64px")
            .replace("<p ", "<h2 ").replace("</p>", "</h2>")
        + p(description, f"font-size:36px;line-height:46px;color:{MUTED}")
        + "</div>"
        + body
        + f"<aside>{escape(cut(notes, 3990))}</aside></section>"
    )


CARD_LINE = 36  # characters per 24px line inside the card, estimated on the safe side


def card_height(sections):
    lines = sum(-(-len(line) // CARD_LINE) for _, ls, _ in sections for line in ls)
    return 2 * 28 + 6 + len(sections) * 36 + lines * 32 + 16 * (len(sections) - 1)


def fit(sections):
    """Shorten the quoted question and answer, then drop the optional notes, until the card fits."""
    optional = ("Fills", "Separates", "Changed")

    def shorten(secs, limit):
        return [(lab, [f"“{cut(l.strip('“”'), limit)}”" if l.startswith("“") else l for l in ls], st) for lab, ls, st in secs]

    sections = list(sections)
    for limit in (150, 130, 110):
        if card_height(sections) <= HOST_H:
            return sections
        sections = shorten(sections, limit)
    if card_height(sections) > HOST_H:
        sections = [x for x in sections if x[0] not in optional]
    for limit in (90, 70):
        if card_height(sections) <= HOST_H:
            break
        sections = shorten(sections, limit)
    return sections


def step_slide(sid, name, title, description, nodes_on, edges_on, sections, notes):
    sections = fit(sections)
    body = '<div style="display:flex;flex-direction:row;gap:32px;align-items:start">' + diagram_host(name, nodes_on, edges_on) + card(sections) + "</div>"
    return slide(sid, title, description, body, notes)


def qa_sections(it, i, q_chars=150, a_chars=170):
    return [
        (f"Out · question {i}", [f"“{cut(it['question'], q_chars)}”"], False),
        (f"Answer · {SOURCE.get(it['answer_source'], 'from the environment')}", [f"“{cut(it['answer'], a_chars)}”"] if it.get("answer") else ["No answer."], False),
    ]


def qa_notes(it, i):
    why = f" Why: {it['rationale']}" if it.get("rationale") else ""
    return f"Question {i}: {it['question']}{why} Answer ({SOURCE.get(it['answer_source'], 'environment')}): {it.get('answer')}"


def final_list(run, n=3):
    return [f"{i + 1}. {cut(plain(x['name']), 36)} ({pct(x['probability'])})" for i, x in enumerate(run["diagnosis"]["differential"][:n])]


def truth_line(run, ev):
    rank = ev.get("rank")
    truth = run["case"]["diagnosis"]
    if rank:
        named = run["diagnosis"]["differential"][rank - 1]["name"]
        same = named.lower() == truth.lower()
        return f"{truth}: named at rank {rank}" + ("" if same else f" (as “{named}”)")
    return f"{truth}: not in the top 10"


# --- one strategy's slides ----------------------------------------------------------------------


def hypothesis_slides(run, ev, params, kind):
    name = kind
    its = run["iterations"]
    n = len(its)
    accept, margin = params.get("accept", 0.8), params.get("margin", 0.3)
    out = []

    def diff_lines(diff):
        return [f"{pct(h['probability'])} {cut(plain(h['diagnosis']), 38)}" for h in (diff or [])[:3]] or ["None yet."]

    def lead(diff):
        top = diff[0]["probability"] if diff else 0
        second = diff[1]["probability"] if len(diff) > 1 else 0
        return top, top - second

    def pic_lines(pic):
        pats = (pic or {}).get("patterns", [])
        if not pats:
            return ["Nothing known yet."]
        lines = [f"{len(pic.get('findings', []))} findings; {len(pats)} pattern{'s' if len(pats) != 1 else ''}:"]
        for pt in pats[:2]:
            lines.append(f"{cut(pt['name'], 30)}: {len(pt.get('missing', []))} missing")
        return lines

    for i, it in enumerate(its, 1):
        tr = it.get("strategy_trace") or {}
        sid = f"{kind[:3]}-q{i:02d}"
        title = f"{TITLES[kind]} · question {i}"
        if kind == "hypothesis":
            state = tr.get("differential") or []
            if i == 1:
                desc, nodes, edges = "No differential yet: ask for the complaint.", ["ask"], ["query", "answer"]
                sections = [("In", ["The case; the diagnosis is hidden.", "Differential: none yet."], False)]
            else:
                top, gap = lead(state)
                desc = f"Leader at {pct(top)}, {round(100 * gap)} points ahead: ask again."
                nodes, edges = ["upd", "stop", "ask"], ["toStop", "no", "query", "answer"]
                sections = [
                    (f"In · differential after answer {i - 1}", diff_lines(state), False),
                    ("Stop rule", [f"Leader {pct(top)}, lead {round(100 * gap)} points: no."], False),
                ]
            if tr.get("separates"):
                sections.append(("Separates", [cut(" vs ".join(plain(x) for x in tr["separates"]), 90)], False))
        else:
            pic = tr.get("picture") or {}
            if i == 1:
                desc, nodes, edges = "Nothing known yet: ask for the complaint.", ["ask"], ["query", "answer"]
                sections = [("In", ["The case; the diagnosis is hidden.", "Clinical picture: empty."], False)]
            else:
                done = [pt for pt in pic.get("patterns", []) if pt.get("present") and not pt.get("missing")]
                desc = "No complete pattern yet: ask what is missing." if not done else "Basics not yet covered: keep asking."
                nodes, edges = ["upd", "stop", "ask"], ["toStop", "no", "query", "answer"]
                sections = [
                    (f"In · picture after answer {i - 1}", pic_lines(pic), False),
                    ("Stop rule", [f"{len(done)} complete; basics {'covered' if pic.get('basics_covered') else 'not covered'}: no."], False),
                ]
            if tr.get("fills"):
                sections.append(("Fills", [cut(tr["fills"], 80)], False))
        sections += qa_sections(it, i, 130 if len(sections) > 2 else 150)
        out.append((sid, step_slide(sid, kind, title, desc, nodes, edges, sections, qa_notes(it, i))))

    # Stop and diagnosis.
    trace = run["diagnosis"].get("trace") or {}
    if kind == "hypothesis":
        diff = trace.get("differential") or []
        top, gap = lead(diff)
        desc = f"Leader at {pct(top)}, {round(100 * gap)} points ahead: stop."
        sections = [
            (f"In · differential after answer {n}", diff_lines(diff), False),
            ("Stop rule", [f"Leader ≥ {pct(accept)} and lead ≥ {round(100 * margin)} points: yes."], False),
        ]
        notes = f"After answer {n} the leader reached {pct(top)}, {round(100 * gap)} points ahead of the runner-up, which meets the stop rule (at least {pct(accept)} and ahead by at least {round(100 * margin)} points)."
    else:
        pic = trace.get("picture") or {}
        done = [pt for pt in pic.get("patterns", []) if pt.get("present") and not pt.get("missing")]
        desc = "A pattern is complete and basics covered: stop."
        sections = [
            (f"In · picture after answer {n}", pic_lines(pic), False),
            ("Stop rule", [f"Complete: {cut(done[0]['name'], 40)}." if done else "Complete pattern found.", "Basics covered: yes."], False),
        ]
        notes = f"After answer {n} the pattern '{done[0]['name'] if done else ''}' had nothing missing and the basics were covered, so the strategy stopped."
    sections += [("Out · final differential", final_list(run), True), ("True diagnosis", [truth_line(run, ev)], True)]
    sid = f"{kind[:3]}-stop"
    out.append((sid, step_slide(sid, kind, f"{TITLES[kind]} · stop and diagnose", desc, ["upd", "stop", "dx", "end"], ["toStop", "yes", "toEnd"], sections, notes + " Final differential: " + "; ".join(f"{x['name']} {pct(x['probability'])}" for x in run["diagnosis"]["differential"]))))
    return out


def channel_slides(run, ev, params, max_iter):
    its = run["iterations"]
    channels = params.get("channels") or ["interview", "exam"]
    cap = params.get("questions_per_channel") or max(1, (max_iter or 2 * len(channels)) // len(channels))
    confident = params.get("confident", 0.8)
    out, asked = [], 0
    for i, it in enumerate(its, 1):
        tr = it.get("strategy_trace") or {}
        prev = (its[i - 2].get("strategy_trace") or {}) if i > 1 else None
        ch = tr.get("channel")
        sid = f"cha-q{i:02d}"
        if prev and prev.get("channel") != ch:
            a = (tr.get("assessments") or [{}])[-1]
            nodes, edges = ["more", "conf", "sure", "sw", "ask"], ["yes", "toSure", "sureNo", "back", "query", "answer"]
            desc = f"{prev['channel'].capitalize()} used up, {pct(a.get('confidence'))} sure: switch to {ch}."
            sections = [
                ("In · channel check", [f"{asked} of {cap} {prev['channel']} questions asked: used up."], False),
                ("Diagnose and rate", [f"{cut(plain(a.get('diagnosis', '')), 34)}: {pct(a.get('confidence'))} (needs {pct(confident)})."], False),
            ]
            asked = 0
        elif i == 1:
            nodes, edges = ["ask"], ["query", "answer"]
            desc = f"Start in the {ch} channel: question 1 of {cap}."
            sections = [("In", ["The case; the diagnosis is hidden.", f"Channel: {ch}, 0 of {cap} asked."], False)]
        else:
            nodes, edges = ["more", "ask"], ["no", "query", "answer"]
            desc = f"{ch.capitalize()} channel, question {asked + 1} of {cap}: keep asking."
            sections = [("In · channel check", [f"{asked} of {cap} {ch} questions asked: not used up."], False)]
        rejected = tr.get("rejected") or []
        if rejected:
            sections.append(("Rejected by the classifier", [f"{len(rejected)} question{'s' if len(rejected) != 1 else ''} outside the channel"], False))
        asked += 1
        sections += qa_sections(it, i)
        out.append((sid, step_slide(sid, "channel", f"{TITLES['channel']} · question {i}", desc, nodes, edges, sections, qa_notes(it, i))))

    trace = run["diagnosis"].get("trace") or {}
    a = (trace.get("assessments") or [{}])[-1]
    last = (its[-1].get("strategy_trace") or {}).get("channel")
    sure = (a.get("confidence") or 0) >= confident
    desc = f"{last.capitalize()} used up; {pct(a.get('confidence'))} confident: stop."
    sections = [
        ("In · channel check", [f"{asked} of {cap} {last} questions asked: used up."], False),
        ("Diagnose and rate", [f"{cut(plain(a.get('diagnosis', '')), 40)}: {pct(a.get('confidence'))}."], False),
        ("Confident?", [f"{pct(a.get('confidence'))} ≥ {pct(confident)}: yes; the exam channel is never opened." if sure else "No channel left: stop."], False),
        ("Out · final differential", final_list(run), True),
        ("True diagnosis", [truth_line(run, ev)], True),
    ]
    notes = f"After {asked} {last} questions the channel was used up. The assessment was {a.get('diagnosis')} at {pct(a.get('confidence'))} confidence, at or above the {pct(confident)} threshold, so the strategy stopped without examining. Final differential: " + "; ".join(f"{x['name']} {pct(x['probability'])}" for x in run["diagnosis"]["differential"])
    out.append(("cha-stop", step_slide("cha-stop", "channel", f"{TITLES['channel']} · stop and diagnose", desc, ["more", "conf", "sure", "dx", "end"], ["yes", "toSure", "sureYes", "toEnd"], sections, notes)))
    return out


def sequence_slides(run, ev, params, max_iter):
    its = run["iterations"]
    budget = max(3, max_iter or params.get("budget", 8))
    opening = max(1, round(params.get("opening_share", 0.25) * budget))
    final_from = budget - max(1, round(params.get("final_share", 0.25) * budget))
    row = {"init": 0, "refine": 1, "final": 2}
    node = {"init": "open", "refine": "refine", "final": "confirm"}
    out = []

    def cands(lst, n=5):
        return [f"{k + 1}. {cut(plain(c), 40)}" for k, c in enumerate((lst or [])[:n])] or ["None yet."]

    for i, it in enumerate(its, 1):
        tr = it.get("strategy_trace") or {}
        prev = (its[i - 2].get("strategy_trace") or {}) if i > 1 else {}
        ph = tr.get("phase", "init")
        r = row[ph]
        nodes, edges = [node[ph]], [f"q{r}", f"a{r}"]
        sid = f"seq-q{i:02d}"
        if ph == "init":
            desc = f"Phase 1: opening question {i} of {opening}."
            sections = [("In", ["The case; the diagnosis is hidden." if i == 1 else f"{i - 1} answers so far.", "No candidate list yet."], False)]
        elif prev.get("phase") == "init":
            nodes, edges = ["draft", "refine"], ["toDraft", "toRefine", "q1", "a1"]
            desc = f"Draft {len(tr.get('candidates', []))} candidates, then start narrowing."
            sections = [(f"Draft after answer {i - 1}", cands(tr.get("candidates")), False)]
        elif ph == "refine":
            desc = f"Phase 2: {len(tr.get('candidates', []))} candidates left; question {i} of {final_from}."
            before, after = prev.get("candidates") or [], tr.get("candidates") or []
            sections = [(f"In · pruned after answer {i - 1}", cands(after), False)]
            dropped = [c for c in before if c not in after]
            added = [c for c in after if c not in before]
            if dropped or added:
                sections.append(("Changed", [cut("; ".join([f"− {c}" for c in dropped] + [f"+ {c}" for c in added]), 110)], False))
        else:
            nodes, edges = ["confirm"], (["toFinal"] if prev.get("phase") != "final" else []) + ["q2", "a2"]
            lst = tr.get("candidates") or []
            why = f"{i - 1} of {budget} asked" if len(lst) > params.get("narrow_to", 2) else f"{len(lst)} left"
            desc = f"Phase 3 ({why}): test the leader."
            sections = [("In · candidates", cands(lst, 4), False)]
        sections += qa_sections(it, i, 130 if ph != "init" else 150, 150 if ph != "init" else 170)
        out.append((sid, step_slide(sid, "sequence", f"{TITLES['sequence']} · question {i}", desc, nodes, edges, sections, qa_notes(it, i))))

    v = (run["diagnosis"].get("trace") or {}).get("verdict") or {}
    desc = f"{cut(v.get('diagnosis', 'The leader'), 30)} is settled: stop."
    sections = [
        (f"Settle? · after answer {len(its)}", [f"{v.get('diagnosis')}: {'settled' if v.get('settled') else 'still open'}."], False),
        ("Out · final differential", final_list(run), True),
        ("True diagnosis", [truth_line(run, ev)], True),
    ]
    notes = f"The settle check judged {v.get('diagnosis')} settled after {len(its)} questions. Final differential: " + "; ".join(f"{x['name']} {pct(x['probability'])}" for x in run["diagnosis"]["differential"])
    out.append(("seq-stop", step_slide("seq-stop", "sequence", f"{TITLES['sequence']} · stop and diagnose", desc, ["confirm", "dx", "end"], ["toDx", "toEnd"], sections, notes)))
    return out


# --- the other slides ---------------------------------------------------------------------------


def title_slide(sid, title, subtitle, notes=""):
    aside = f"<aside>{escape(notes)}</aside>" if notes else ""
    return (
        f'<section id="{sid}" data-transition="fade" style="background:{WARM};color:{INK};font-family:{SANS};padding:96px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:24px">'
        + p(title, f"font-family:{SERIF};font-size:96px;font-weight:500;line-height:104px;text-align:center;width:1500px").replace("<p ", "<h1 ").replace("</p>", "</h1>")
        + p(subtitle, f"font-family:{SERIF};font-size:52px;font-weight:400;line-height:64px;text-align:center;width:1500px")
        + aside
        + "</section>"
    )


def case_slide(run0, max_iter, models):
    case = run0["case"]
    callout = lambda fig, label: (
        f'<div style="flex:1;display:flex;flex-direction:column;gap:8px;background:{WHITE};border:3px solid {INK};border-radius:24px;padding:32px">'
        + p(fig, f"font-family:{COND};font-size:72px;font-weight:700;line-height:72px")
        + p(label, f"font-size:28px;font-weight:500;line-height:34px;color:{MUTED}")
        + "</div>"
    )
    body = (
        '<div style="display:flex;flex-direction:column;gap:32px">'
        f'<div style="background:{WHITE};border:3px solid {INK};border-radius:24px;padding:40px 48px;display:flex;flex-direction:column;gap:16px">'
        + p("What the strategies see first", f"font-size:28px;font-weight:500;line-height:34px;color:{MUTED}")
        + p("“The patient presented with painless swelling in the left submandibular region, which had enlarged over the preceding 3 months.”", "font-size:36px;line-height:48px")
        + "</div>"
        '<div style="display:flex;flex-direction:row;gap:24px">'
        + callout(str(max_iter), "questions at most")
        + callout("Haiku 5.5", "asks (strategy model)")
        + callout("GPT-6 Luna", "answers (environment)")
        + callout("Hidden", f"true diagnosis: {case['diagnosis'].lower()}")
        + "</div></div>"
    )
    notes = (f"Case {run0['case_id']}, from the 16-question run of the 272-case experiment. The full case: {case['narrative']} "
             f"Each strategy starts from nothing and asks one question at a time; the environment answers from the case study or, when the case is silent, synthesizes an answer from the literature. Models: {models}.")
    return slide("case", "The case: a painless neck swelling", "One case from the 16-question run; four strategies.", body, notes)


def closing_slide(runs, evs):
    head = ["Strategy", "Questions", "Their first diagnosis", "True rank", "Cost"]
    widths = [24, 13, 39, 12, 12]
    rows = [f'<div style="display:flex;flex-direction:row;border-bottom:2px solid {INK};padding:10px 0px">' + "".join(
        p(h, f"width:{w}%;font-size:28px;font-weight:500;line-height:34px" + (";text-align:right" if k in (1, 3, 4) else "")) for k, (h, w) in enumerate(zip(head, widths))) + "</div>"]
    for s in STRATEGIES:
        r, e = runs[s], evs[s]
        top = r["diagnosis"]["differential"][0]
        miss = (e.get("rank") or 99) > 1
        cells = [SHORT[s], str(len(r["iterations"])), f"{cut(plain(top['name']), 30)} ({pct(top['probability'])})",
                 str(e["rank"]) if e.get("rank") else "—", f"${r['strategy_cost_usd'] + r['environment_cost_usd']:.3f}"]
        bg = f";background:{ACCENT}" if miss else ""
        rows.append(f'<div style="display:flex;flex-direction:row;border-bottom:2px solid {RULE};padding:16px 0px{bg}">' + "".join(
            p(c, f"width:{w}%;font-size:32px;line-height:44px" + (";text-align:right" if k in (1, 3, 4) else "") + (";font-weight:700" if miss else "")) for k, (c, w) in enumerate(zip(cells, widths))) + "</div>")
    body = '<div style="display:flex;flex-direction:column;font-variant-numeric:tabular-nums">' + "".join(rows) + "</div>" + p(
        "Every strategy stopped by its own rule, before the 16-question limit. Cost: strategy and environment calls for this case.", f"font-size:24px;line-height:32px;color:{MUTED}")
    notes = ("Three strategies named plunging ranula first. Hypothesis-driven got there in six questions by asking for the biopsy once lymphoma and metastasis had stalled. "
             "Knowledge-driven took fourteen and stopped when a pattern was complete. Channel-based never left the interview: the history of an earlier aspiration was enough for 85 percent confidence. "
             "Sequence-based committed early to a candidate list without ranula; ranula re-entered as 'plunging ranula or submandibular duct cyst' but was dropped before the final phase, and the egg-white fluid did not bring it back.")
    sec = (f'<section id="takeaway" data-transition="fade" style="background:{WHITE};color:{INK};font-family:{SANS};padding:96px;display:flex;flex-direction:column;gap:40px">'
           '<div style="display:flex;flex-direction:column;gap:24px">'
           + p("Same case, four routes: three named it first", f"font-family:{SERIF};font-size:56px;font-weight:500;line-height:64px").replace("<p ", "<h2 ").replace("</p>", "</h2>")
           + p("Sequence-based narrowed too early and missed it.", f"font-size:36px;line-height:46px;color:{MUTED}")
           + "</div>" + body + f"<aside>{escape(notes)}</aside></section>")
    return sec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--eval", required=True)
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", required=True, help="the deck folder; slides go in <out>/project/slides")
    ap.add_argument("--overview-src", required=True, help="the uploaded overview image's /_blob/<id> url")
    args = ap.parse_args()

    record = json.loads(Path(args.record).read_text())
    ev = json.loads(Path(args.eval).read_text())
    runs = {c["strategy"]: c for c in record["case_runs"] if c["case_id"] == args.case and c["strategy"] in STRATEGIES}
    evs = {c["strategy"]: c for c in ev["case_runs"] if c["case_id"] == args.case and c["strategy"] in STRATEGIES}
    max_iter = record["config"]["stopping"]["max_iterations"]
    params = {s: record["strategies"][s]["params"] for s in STRATEGIES}

    slides = [
        ("title", title_slide("title", "Information Collection Strategies Experiment", "One case, question by question, four strategies",
                              "We follow one case from the 16-question run through each of the four information collection strategies, one question per slide.")),
        ("research-question", title_slide("research-question", "Research Question", "What is the most accurate information collection strategy for a computer-based diagnostic system?")),
        ("overview", slide("overview", "Overview", "", f'<img src="{args.overview_src}" alt="An information collection strategy sends queries to an LLM inside a simulated environment. The LLM consults the case study and the literature, and returns answers." style="width:1728px;height:776px;object-fit:contain">',
                           "The strategy under test asks questions. The simulated environment answers them from the case study and, when the case does not say, from the literature. The rest of the deck opens the strategy box: each strategy's flow, lit one step at a time.")
         .replace(f'<p style="font-size:36px;line-height:46px;color:{MUTED}"></p>', "")),
        ("case", case_slide(runs["hypothesis"], max_iter, "strategy anthropic/claude-haiku-5.5, environment openai/gpt-6-luna")),
    ]
    for s in STRATEGIES:
        r, e = runs[s], evs[s]
        slides.append((f"{s[:3]}-section", title_slide(f"{s[:3]}-section", TITLES[s], PROMISE[s], record["strategies"][s]["description"])))
        if s in ("hypothesis", "knowledge"):
            slides += hypothesis_slides(r, e, params[s], s)
        elif s == "channel":
            slides += channel_slides(r, e, params[s], max_iter)
        else:
            slides += sequence_slides(r, e, params[s], max_iter)
    slides.append(("takeaway", closing_slide(runs, evs)))

    folder = Path(args.out) / "project" / "slides"
    folder.mkdir(parents=True, exist_ok=True)
    for sid, html in slides:
        (folder / f"{sid}.html").write_text(html + "\n")
    (Path(args.out) / "project" / "order.json").write_text(json.dumps([sid for sid, _ in slides]))
    print(len(slides), "slides;", "largest", max(len(h) for _, h in slides), "bytes")


if __name__ == "__main__":
    main()
