from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import UserProfile, MissingPerson, FoundPerson

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "mobile",
        "city",
        "state",
        "country",
    )
    search_fields = (
        "full_name",
        "mobile",
        "city",
        "state",
        "country",
        "user__username",
    )
    list_filter = ("state", "country")
    ordering = ("full_name",)


@admin.register(MissingPerson)
class MissingPersonAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "age",
        "gender",
        "status",
        "last_seen_location",
        "user",
        "reported_at",
    )
    search_fields = (
        "name",
        "last_seen_location",
        "description",
        "user__username",
    )
    list_filter = ("gender", "reported_at")
    ordering = ("-reported_at",)
    date_hierarchy = "reported_at"


@admin.register(FoundPerson)
class FoundPersonAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "age_estimate",
        "found_location",
        "user",
        "reported_at",
    )
    search_fields = (
        "name",
        "found_location",
        "description",
        "user__username",
    )
    list_filter = ("reported_at",)
    ordering = ("-reported_at",)
    date_hierarchy = "reported_at"
