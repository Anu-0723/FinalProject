def navbar_context(request):
    app_pages = {
        "report_missing",
        "report_found",
        "view_found",
        "view_missing",
        "browse_missing",
        "my_reports",
        "view_report",
        "profile",
        "update_profile",
        "inbox",
        "open_chat",
    }

    return {
        "show_app_nav": request.user.is_authenticated
    }
