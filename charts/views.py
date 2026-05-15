import os
import subprocess
import tempfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from astro_site.localization import SUPPORTED_LANGUAGES, normalize_language

from .astro_engine import build_placeholder_chart, build_vedic_chart
from .forms import SavedChartForm
from .geocoding import search_places
from .report_context import build_chart_report_context
from .models import SavedChart
from .yearly_predictions import get_or_create_yearly_predictions
from .yogas import detect_yogas


def _report_payload(request, chart):
    report_language = normalize_language(request.GET.get("language", "English"))
    yearly = get_or_create_yearly_predictions(chart, answer_language=report_language)
    report = build_chart_report_context(chart, report_language=report_language)
    return {
        "chart": chart,
        "report": report,
        "yearly": yearly,
        "report_language": report_language,
        "report_languages": SUPPORTED_LANGUAGES,
    }


def _browser_path():
    candidates = [
        os.environ.get("ASTROGPT_PDF_BROWSER_PATH", ""),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "google-chrome",
        "chromium",
        "chromium-browser",
        "msedge",
    ]
    for candidate in candidates:
        if candidate and (os.path.exists(candidate) or os.path.basename(candidate) == candidate):
            return candidate
    return ""


def _absolute_static_urls(html, request):
    origin = f"{request.scheme}://{request.get_host()}"
    return (
        html.replace('href="/static/', f'href="{origin}/static/')
        .replace("href='/static/", f"href='{origin}/static/")
        .replace('src="/static/', f'src="{origin}/static/')
        .replace("src='/static/", f"src='{origin}/static/")
    )


def _expand_report_details(html):
    return (
        html.replace('<details class="report-section">', '<details class="report-section" open>')
        .replace('<details class="monthly-report__month">', '<details class="monthly-report__month" open>')
    )


def _pdf_filename(chart):
    safe_name = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in chart.name)
    return f"{safe_name or 'chart'}-astrology-report.pdf"


def _render_report_html(request, context):
    html = render_to_string("charts/chart_report.html", context, request=request)
    return _expand_report_details(_absolute_static_urls(html, request))


def _pdf_with_weasyprint(html, request):
    try:
        from weasyprint import HTML
    except ImportError:
        return None

    base_url = f"{request.scheme}://{request.get_host()}"
    return HTML(string=html, base_url=base_url).write_pdf()


def _refresh_chart_calculation(chart):
    first_planet = (chart.chart_data.get("d1", {}).get("planets") or [{}])[0]
    first_dasha = (
        chart.chart_data.get("dashas", {}).get("vimshottari", {}).get("periods") or [{}]
    )[0]
    needs_calculation = (
        chart.chart_data.get("system") != "vedic_lahiri"
        or chart.chart_data.get("chart_template") != "north_indian_clear_sign_positions_v9_d4_extra_vargas"
        or "d2" not in chart.chart_data
        or "d4" not in chart.chart_data
        or "d7" not in chart.chart_data
        or "d9" not in chart.chart_data
        or "d10" not in chart.chart_data
        or "d20" not in chart.chart_data
        or "d24" not in chart.chart_data
        or "d30" not in chart.chart_data
        or "ashtakavarga" not in chart.chart_data
        or "jaimini" not in chart.chart_data
        or "yogas" not in chart.chart_data
        or "sign_lord" not in first_planet
        or "jaimini_karaka" not in first_planet
        or "start_display" not in first_dasha
        or "antardashas" not in first_dasha
    )
    has_coordinates = chart.latitude is not None and chart.longitude is not None
    if needs_calculation and has_coordinates:
        chart.chart_data = build_vedic_chart(
            chart.name,
            chart.birth_date,
            chart.birth_time,
            chart.birth_place,
            chart.latitude,
            chart.longitude,
            chart.timezone,
        )
        chart.save(update_fields=["chart_data", "updated_at"])
    elif chart.chart_data.get("d1") and "yogas" not in chart.chart_data:
        chart.chart_data["yogas"] = detect_yogas(chart.chart_data)
        chart.save(update_fields=["chart_data", "updated_at"])
    return chart


@login_required
def chart_list(request):
    charts = SavedChart.objects.filter(user=request.user)
    for chart in charts:
        _refresh_chart_calculation(chart)
    return render(request, "charts/chart_list.html", {"charts": charts})


