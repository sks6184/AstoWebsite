import re

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe


register = template.Library()


def _inline_format(text):
    escaped = conditional_escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", escaped)


@register.filter
def _is_remedy_heading(text):
    normalized = (text or "").strip().lower()
    return normalized in {"remedy", "remedies", "उपाय"}


def _is_collapsed_heading(text):
    normalized = (text or "").strip().lower()
    return normalized in {
        "remedy",
        "remedies",
        "practical guidance",
        "why we advise that",
        "why we advise that?",
    }


@register.filter
def astro_answer(value, remedy_note=None):
    lines = str(value or "").splitlines()
    html = []
    in_list = False
    in_details = False
    note_rendered = False

    def close_list():
        nonlocal in_list
        if in_list:
            html.append("</ul>")
            in_list = False

    def close_details():
        nonlocal in_details
        if in_details:
            html.append("</div></details>")
            in_details = False

    def render_heading(heading):
        nonlocal in_details, note_rendered
        close_list()
        close_details()
        if _is_collapsed_heading(heading):
            html.append(
                '<details class="answer-section answer-section--collapsed">'
                f'<summary><span>{_inline_format(heading)}</span><span class="answer-section__hint">View</span></summary>'
                '<div class="answer-section__body">'
            )
            in_details = True
        else:
            html.append(f"<h3>{_inline_format(heading)}</h3>")
        if remedy_note and _is_remedy_heading(heading) and not note_rendered:
            html.append(f'<p class="chart-note remedy-note"><em>{_inline_format(remedy_note)}</em></p>')
            note_rendered = True

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            close_list()
            continue

        if line.startswith("### "):
            render_heading(line[4:])
        elif line.startswith("## "):
            render_heading(line[3:])
        elif line.startswith("# "):
            render_heading(line[2:])
        elif line.startswith(("- ", "* ")):
            if not in_list:
                html.append("<ul>")
                in_list = True
            html.append(f"<li>{_inline_format(line[2:])}</li>")
        else:
            close_list()
            html.append(f"<p>{_inline_format(line)}</p>")

    close_list()
    close_details()
    return mark_safe("".join(html))
