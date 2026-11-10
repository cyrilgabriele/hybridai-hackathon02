"""Passenger chat, live workflow graph and customer-service desk."""

from __future__ import annotations

import html
import json
import threading

import gradio as gr

from pipeline.assistant import Assistant
from pipeline.slots import REQUIRED
from pipeline.state import Conversation, Step

EXAMPLES = [
    "On 7 November I took the 13:29 train from Zürich HB to Oensingen and it never came. Do I get money back?",
    "I travelled from Rotkreuz to Zürich HB on 7 November 2026 at 20:48. Am I owed anything?",
    "On 7 November I was going from St. Gallen to Zürich HB at 8 o'clock. I had a delay. Do I get a refund?",
    "Ich war am 7. November unterwegs und hatte Verspätung.",
    "On 7 November I took the 06:14 from Basel Bad Bf to Basel SBB. Do I get a refund?",
    "On 8 November I went from Bern to Zürich HB at 12:00. Do I get a refund?",
    "From Zürich to Bern on 7 November 2026 at 17:30, big delay!",
]
WAITING = "Checking the SBB data. This can take about 20 seconds."
HEADERS = ["Pattern", "Who", "Step", "What crossed the boundary", "Status", "Seconds"]
LEGEND = """**Patterns.** **P3 Translator:** words become a checked request, the rules' decision becomes words. \
**P1 Sensor:** every slot carries the passenger's quote and the host checks it. \
**P6 Critique and Repair:** failed checks go back to the model with a fixed reason. \
**P12 Model Selects, Rules Write:** the model writes words around values it never sees. \
**P7 Division by Competence:** the rules decide what they cover; a person decides the rest."""

# The pipeline as a node graph. Each node: caption, input port, output port, grid cell.
NODES = {
    "passenger": ("Passenger: message", ("", ""), ("message", "text"), (0, 0)),
    "slots": ("1 Model: slots (P3+P1)", ("message", "json"), ("slots", "json"), (1, 0)),
    "check": ("2 Host: quote check (P1+P6)", ("slots", "json"), ("accepted", "json"), (2, 0)),
    "trains": ("3 Rules+KB: trains (P3)", ("RefundCase", "frame"), ("trains", "list"), (3, 0)),
    "pick": ("4 Model: pick train (P12)", ("trains", "json"), ("train_id", "text"), (0, 1)),
    "decide": ("5 Rules+KB: decide (P3+P7)", ("DelayCheck", "frame"), ("decision", "text"), (1, 1)),
    "reply": ("6 Model: reply (P12+P6)", ("decision", "json"), ("words", "text"), (2, 1)),
    "out": ("Reply to passenger", ("reply", "text"), ("", ""), (3, 1)),
    "handoff": ("7 Hand-off: SBB staff (P7)", ("case + note", "json"), ("decision", "text"), (2, 2)),
}
# Every path the pipeline can take; drawn faint until a turn uses it.
EDGES = (("passenger", "slots"), ("slots", "check"), ("check", "trains"), ("trains", "reply"), ("passenger", "pick"),
         ("pick", "decide"), ("decide", "reply"), ("reply", "out"), ("decide", "handoff"), ("handoff", "reply"),
         ("check", "reply"), ("handoff", "out"))
# Which node a step belongs to (title prefix).
NODE_OF = (
    ("Passenger wrote", "passenger"), ("Chose a station", "passenger"), ("Picked a train", "pick"),
    ("Translate the passenger", "slots"), ("Check quotes and values", "check"),
    ("Assert RefundCase", "trains"), ("Planned connections", "trains"), ("Select an identifier", "pick"),
    ("Assert DelayCheck", "decide"), ("Delay and policy", "decide"),
    ("Assess the open case", "handoff"), ("Handed on", "handoff"), ("Officer decided", "handoff"),
    ("Phrase the outcome", "reply"), ("Phrasing call failed", "reply"), ("Check words", "reply"),
    ("Reply refused", "reply"), ("Fixed wording used", "reply"),
)
NODE_W, NODE_H, COL, ROW, PAD = 214, 136, 252, 226, 22
WIDTH, HEIGHT = PAD * 2 + COL * 3 + NODE_W, PAD + 26 + ROW * 2 + NODE_H + 20
IN_Y, OUT_Y = 60, NODE_H - 18
WORKING = {"slots": "GPT-5 mini is reading", "pick": "GPT-5 mini is picking", "reply": "GPT-5 mini is phrasing",
           "trains": "FrameX is reasoning", "decide": "FrameX is reasoning", "handoff": "preparing the hand-off"}


