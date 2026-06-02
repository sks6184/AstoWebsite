from __future__ import annotations

from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "astrology" / "docs" / "user_question_flow.pdf"


def esc(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", "")
    )


class Pdf:
    def __init__(self) -> None:
        self.objects: list[bytes] = []
        self.pages: list[int] = []
        self.font_obj = self.add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        self.font_bold_obj = self.add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    def add(self, payload: bytes) -> int:
        self.objects.append(payload)
        return len(self.objects)

    def page(self, content: str, width: int = 842, height: int = 595) -> None:
        stream = content.encode("utf-8")
        stream_obj = self.add(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
        page_obj = self.add(
            (
                f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {width} {height}] "
                f"/Resources << /Font << /F1 {self.font_obj} 0 R /F2 {self.font_bold_obj} 0 R >> >> "
                f"/Contents {stream_obj} 0 R >>"
            ).encode("ascii")
        )
        self.pages.append(page_obj)

    def write(self, path: Path) -> None:
        kids = " ".join(f"{page} 0 R" for page in self.pages)
        pages_obj = self.add(f"<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>".encode("ascii"))
        catalog_obj = self.add(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("ascii"))

        fixed_objects = []
        for payload in self.objects:
            fixed_objects.append(payload.replace(b"/Parent 0 0 R", f"/Parent {pages_obj} 0 R".encode("ascii")))

        offsets = []
        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        for index, payload in enumerate(fixed_objects, start=1):
            offsets.append(len(output))
            output.extend(f"{index} 0 obj\n".encode("ascii"))
            output.extend(payload)
            output.extend(b"\nendobj\n")
        xref_offset = len(output)
        output.extend(f"xref\n0 {len(fixed_objects) + 1}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets:
            output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.extend(
            (
                f"trailer\n<< /Size {len(fixed_objects) + 1} /Root {catalog_obj} 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF\n"
            ).encode("ascii")
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(output)


class Canvas:
    def __init__(self) -> None:
        self.ops: list[str] = []

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = "2B3A39", width: float = 1) -> None:
        self.ops.append(color_rgb(color))
        self.ops.append(f"{width} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S")

    def arrow(self, x1: float, y1: float, x2: float, y2: float, label: str = "", color: str = "315C72") -> None:
        self.line(x1, y1, x2, y2, color, 1.3)
        if x2 >= x1:
            points = [(x2, y2), (x2 - 8, y2 + 4), (x2 - 8, y2 - 4)]
        else:
            points = [(x2, y2), (x2 + 8, y2 + 4), (x2 + 8, y2 - 4)]
        self.ops.append(color_rgb(color, fill=True))
        self.ops.append(
            f"{points[0][0]:.1f} {points[0][1]:.1f} m {points[1][0]:.1f} {points[1][1]:.1f} l "
            f"{points[2][0]:.1f} {points[2][1]:.1f} l f"
        )
        if label:
            self.text((x1 + x2) / 2 - 30, y1 + 9, label, 7, color=color)

    def rect(self, x: float, y: float, w: float, h: float, stroke: str = "D9DED2", fill: str = "FFFFFF", width: float = 1) -> None:
        self.ops.append(color_rgb(fill, fill=True))
        self.ops.append(color_rgb(stroke))
        self.ops.append(f"{width} w {x:.1f} {y:.1f} {w:.1f} {h:.1f} re B")

    def box(self, x: float, y: float, w: float, h: float, title: str, body: list[str], fill: str = "FBFCF8", stroke: str = "D9DED2") -> None:
        self.rect(x, y, w, h, stroke, fill, 1)
        self.text(x + 8, y + h - 16, title, 9, bold=True, color="17384A")
        yy = y + h - 31
        for line in body:
            for wrapped in textwrap.wrap(line, width=max(20, int(w / 5.4))):
                if yy < y + 8:
                    return
                self.text(x + 8, yy, wrapped, 7, color="1F2A29")
                yy -= 10

    def title(self, text: str, subtitle: str = "") -> None:
        self.text(32, 560, text, 19, bold=True, color="17384A")
        if subtitle:
            self.text(34, 540, subtitle, 9, color="65716D")
        self.line(32, 528, 810, 528, "D9DED2", 1)

    def text(self, x: float, y: float, text: str, size: int = 9, bold: bool = False, color: str = "1F2A29") -> None:
        self.ops.append(color_rgb(color, fill=True))
        font = "F2" if bold else "F1"
        self.ops.append(f"BT /{font} {size} Tf {x:.1f} {y:.1f} Td ({esc(text)}) Tj ET")

    def bullet_list(self, x: float, y: float, items: list[str], width: int = 88, size: int = 8, gap: int = 11) -> float:
        yy = y
        for item in items:
            lines = textwrap.wrap(item, width=width)
            if not lines:
                continue
            self.text(x, yy, "-", size, bold=True, color="315C72")
            self.text(x + 10, yy, lines[0], size)
            yy -= gap
            for line in lines[1:]:
                self.text(x + 10, yy, line, size)
                yy -= gap
        return yy

    def content(self) -> str:
        return "\n".join(self.ops)


def color_rgb(hex_color: str, fill: bool = False) -> str:
    value = hex_color.strip("#")
    r = int(value[0:2], 16) / 255
    g = int(value[2:4], 16) / 255
    b = int(value[4:6], 16) / 255
    op = "rg" if fill else "RG"
    return f"{r:.3f} {g:.3f} {b:.3f} {op}"


def add_flow_page(pdf: Pdf) -> None:
    c = Canvas()
    c.title("Astrology GPT: User Question Flow", "Live Django request path, deterministic astrology pipeline, RAG/LLM traffic, validation, and storage.")

    y = 420
    boxes = [
        ("Browser / ngrok", ["User submits chart_id, question, depth, language.", "templates/chat/ask.html"], "EEF3F1"),
        ("Django view", ["Checks auth, credits, chart ownership.", "chat/views.py::ask_question"], "FFFFFF"),
        ("Conversation DB", ["Creates user Message before LLM call.", "chat/models.py"], "FFF8DF"),
        ("LLM engine", ["Intent, evidence payload, cache, OpenAI call.", "chat/llm_engine.py"], "FFFFFF"),
        ("Assistant answer", ["Validated/repaired answer saved as Message.", "chat/views.py + chat/models.py"], "FFF8DF"),
        ("Rendered reading", ["astro_answer filter formats answer sections.", "templates/chat/ask.html", "chat/templatetags/chat_formatting.py"], "EEF3F1"),
    ]
    x = 30
    for title, body, fill in boxes:
        c.box(x, y, 116, 78, title, body, fill=fill)
        if x < 670:
            c.arrow(x + 116, y + 39, x + 137, y + 39)
        x += 137

    c.text(36, 375, "High-level rule:", 10, bold=True, color="A66F2A")
    c.text(126, 375, "Software calculates. Rules judge. RAG supports. LLM explains. Validator controls quality.", 10, bold=True)

    c.box(52, 245, 170, 92, "Normal prediction branch", [
        "chat.llm_engine.generate_answer()",
        "classify_intent() says intent is not periodic",
        "build_prompt_payload() calls astrology.services.prediction_service.build_prediction_evidence()",
    ])
    c.box(334, 245, 170, 92, "Periodic/rashifal branch", [
        "classify_intent() returns periodic",
        "_generate_rashifal_answer()",
        "chat/rashifal_context.py builds periodic payload",
        "OpenAI file_search max results = 6",
    ])
    c.box(616, 245, 170, 92, "Fallback branch", [
        "If OPENAI_API_KEY or OPENAI_VECTOR_STORE_ID is missing",
        "_fallback_answer() returns deterministic summary",
        "No external LLM/RAG traffic is made",
    ])
    c.arrow(222, 291, 334, 291, "intent split")
    c.arrow(504, 291, 616, 291, "config fail")

    c.text(36, 205, "Important current boundary:", 10, bold=True, color="A66F2A")
    c.bullet_list(54, 188, [
        "The architecture package astrology/ owns deterministic evidence, rules, RAG query construction, synthesis payloads, and validation helpers.",
        "The live traffic orchestrator is still chat/llm_engine.py: it builds compact evidence, calls OpenAI, runs validation, repairs, applies deterministic remedies, caches, and returns the answer.",
        "SavedChart.chart_data is assumed to already contain chart calculations from charts/ code; prediction_service wraps and normalizes that data instead of recalculating from the LLM.",
    ], width=130)
    pdf.page(c.content())


def add_evidence_page(pdf: Pdf) -> None:
    c = Canvas()
    c.title("Deterministic Evidence Construction", "Files used before any LLM synthesis. This is the core no-invention boundary.")

    x0, y0 = 34, 455
    c.box(x0, y0, 145, 62, "Question scope/category", [
        "chat/prediction_context.py",
        "classify_question()",
        "detect_question_scope()",
        "CATEGORY_RULES",
    ], fill="EEF3F1")
    c.box(222, y0, 145, 62, "Chart facts / varga", [
        "astrology/calculations/varga.py",
        "build_chart_facts()",
        "build_varga_assessment()",
        "D1, D9, D10, plus supported vargas",
    ])
    c.box(410, y0, 145, 62, "Dasha facts", [
        "astrology/calculations/dasha_facts.py",
        "Vimshottari",
        "Jaimini / Chara",
        "Yogini",
    ])
    c.box(598, y0, 145, 62, "Transits / timing", [
        "astrology/calculations/transit_facts.py",
        "chat/timing_windows.py",
        "charts/transit_priority.py",
        "SAV and future windows",
    ])
    c.arrow(179, y0 + 31, 222, y0 + 31)
    c.arrow(367, y0 + 31, 410, y0 + 31)
    c.arrow(555, y0 + 31, 598, y0 + 31)

    y = 335
    c.box(34, y, 145, 88, "Parashari facts", [
        "astrology/calculations/parashari.py",
        "House/lord factors",
        "Raja yoga / Dhana yoga",
        "Dasha activation",
    ], fill="FFFFFF")
    c.box(222, y, 145, 88, "Jaimini enrichment", [
        "astrology/calculations/jaimini.py",
        "charts/jaimini_confirmation.py",
        "Karakamsha, Arudha, AK/AmK, Chara dasha",
    ], fill="FFFFFF")
    c.box(410, y, 145, 88, "Varga rule modules", [
        "varga_generic_rules.py",
        "d1_lagna_rules.py",
        "d2_hora_rules.py",
        "d3_drekkana_rules.py",
        "d4_chaturthamsha_rules.py",
        "d7_saptamsha_rules.py",
        "d9_navamsha_rules.py",
    ], fill="FFF8DF")
    c.box(598, y, 145, 88, "YAML rule engine", [
        "astrology/rules/loader.py",
        "astrology/rules/engine.py",
        "parashari_rules.yaml",
        "jaimini_rules.yaml",
        "divisional_rules.yaml",
        "yogini_rules.yaml",
        "transit_rules.yaml",
    ], fill="FFF8DF")

    c.arrow(106, 335, 106, 296)
    c.arrow(294, 335, 294, 296)
    c.arrow(482, 335, 482, 296)
    c.arrow(670, 335, 670, 296)

    c.box(50, 210, 220, 70, "Triggered rules + scores", [
        "astrology/rules/scoring.py::aggregate_scores()",
        "Triggered YAML rules plus Python varga rules are merged into evidence_json['triggered_rules'].",
    ], fill="EEF3F1")
    c.box(310, 210, 220, 70, "Evidence ledger + contradictions", [
        "astrology/evidence/ledger.py",
        "astrology/evidence/contradiction_resolver.py",
        "astrology/evidence/confidence_scorer.py",
    ], fill="EEF3F1")
    c.box(570, 210, 220, 70, "RAG query request", [
        "astrology/rag/query_builder.py",
        "Builds query from category, triggered rules, deterministic facts, ledger, contradictions, and timing windows.",
    ], fill="EEF3F1")
    c.arrow(270, 245, 310, 245)
    c.arrow(530, 245, 570, 245)

    c.box(160, 88, 520, 68, "PredictionEvidence JSON payload", [
        "astrology/structures.py defines question, chart_facts, parashari_vimshottari, jaimini, varga, yogini, transits, triggered_rules, summary_scores, rag, validation.",
        "astrology/services/prediction_service.py is the canonical evidence builder.",
    ], fill="FFFFFF", stroke="315C72")
    c.arrow(680, 210, 680, 156, "payload")

    pdf.page(c.content())


def add_llm_page(pdf: Pdf) -> None:
    c = Canvas()
    c.title("LLM, RAG, Cache, Validation, and Repair Traffic", "External network calls and the exact places where generated text is allowed.")

    c.box(36, 430, 155, 72, "Compact live payload", [
        "chat/llm_engine.py::_compact_live_evidence()",
        "Sends compact context only",
        "Includes evidence_payload, ledger, rules, RAG query request, remedy context",
    ], fill="EEF3F1")
    c.box(240, 430, 155, 72, "Cache lookup", [
        "django.core.cache",
        "key from payload + model + vector_store_id",
        "Cache hit: no OpenAI call",
    ], fill="FFF8DF")
    c.box(444, 430, 155, 72, "OpenAI Responses API", [
        "client.responses.create()",
        "model_for_depth()",
        "instructions from _system_instructions()",
        "input_text = JSON payload",
    ], fill="FFFFFF", stroke="315C72")
    c.box(648, 430, 155, 72, "File search / RAG", [
        "tools=[{'type':'file_search'}]",
        "vector_store_ids=[settings.OPENAI_VECTOR_STORE_ID]",
        "max_num_results=8 normal, 6 rashifal",
    ], fill="FFFFFF", stroke="A66F2A")
    c.arrow(191, 466, 240, 466)
    c.arrow(395, 466, 444, 466, "miss")
    c.arrow(599, 466, 648, 466, "tool")
    c.arrow(648, 444, 599, 444, "snippets")

    c.box(116, 300, 170, 82, "Draft answer returns", [
        "response.output_text",
        "usage input/output tokens captured",
        "LLM may explain only using payload + retrieved context",
    ])
    c.box(336, 300, 170, 82, "Validation gate", [
        "astrology/validation/validator.py",
        "answer_validator.py",
        "evidence_checker.py",
        "completeness_checker.py",
        "specificity_checker.py",
        "contradiction_checker.py",
        "genericity_checker.py",
    ], fill="EEF3F1")
    c.box(556, 300, 170, 82, "Repair call if failed", [
        "chat/llm_engine.py::_repair_answer()",
        "Second Responses API call",
        "Sends original payload, draft answer, validation_result",
        "Uses file_search again",
    ], fill="FFF8DF", stroke="A66F2A")
    c.arrow(444, 430, 201, 382, "answer")
    c.arrow(286, 341, 336, 341)
    c.arrow(506, 341, 556, 341, "fail")
    c.arrow(641, 300, 506, 300, "re-validate")

    c.box(150, 178, 205, 72, "Deterministic remedy override", [
        "chat/llm_engine.py::_apply_deterministic_remedy()",
        "Uses charts/remedies.py via remedy_context",
        "Replaces LLM remedy section with deterministic mantra lines when present",
    ], fill="FFFFFF")
    c.box(486, 178, 205, 72, "Persist final answer", [
        "chat/views.py creates assistant Message",
        "model_name, prompt_tokens, completion_tokens saved",
        "Django redirects to conversation_detail",
    ], fill="FFF8DF")
    c.arrow(421, 300, 252, 250, "pass or repaired")
    c.arrow(355, 214, 486, 214)

    c.text(44, 128, "Traffic summary", 11, bold=True, color="A66F2A")
    c.bullet_list(62, 111, [
        "Inbound user traffic: Browser or ngrok public URL -> Django route chat/urls.py path('ask/') -> chat.views.ask_question().",
        "Internal deterministic traffic: Python function calls over local chart_data, no LLM calculation.",
        "External LLM/RAG traffic: Django server -> OpenAI Responses API. File search is requested as an OpenAI tool against OPENAI_VECTOR_STORE_ID.",
        "Cache hit traffic: if the cache key exists, Django returns cached answer and no OpenAI/File Search request is made.",
        "Failure traffic: missing OPENAI_API_KEY or OPENAI_VECTOR_STORE_ID returns _fallback_answer(), no external call.",
    ], width=138, size=8)
    pdf.page(c.content())


def add_payload_page(pdf: Pdf) -> None:
    c = Canvas()
    c.title("Evidence Payload and File Responsibility Map", "What each part of the JSON means and which files own it.")

    left_items = [
        "question: astrology/structures.py::QuestionContext; populated by prediction_service.py from chat/prediction_context.py.",
        "chart_facts: astrology/calculations/varga.py wraps SavedChart.chart_data; source chart generation is in charts/.",
        "parashari and parashari_vimshottari: parashari.py + dasha_facts.py.",
        "jaimini: dasha_facts.py + jaimini.py + charts/jaimini_confirmation.py.",
        "varga: varga.py plus Python varga rule modules such as d7_saptamsha_rules.py.",
        "yogini: astrology/calculations/yogini.py and charts/yogini_alignment.py for timing windows.",
        "transits: transit_facts.py + chat/timing_windows.py + charts/transit_priority.py.",
    ]
    right_items = [
        "triggered_rules: astrology/rules/engine.py YAML rules plus Python deterministic varga rules.",
        "summary_scores: astrology/rules/scoring.py aggregates triggered rule outcomes.",
        "evidence_ledger: astrology/evidence/ledger.py creates traceable claims.",
        "contradictions: astrology/evidence/contradiction_resolver.py flags mixed signals.",
        "confidence_summary: astrology/evidence/confidence_scorer.py summarizes evidence strength.",
        "rag: astrology/rag/query_builder.py builds search terms; OpenAI file_search retrieves source snippets at call time.",
        "validation: astrology/validation/* checks final answer and drives repair_instruction.",
    ]
    c.box(36, 328, 360, 184, "Required JSON evidence shape - deterministic side", left_items, fill="FBFCF8")
    c.box(446, 328, 360, 184, "Required JSON evidence shape - judgment/support side", right_items, fill="FBFCF8")

    c.text(42, 288, "Strict LLM contract", 11, bold=True, color="A66F2A")
    c.bullet_list(60, 271, [
        "The LLM must not calculate placements, houses, dashas, vargas, yogas, transits, or rule applicability.",
        "The LLM receives already-calculated evidence and may synthesize, explain, and cite retrieved support.",
        "RAG is not the rule engine. RAG supports explanation after deterministic facts and triggered rules exist.",
        "Validation can force a repair pass when the answer is generic, unsupported, missing systems, or contradicts evidence.",
    ], width=132, size=8)

    c.text(42, 198, "Notable live files in request order", 11, bold=True, color="A66F2A")
    c.bullet_list(60, 181, [
        "templates/chat/ask.html -> chat/views.py -> chat/models.py.",
        "chat/llm_engine.py -> astrology/services/prediction_service.py.",
        "prediction_service.py -> calculations, rules, evidence, rag, synthesis.",
        "chat/llm_engine.py -> OpenAI Responses API with file_search vector store.",
        "astrology/validation/validator.py -> repair call when failed.",
        "chat/llm_engine.py::_apply_deterministic_remedy() -> chat/views.py saves final Message.",
        "templates/chat/ask.html + chat/templatetags/chat_formatting.py render final reading.",
    ], width=132, size=8)

    c.text(42, 78, "Current architecture note", 11, bold=True, color="A66F2A")
    c.text(60, 61, "The deterministic architecture is centered in astrology/. The live LLM adapter is still chat/llm_engine.py, which is the main future refactor target.", 8)
    c.text(60, 46, f"Generated file: {OUT.relative_to(ROOT)}", 8, color="65716D")
    pdf.page(c.content())


def main() -> None:
    pdf = Pdf()
    add_flow_page(pdf)
    add_evidence_page(pdf)
    add_llm_page(pdf)
    add_payload_page(pdf)
    pdf.write(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
