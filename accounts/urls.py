from django.urls import path
from .views import (
    register_view, login_view, dashboard_view, logout_view,
    report_missing_view, report_found_view,
    view_found_view, view_missing_view, my_reports_view, open_chat, send_message,
    update_profile_view, delete_report_view,
)

from . import views



urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("logout/", logout_view, name="logout"),

    path("report-missing/", report_missing_view, name="report_missing"),
    path("report-found/", report_found_view, name="report_found"),
    path("found/", view_found_view, name="view_found"),
    path("missing/", view_missing_view, name="browse_missing"),
    path("my-reports/", my_reports_view, name="view_report"),
    path("delete-report/<str:report_type>/<int:report_id>/", delete_report_view, name="delete_report"),

    # Profile
    path("profile/", update_profile_view, name="update_profile"),

    # CHAT
    path("chat/", views.inbox, name="inbox"),
    path("chat/<int:user_id>/", views.open_chat, name="open_chat"),
    path("chat/send/<int:conversation_id>/", views.send_message, name="send_message"),
]