def _node_of(step: Step, stage: str) -> str | None:
    if step.title.startswith("Model call failed"):  # only the slot and train-pick calls let a failure through
        return "pick" if stage == "choose_train" else "slots"
    return next((node for prefix, node in NODE_OF if step.title.startswith(prefix)), None)


def _current_turn(trace: list[Step]) -> tuple[int, list[Step]]:
    """The turn number and its steps: everything since the passenger last wrote."""
    starts = [i for i, step in enumerate(trace) if step.title == "Passenger wrote"]
    return len(starts), trace[starts[-1]:] if starts else []


def _path(steps: list[Step], running: bool, stage: str) -> list[tuple[str, str]]:
    """The edges this turn used, in order. A staff decision arrives after the reply went out."""
    edges, last = [], None
    for step in steps:
        node = _node_of(step, stage)
        if step.title.startswith("Officer decided"):
            edges.append(("handoff", "out"))
            last = None
            continue
        if node and last and node != last:
            edges.append((last, node))
        last = node or last
    if last and not running and last != "out" and steps[-1].title != "Officer decided":
        edges.append((last, "out"))
    return edges


def _next_node(conv: Conversation, steps: list[Step]) -> str | None:
    """Which node works now, where that is certain. Otherwise none is guessed."""
    last = steps[-1] if steps else None
    if last is None:
        return None
    node = _node_of(last, conv.stage)
    if node == "passenger":
        return "pick" if conv.stage == "choose_train" else "slots"
    if last.title.startswith("Picked a train") or (node == "pick" and last.status == "ok" and conv.chosen):
        return "decide"
    if node == "check" and last.status == "ok" and conv.pending_station is None and all(n in conv.slots for n in REQUIRED):
        return "trains"  # nothing left to ask, so the rules search the trains
    return {"slots": "check", "trains": "reply", "decide": "reply"}.get(node or "")


def _node_data(steps: list[Step], stage: str) -> dict[str, dict]:
    """Per node: what went in, what came out, last status, seconds, whether it was repaired."""
    data: dict[str, dict] = {}
    for step in steps:
        node = _node_of(step, stage)
        if node is None:
            continue
        entry = data.setdefault(node, {"in": "", "out": "", "status": "ok", "seconds": 0.0, "repaired": False, "steps": []})
        if step.sent:
            entry["in"] = step.sent
        if step.title.startswith("Assert") or step.title.startswith("Handed on"):
            entry["in"] = step.detail
        elif not (entry["out"] and step.actor == "Host"):  # a host check keeps the model's words on show
            entry["out"] = step.detail
        entry["repaired"] |= step.status in ("repair", "refused")
        entry["status"] = step.status
        entry["seconds"] += step.seconds
        entry["steps"].append(step)
    return data


def _pretty(text: str) -> str:
    """Model answers carry a [live]/[replay] tag; JSON reads better indented."""
    body = text.split("] ", 1)[1] if text.startswith(("[live] ", "[replay] ")) else text
    try:
        return json.dumps(json.loads(body), ensure_ascii=False, indent=2)
    except ValueError:
        return body


def _preview(text: str, width: int = 30, lines: int = 2) -> list[str]:
    flat = " ".join(_pretty(text).split())
    chunks = [flat[i:i + width] for i in range(0, min(len(flat), width * lines), width)]
    if len(flat) > width * lines:
        chunks[-1] = chunks[-1][:-1] + "…"
    return chunks


def _xy(node: str) -> tuple[int, int]:
    col, row = NODES[node][3]
    return PAD + col * COL, PAD + 26 + row * ROW