@login_required
def report_list(request):
    charts = SavedChart.objects.filter(user=request.user)
    for chart in charts:
        _refresh_chart_calculation(chart)
    return render(
        request,
        "charts/report_list.html",
        {
            "charts": charts,
            "report_languages": SUPPORTED_LANGUAGES,
            "report_language": normalize_language(request.GET.get("language", "English")),
        },
    )


@login_required
def chart_create(request):
    if request.method == "POST":
        form = SavedChartForm(request.POST)
        if form.is_valid():
            chart = form.save(commit=False)
            chart.user = request.user
            if chart.latitude is not None and chart.longitude is not None:
                chart.chart_data = build_vedic_chart(
                    chart.name,
                    chart.birth_date,
                    chart.birth_time,
                    chart.birth_place,
                    chart.latitude,
                    chart.longitude,
                    chart.timezone,
                )
            else:
                chart.chart_data = build_placeholder_chart(
                    chart.name,
                    chart.birth_date,
                    chart.birth_time,
                    chart.birth_place,
                )
            chart.save()
            messages.success(request, "Chart saved.")
            return redirect("chart_list")
    else:
        form = SavedChartForm()
    return render(request, "charts/chart_form.html", {"form": form})


@login_required
def chart_delete(request, chart_id):
    chart = get_object_or_404(SavedChart, id=chart_id, user=request.user)
    if request.method == "POST":
        chart_name = chart.name
        chart.delete()
        messages.success(request, f"{chart_name} deleted.")
    return redirect("chart_list")


@login_required
def chart_report(request, chart_id):
    chart = get_object_or_404(SavedChart, id=chart_id, user=request.user)
    chart = _refresh_chart_calculation(chart)
    if not chart.chart_data.get("d1"):
        messages.warning(
            request,
            "This chart needs a selected birthplace with latitude and longitude before a report can be generated.",
        )
        return redirect("chart_list")

    return render(request, "charts/chart_report.html", _report_payload(request, chart))


@login_required
def chart_report_pdf(request, chart_id):
    chart = get_object_or_404(SavedChart, id=chart_id, user=request.user)
    chart = _refresh_chart_calculation(chart)
    if not chart.chart_data.get("d1"):
        messages.warning(
            request,
            "This chart needs a selected birthplace with latitude and longitude before a report can be generated.",
        )
        return redirect("chart_list")

    context = _report_payload(request, chart)
    html = _render_report_html(request, context)

    pdf_bytes = _pdf_with_weasyprint(html, request)
    if pdf_bytes:
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{_pdf_filename(chart)}"'
        return response

    browser_path = _browser_path()
    if not browser_path:
        return HttpResponse(
            "PDF generation needs WeasyPrint in production, or Chrome/Edge for local fallback.",
            status=503,
            content_type="text/plain",
        )

    html_path = ""
    pdf_path = ""
    user_data_dir = ""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as html_file:
            html_file.write(html)
            html_path = html_file.name
        pdf_fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
        os.close(pdf_fd)
        user_data_dir = tempfile.mkdtemp(prefix="astrogpt-pdf-")

        subprocess.run(
            [
                browser_path,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                f"--user-data-dir={user_data_dir}",
                "--no-pdf-header-footer",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=1000",
                f"--print-to-pdf={pdf_path}",
                f"file:///{html_path.replace(os.sep, '/')}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )

        with open(pdf_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{_pdf_filename(chart)}"'
        return response
    except (subprocess.SubprocessError, OSError) as exc:
        return HttpResponse(
            f"PDF generation failed: {exc}",
            status=500,
            content_type="text/plain",
        )
    finally:
        for path in [html_path, pdf_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        if user_data_dir and os.path.isdir(user_data_dir):
            try:
                import shutil

                shutil.rmtree(user_data_dir, ignore_errors=True)
            except OSError:
                pass


@login_required
def birth_place_suggestions(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"configured": True, "results": [], "error": ""})

    cache_key = f"birth-place-suggestions:v2:{query.lower()}"
    payload = cache.get(cache_key)
    if payload is None:
        payload = search_places(query)
        if not payload.get("error"):
            cache.set(cache_key, payload, 60 * 60 * 24)
    return JsonResponse(payload)
