from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .astro_engine import build_placeholder_chart, build_vedic_chart
from .forms import SavedChartForm
from .geocoding import search_places
from .models import SavedChart


@login_required
def chart_list(request):
    charts = SavedChart.objects.filter(user=request.user)
    for chart in charts:
        first_planet = (chart.chart_data.get("d1", {}).get("planets") or [{}])[0]
        first_dasha = (
            chart.chart_data.get("dashas", {}).get("vimshottari", {}).get("periods") or [{}]
        )[0]
        needs_calculation = (
            chart.chart_data.get("system") != "vedic_lahiri"
            or chart.chart_data.get("chart_template") != "north_indian_clear_sign_positions_v8_extra_vargas"
            or "d2" not in chart.chart_data
            or "d7" not in chart.chart_data
            or "d9" not in chart.chart_data
            or "d10" not in chart.chart_data
            or "d20" not in chart.chart_data
            or "d24" not in chart.chart_data
            or "d30" not in chart.chart_data
            or "ashtakavarga" not in chart.chart_data
            or "jaimini" not in chart.chart_data
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
    return render(request, "charts/chart_list.html", {"charts": charts})


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