def _wire(a: str, b: str, css: str) -> str:
    (ax, ay), (bx, by) = _xy(a), _xy(b)
    x1, y1, x2, y2 = ax + NODE_W, ay + OUT_Y, bx, by + IN_Y
    if x2 - x1 >= 30:  # forward: a plain S-curve
        bend = max(40, (x2 - x1) / 2)
        d = f"M{x1},{y1} C{x1 + bend},{y1} {x2 - bend},{y2} {x2},{y2}"
    else:  # backward: drop into the gap between rows, run left, rise into the input
        gap = (y1 + y2) / 2 if y2 > y1 else max(y1, y2) + 40
        d = (f"M{x1},{y1} C{x1 + 40},{y1} {x1 + 30},{gap} {x1 - 10},{gap} "
             f"L{x2 + 10},{gap} C{x2 - 30},{gap} {x2 - 40},{y2} {x2},{y2}")
    return f'<path class="wire {css}" d="{d}"/>'


def _node_svg(key: str, entry: dict | None, state: str, reply: str) -> str:
    caption, (in_name, in_type), (out_name, out_type), _cell = NODES[key]
    x, y = _xy(key)
    status = entry["status"] if entry else ""
    css = f"node {state} st-{status}" + (" repaired" if entry and entry["repaired"] else "")
    title = html.escape(caption.split(" (")[0].lstrip("0123456789 "))  # patterns stay in the caption
    tip = html.escape(f"{caption}\nin: {_pretty(entry['in'])[:300]}\nout: {_pretty(entry['out'])[:300]}" if entry else caption)
    parts = [f'<g class="{css}" transform="translate({x},{y})"><title>{tip}</title>',
             f'<text class="cap" x="{NODE_W}" y="-9" text-anchor="end">{html.escape(caption)}()</text>',
             f'<rect class="card" width="{NODE_W}" height="{NODE_H}" rx="9"/>',
             f'<line class="sep" x1="0" y1="36" x2="{NODE_W}" y2="36"/>',
             f'<text class="title" x="14" y="23">{title}</text>',
             _badge(state, status)]
    if in_name:
        parts.append(f'<circle class="port in" cx="0" cy="{IN_Y}" r="5.5"/>'
                     f'<text class="pname" x="16" y="{IN_Y + 4}">{in_name} <tspan class="ptype">{in_type}</tspan></text>')
    shown = reply if key == "out" else (entry["out"] if entry else "")
    if key == "out" and not shown and state == "done":
        shown = "sent to the chat"
    lines = _preview(shown, 27, 2 if out_name else 4) if shown else (["working…"] if state == "active" else ["Waiting for output…"])
    base = IN_Y + 24 if in_name else 58
    for i, line in enumerate(lines):
        parts.append(f'<text class="pv{" empty" if not shown else ""}" x="16" y="{base + i * 15}">{html.escape(line)}</text>')
    if out_name:
        parts.append(f'<text class="pname" x="{NODE_W - 16}" y="{OUT_Y + 4}" text-anchor="end">'
                     f'<tspan class="ptype">{out_type}</tspan> {out_name}</text>'
                     f'<path class="port out" d="M{NODE_W - 6},{OUT_Y} l6,-6 l6,6 l-6,6 z"/>')
    if entry and entry["seconds"]:
        parts.append(f'<text class="secs" x="{NODE_W - 14}" y="{IN_Y + 4}" text-anchor="end">{entry["seconds"]:.1f} s</text>')
    parts.append("</g>")
    return "".join(parts)


def _badge(state: str, status: str) -> str:
    """Top-right icon: play when idle, a pulse when running, a check or cross when done."""
    x = NODE_W - 22
    if state == "active":
        return f'<circle class="pulse" cx="{x + 4}" cy="18" r="5"/>'
    if state == "done" and status in ("refused", "failed"):
        return f'<path class="mark bad" d="M{x},14 l8,8 M{x + 8},14 l-8,8"/>'
    if state == "done" and status == "handed_on":
        return f'<path class="mark hand" d="M{x - 1},18 h10 m-4,-4 l4,4 l-4,4"/>'
    if state == "done":
        return f'<path class="mark ok" d="M{x - 1},18 l3.5,3.5 l6.5,-7"/>'
    return f'<path class="play" d="M{x},12 l9,6 l-9,6 z"/>'


