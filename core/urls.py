from django.urls import path

from . import views

app_name = "core"


urlpatterns = [
    path(
        "",
        views.index,
        name="index",
    ),
    path(
        "calendar/memo/",
        views.calendar_memo_detail,
        name="calendar_memo_detail",
    ),
    path(
        "calendar/memo/save/",
        views.calendar_memo_save,
        name="calendar_memo_save",
    ),
    path(
        "calendar/memo/dates/",
        views.calendar_memo_dates,
        name="calendar_memo_dates",
    ),
]
