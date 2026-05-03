import re

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe


register = template.Library()


def _inline_format(text):
    escaped = conditional_escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


@register.filter
def astro_answer(value):
    lines = str(value or "").splitlines()
    html = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html.append("</ul>")
            in_list = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            close_list()
            continue

        if line.startswith("### "):
            close_list()
            html.append(f"<h3>{_inline_format(line[4:])}</h3>")
        elif line.startswith("## "):
            close_list()
            html.append(f"<h3>{_inline_format(line[3:])}</h3>")
        elif line.startswith("# "):
            close_list()
            html.append(f"<h3>{_inline_format(line[2:])}</h3>")
        elif line.startswith(("- ", "* ")):
            if not in_list:
                html.append("<ul>")
                in_list = True
            html.append(f"<li>{_inline_format(line[2:])}</li>")
        else:
            close_list()
            html.append(f"<p>{_inline_format(line)}</p>")

    close_list()
    return mark_safe("".join(html))