def _inspector(steps: list[Step], stage: str) -> str:
    """Every boundary crossing of this turn, in order, with the exact payload."""
    items = []
    for i, step in enumerate(steps, 1):
        node = _node_of(step, stage)
        caption = NODES[node][0] if node else step.actor
        mode = "replay" if step.detail.startswith("[replay]") else "live" if step.detail.startswith("[live]") else ""
        meta = " · ".join(x for x in (step.pattern, mode, f"{step.seconds:.1f} s" if step.seconds else "") if x)
        blocks = ""
        if step.sent:
            blocks += f'<div class="io"><b>sent</b><pre>{html.escape(_pretty(step.sent)[:4000])}</pre></div>'
        label = "sent" if step.title.startswith(("Assert", "Handed on")) else "returned"
        blocks += f'<div class="io"><b>{label}</b><pre>{html.escape(_pretty(step.detail)[:4000])}</pre></div>'
        items.append(f'<details class="st-{step.status}"><summary><span class="n">{i}</span>'
                     f'<span class="who">{html.escape(caption)}</span><span class="what">{html.escape(step.title)}</span>'
                     f'<span class="meta">{html.escape(meta)}</span></summary>{blocks}</details>')
    return "".join(items)


def diagram(conv: Conversation, running: bool = False, reply: str = "") -> str:
    """The current turn on a node graph: lit wires show where the data went, nodes show what came out."""
    turn, steps = _current_turn(conv.trace)
    data = _node_data(steps, conv.stage)
    used = _path(steps, running, conv.stage)
    active = _next_node(conv, steps) if running else None
    earlier = {node for step in conv.trace[: len(conv.trace) - len(steps)] if (node := _node_of(step, conv.stage))}
    wires = [_wire(a, b, "faint") for a, b in EDGES if (a, b) not in used]
    wires += [_wire(a, b, "lit") for a, b in dict.fromkeys(used)]
    if active and steps and (last := _node_of(steps[-1], conv.stage)) and last != active:
        wires.append(_wire(last, active, "flowing"))
    nodes = []
    for key in NODES:
        if key == active:
            state = "active"
        elif key in data or (key == "out" and any(b == "out" for _, b in used)):
            state = "done"
        elif key in earlier:
            state = "earlier"
        else:
            state = "idle"
        nodes.append(_node_svg(key, data.get(key), state, reply if state == "done" else ""))
    if running:
        status = f'<span class="status live"><i></i>{WORKING.get(active or "", "working")}</span>'
    elif steps:
        seconds = sum(step.seconds for step in steps)
        status = f'<span class="status done"><i></i>done · {len(steps)} steps · {seconds:.1f} s</span>'
    else:
        status = '<span class="status idle"><i></i>waiting for a message</span>'
    svg = (f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Pipeline graph of the refund assistant">'
           f'{"".join(wires)}{"".join(nodes)}</svg>')
    title = f"Workflow · turn {turn}" if turn else "Workflow"
    inspector = _inspector(steps, conv.stage)
    inspector = (f'<div class="inspect"><h4>Inspector <small>what crossed each boundary, in order; click to open</small></h4>'
                 f'{inspector}</div>') if inspector else ""
    return (f'<section class="graph"><header><h3>{title}</h3>{status}</header>'
            f'<div class="canvas">{svg}</div>{inspector}</section>')


def trace_rows(conv: Conversation) -> list[list[str]]:
    return [[s.pattern, s.actor, s.title, s.detail[:600], s.status, f"{s.seconds:.1f}"] for s in conv.trace]


def proof_text(conv: Conversation) -> str:
    if conv.verdict is None:
        return "The rules' proof appears here after a verdict."
    return conv.verdict.proof or "No proof: the rules did not reach a verdict for this case."


def _bot(text: str) -> dict:
    return {"role": "assistant", "content": text}


def _user(text: str) -> dict:
    return {"role": "user", "content": text}


