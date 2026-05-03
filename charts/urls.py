from django.urls import path

from . import views


urlpatterns = [
    path("", views.chart_list, name="chart_list"),
    path("new/", views.chart_create, name="chart_create"),
    path("<int:chart_id>/delete/", views.chart_delete, name="chart_delete"),
    path("birth-place-suggestions/", views.birth_place_suggestions, name="birth_place_suggestions"),
]
