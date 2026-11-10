"""Passenger chat, live workflow view and customer-service desk."""

from __future__ import annotations

import html

import gradio as gr

from pipeline.assistant import Assistant
from pipeline.state import Conversation

EXAMPLES = [
    "On 7 November I took the 13:29 train from Zürich HB to Oensingen and it never came. Do I get money back?",
    "I travelled from Rotkreuz to Zürich HB on 7 November 2026 at 20:48. Am I owed anything?",
    "On 7 November I was going from St. Gallen to Zürich HB at 8 o'clock. I had a delay. Do I get a refund?",
    "Ich war am 7. November unterwegs und hatte Verspätung.",
    "My train was really late and I want my money back.",
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

ON = "var(--primary-500, #eb0000)"
OFF = "var(--border-color-primary, #aaa)"
TEXT = "var(--body-text-color, #222)"
FILL = "var(--background-fill-secondary, #f4f4f4)"

NODES = (
    (30, 195, 200, 84, "Passenger", "asks in their own words"),
    (650, 30, 220, 84, "Language model", "GPT-5 mini"),
    (650, 300, 220, 96, "Knowledge base", "FrameX facts + rules, SBB 07.11.2026"),
    (30, 425, 200, 72, "SBB customer service", "a person decides"),
)
EDGES = (
    ("input", "M230 212 C 400 110, 520 60, 650 60", "user input IN ▶", 400, 88, "middle"),
    ("answer", "M650 96 C 520 130, 400 190, 230 258", "◀ OUT refund answer · P12, P6", 410, 196, "middle"),
    ("query", "M725 114 L 725 300", "formal request IN ▶ · P3, P6", 716, 212, "end"),
    ("decision", "M800 300 L 800 114", "◀ OUT decision", 810, 212, "start"),
    ("handon", "M650 372 C 500 420, 380 450, 230 462", "unknown: case + model's note · P7", 440, 408, "middle"),
    ("human", "M130 425 L 130 279", "human decides refund and amount", 142, 356, "start"),
)


def _lit(conv: Conversation) -> set[str]:
    """Which arrows this conversation has used so far."""
    lit: set[str] = set()
    for step in conv.trace:
        if step.actor == "Passenger":
            lit.add("input")
        if step.actor == "Host" and step.pattern.startswith(("P3", "P1")):
            lit.add("query")
        if step.actor == "Rules":
            lit.add("decision")
        if step.pattern.startswith("P12"):
            lit.add("answer")
        if step.status == "handed_on":
            lit.add("handon")
        if step.actor == "Human":
            lit.add("human")
    return lit


def diagram(conv: Conversation) -> str:
    lit = _lit(conv)
    parts = [
        '<svg viewBox="0 0 960 510" style="width:100%;max-width:960px" role="img" aria-label="Workflow of the refund assistant">',
        "<defs>",
        *(f'<marker id="a{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
          f'<path d="M0 0L10 5L0 10z" style="fill:{color}"/></marker>' for i, color in enumerate((OFF, ON))),
        "</defs>",
    ]
    for key, path, label, x, y, anchor in EDGES:
        active = key in lit
        parts.append(f'<path d="{path}" fill="none" style="stroke:{ON if active else OFF};stroke-width:{3 if active else 1.5}" '
                     f'marker-end="url(#a{int(active)})"/>')
        parts.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="13" style="fill:{TEXT};font-weight:{700 if active else 400}">'
                     f"{html.escape(label)}</text>")
    for x, y, width, height, title, subtitle in NODES:
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" style="fill:{FILL};stroke:{TEXT}"/>')
        parts.append(f'<text x="{x + width / 2}" y="{y + height / 2 - 4}" text-anchor="middle" font-size="16" font-weight="700" style="fill:{TEXT}">{title}</text>')
        parts.append(f'<text x="{x + width / 2}" y="{y + height / 2 + 18}" text-anchor="middle" font-size="12" style="fill:{TEXT}">{subtitle}</text>')
    parts.append("</svg>")
    stage = f"<p><b>Stage:</b> {html.escape(conv.stage)}</p>"
    return "".join(parts) + stage


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


def build_app(assistant: Assistant) -> gr.Blocks:
    desk = assistant.desk

    def views(conv: Conversation):
        return diagram(conv), trace_rows(conv), proof_text(conv)

    def send(text: str, history: list, conv: Conversation):
        if not text or not text.strip():
            yield gr.skip()
            return
        history = [*history, _user(text), _bot(WAITING)]
        yield "", history, conv, *views(conv)
        history[-1] = _bot(assistant.handle(conv, text.strip()))
        yield "", history, conv, *views(conv)

    def new_case():
        conv = Conversation()
        return [], conv, *views(conv)

    def poll(history: list, conv: Conversation):
        message = assistant.deliver(conv)
        if message is None:
            return gr.skip()
        return [*history, _bot(message)], conv, *views(conv)

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
        gr.Markdown("# Fact-safe refund assistant\nDelays on Saturday 7 November 2026, checked against what really ran. The rules keep the last word.")
        conv = gr.State(Conversation())
        known = gr.State([])
        with gr.Tabs():
            with gr.Tab("Passenger chat"):
                chat = gr.Chatbot(height=480, label="Refund chat")
                with gr.Row():
                    box = gr.Textbox(placeholder="Describe your delayed journey in your own words", show_label=False, scale=8, autofocus=True)
                    send_button = gr.Button("Send", variant="primary", scale=1)
                new = gr.Button("New case")
                gr.Examples(examples=EXAMPLES, inputs=box, label="Try one")
            with gr.Tab("Workflow"):
                picture = gr.HTML(diagram(Conversation()))
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