THEME = gr.themes.Soft(
    primary_hue=gr.themes.colors.red,
    neutral_hue=gr.themes.colors.slate,
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
).set(button_primary_background_fill="#eb0000", button_primary_background_fill_hover="#c60018")

CSS = """
.app-head { display:flex; align-items:flex-end; justify-content:space-between; gap:16px; flex-wrap:wrap;
  padding:4px 2px 10px; border-bottom:1px solid var(--border-color-primary); margin-bottom:6px; }
.app-head h1 { margin:0; font-size:22px; letter-spacing:-.01em; display:flex; align-items:center; gap:10px; }
.app-head h1 .mark { width:26px; height:26px; border-radius:6px; background:#eb0000; display:inline-grid; place-items:center; }
.app-head h1 .mark svg { width:16px; height:16px; stroke:#fff; fill:none; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }
.app-head p { margin:4px 0 0; color:var(--body-text-color-subdued); font-size:14px; }
.app-head .chips { display:flex; gap:6px; flex-wrap:wrap; }
.app-head .chips span { font-size:12px; padding:4px 10px; border-radius:999px; border:1px solid var(--border-color-primary);
  color:var(--body-text-color-subdued); background:var(--background-fill-secondary); }

.graph { --bg:#0d0e14; --dot:#262838; --card:#16171f; --edge:#2b2d3b; --ink:#e6e7ee; --sub:#9a9cb0; --faint:#5d6075;
  --wire:#8b7cf6; --ok:#34d399; --bad:#f87171; --warn:#fbbf24; --hand:#fb923c;
  background:var(--bg); border-radius:14px; border:1px solid #23252f; padding:12px 12px 10px; color:var(--ink); font-size:13px; }
.graph header { display:flex; justify-content:space-between; align-items:center; gap:8px; padding:0 2px 6px; }
.graph h3 { margin:0; font-size:14px; font-weight:600; color:var(--ink); }
.graph .status { display:inline-flex; align-items:center; gap:7px; font:500 11.5px var(--font-mono); color:var(--sub);
  padding:3px 10px; border-radius:999px; border:1px solid var(--edge); background:var(--card); }
.graph .status i { width:7px; height:7px; border-radius:50%; background:var(--faint); }
.graph .status.live i { background:var(--warn); animation:g-pulse 1.1s ease-in-out infinite; }
.graph .status.done i { background:var(--ok); }
.graph .canvas { border-radius:10px; background-color:var(--bg);
  background-image:radial-gradient(circle, var(--dot) 1.2px, transparent 1.3px); background-size:22px 22px; }
.graph svg { display:block; width:100%; height:auto; font-family:var(--font); }
.graph .wire { fill:none; stroke-width:2.6; stroke-linecap:round; }
.graph .wire.faint { stroke:#2c2e40; stroke-width:2; }
.graph .wire.lit { stroke:var(--wire); filter:drop-shadow(0 0 3px rgba(139,124,246,.45)); }
.graph .wire.flowing { stroke:var(--warn); stroke-dasharray:7 7; animation:g-march .7s linear infinite; }
.graph .node .card { fill:var(--card); stroke:var(--edge); stroke-width:1.2; }
.graph .node .sep { stroke:var(--edge); }
.graph .node .cap { font:11px var(--font-mono); fill:var(--faint); }
.graph .node .title { font-size:14.5px; font-weight:650; fill:var(--ink); }
.graph .node .pname { font-size:12.5px; fill:var(--ink); }
.graph .node .ptype { font:10px var(--font-mono); fill:#8f86d9; }
.graph .node .pv { font:11.5px var(--font-mono); fill:#c9cbe0; }
.graph .node .pv.empty { fill:#4b4e63; }
.graph .node .secs { font:10px var(--font-mono); fill:var(--faint); }
.graph .node .port.in { fill:var(--wire); }
.graph .node .port.out { fill:var(--wire); }
.graph .node .play { fill:var(--faint); }
.graph .node .mark { fill:none; stroke-width:2.2; stroke-linecap:round; stroke-linejoin:round; }
.graph .node .mark.ok { stroke:var(--ok); } .graph .node .mark.bad { stroke:var(--bad); } .graph .node .mark.hand { stroke:var(--hand); }
.graph .node .pulse { fill:var(--warn); animation:g-pulse 1.1s ease-in-out infinite; }
.graph .node.idle { opacity:.5; }
.graph .node.idle .port { fill:#4b4e63; }
.graph .node.earlier { opacity:.6; }
.graph .node.done .card { stroke:#4a4c66; }
.graph .node.active .card { stroke:var(--warn); stroke-width:1.8; filter:drop-shadow(0 0 8px rgba(251,191,36,.35)); }
.graph .node.done.st-refused .card, .graph .node.done.st-failed .card { stroke:var(--bad); }
.graph .node.done.st-handed_on .card { stroke:var(--hand); }

.graph .inspect { margin-top:10px; }
.graph .inspect h4 { margin:2px 2px 6px; font-size:12.5px; font-weight:600; color:var(--ink); }
.graph .inspect h4 small { font-weight:400; color:var(--faint); margin-left:6px; }
.graph details { border:1px solid var(--edge); background:var(--card); border-radius:8px; margin-bottom:5px; }
.graph details[open] { border-color:#3c3e55; }
.graph summary { display:grid; grid-template-columns:22px 170px 1fr auto; gap:8px; align-items:baseline; padding:6px 10px;
  cursor:pointer; list-style:none; font-size:12px; }
.graph summary::-webkit-details-marker { display:none; }
.graph summary:hover { background:#1c1d28; border-radius:8px; }
.graph summary:focus-visible { outline:2px solid var(--wire); outline-offset:1px; border-radius:8px; }
.graph summary .n { font:10.5px var(--font-mono); color:var(--faint); text-align:right; }
.graph summary .who { font:11px var(--font-mono); color:#a79ff0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.graph summary .what { color:var(--ink); min-width:0; }
.graph summary .meta { font:10.5px var(--font-mono); color:var(--faint); white-space:nowrap; }
.graph details.st-refused summary .what, .graph details.st-failed summary .what { color:var(--bad); }
.graph details.st-handed_on summary .what { color:var(--hand); }
.graph details.st-repair summary .what { color:var(--warn); }
.graph .io { padding:0 10px 8px; }
.graph .io b { display:block; font:600 10px var(--font-mono); text-transform:uppercase; letter-spacing:.06em; color:var(--faint);
  margin:4px 0 3px; }
.graph pre { margin:0; padding:8px 10px; border-radius:6px; background:#0f1017; border:1px solid #20222d; color:#d6d8ea;
  font:11.5px/1.5 var(--font-mono); max-height:240px; overflow:auto; white-space:pre-wrap; word-break:break-word; }

@keyframes g-pulse { 50% { opacity:.3; } }
@keyframes g-march { to { stroke-dashoffset:-28; } }
@media (prefers-reduced-motion: reduce) { .graph * { animation:none !important; } }
"""

HEADER = """<div class="app-head"><div>
<h1><span class="mark"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3.1V7a4 4 0 0 0 8 0V3.1"/><path d="m9 15-1-1"/><path d="m15 15 1-1"/><path d="M9 19c-2.8 0-5-2.2-5-5v-4a8 8 0 0 1 16 0v4c0 2.8-2.2 5-5 5Z"/><path d="m8 19-2 3"/><path d="m16 19 2 3"/></svg></span>Fact-safe refund assistant</h1>
<p>Delays on Saturday 7 November 2026, checked against what really ran. The rules keep the last word.</p></div>
<div class="chips"><span>GPT-5 mini reads and phrases</span><span>FrameX rules decide</span><span>SBB staff decide the rest</span></div></div>"""


def build_app(assistant: Assistant) -> gr.Blocks:
    desk = assistant.desk

    def views(conv: Conversation, reply: str = ""):
        return diagram(conv, reply=reply), trace_rows(conv), proof_text(conv)

    def send(text: str, history: list, conv: Conversation):
        if not text or not text.strip():
            yield gr.skip()
            return
        history = [*history, _user(text), _bot(WAITING)]
        result = {}
        worker = threading.Thread(target=lambda: result.update(reply=assistant.handle(conv, text.strip())))
        worker.start()
        while worker.is_alive():  # redraw the flow as steps land in conv.trace
            yield "", history, conv, diagram(conv, running=True), trace_rows(conv), proof_text(conv)
            worker.join(0.5)
        reply = result.get("reply", "Something went wrong. Please try again.")
        history[-1] = _bot(reply)
        yield "", history, conv, *views(conv, reply)

    def new_case():
        conv = Conversation()
        return [], conv, *views(conv)

    def poll(history: list, conv: Conversation):
        message = assistant.deliver(conv)
        if message is None:
            return gr.skip()
        return [*history, _bot(message)], conv, *views(conv, message)

    def refresh(previous: list[str]):
        choices = desk.open_choices()
        if choices == previous:
            return gr.skip()
        return gr.update(choices=choices), choices

    def show(choice: str | None) -> str:
        case = desk.get(choice.split(":")[0]) if choice else None
        return case.file() if case else "Select an open case."

    def decide(choice: str | None, outcome: str | None, percent, comment: str):
        if not choice or not outcome:
            return gr.skip(), "Select a case and a decision first.", gr.skip()
        desk.decide(choice.split(":")[0], "refund" if outcome == "Refund" else "none", int(percent or 0), comment or "")
        choices = desk.open_choices()
        return gr.update(choices=choices, value=None), "Decision sent to the passenger.", choices

    with gr.Blocks(title="SBB refund assistant") as app:
        gr.HTML(HEADER)
        conv = gr.State(Conversation())
        known = gr.State([])
        with gr.Tabs():
            with gr.Tab("Passenger chat and workflow"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=4, min_width=340):
                        chat = gr.Chatbot(height=600, label="Refund chat", show_label=False,
                                          placeholder="Describe a delayed journey on 7 November 2026, in your own words.")
                        with gr.Row():
                            box = gr.Textbox(placeholder="Describe your delayed journey in your own words", show_label=False,
                                             scale=8, autofocus=True, container=False)
                            send_button = gr.Button("Send", variant="primary", scale=1, min_width=80)
                        new = gr.Button("New case", variant="secondary", size="sm")
                        gr.Examples(examples=EXAMPLES, inputs=box, label="Try one")
                    with gr.Column(scale=7, min_width=520):
                        picture = gr.HTML(diagram(Conversation()))
                with gr.Accordion("Step log and the rules' proof (all turns)", open=False):
                    gr.Markdown(LEGEND)
                    trace = gr.Dataframe(headers=HEADERS, value=[], wrap=True, interactive=False, label="What happened, step by step",
                                         column_widths=["7%", "10%", "24%", "45%", "8%", "6%"])
                    proof = gr.Code(value=proof_text(Conversation()), label="The rules' proof (first lines)", lines=14)
            with gr.Tab("SBB customer service"):
                gr.Markdown("Cases the rules could not decide. A person decides here, and the decision goes straight to the passenger.")
                picker = gr.Dropdown(choices=[], label="Open cases")
                case_file = gr.Markdown("Select an open case.")
                decision = gr.Radio(["Refund", "No refund"], label="Decision")
                percent = gr.Number(value=0, precision=0, minimum=0, maximum=100, label="Refund, % of the ticket price")
                comment = gr.Textbox(label="Note to the passenger (optional)")
                decide_button = gr.Button("Send decision to the passenger", variant="primary")
                status = gr.Markdown()

        chat_inputs = [box, chat, conv]
        chat_outputs = [box, chat, conv, picture, trace, proof]
        send_button.click(send, chat_inputs, chat_outputs, api_name="send")
        box.submit(send, chat_inputs, chat_outputs)
        new.click(new_case, None, [chat, conv, picture, trace, proof])
        gr.Timer(2.0).tick(poll, [chat, conv], [chat, conv, picture, trace, proof], show_progress="hidden")
        gr.Timer(2.0).tick(refresh, [known], [picker, known], show_progress="hidden")
        picker.change(show, picker, case_file)
        decide_button.click(decide, [picker, decision, percent, comment], [picker, status, known])
    return app
