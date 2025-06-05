from django.contrib import admin

from .models import Conversion, Identity, Touchpoint


class TouchpointInline(admin.TabularInline):
    model = Touchpoint
    extra = 0
    readonly_fields = (
        "uuid",
        "created_at",
    )
    fields = (
        "created_at",
        "utm_source",
        "utm_medium",
        "utm_campaign",
    )
    ordering = ("-created_at",)


class ConversionInline(admin.TabularInline):
    model = Conversion
    extra = 0
    readonly_fields = (
        "uuid",
        "created_at",
    )
    fields = (
        "created_at",
        "conversion_type",
        "conversion_value",
        "currency",
    )
    ordering = ("-created_at",)


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):
    list_display = (
        "tracking_method",
        "linked_user",
        "created_at",
        "last_visit_at",
    )
    list_filter = (
        "tracking_method",
        "created_at",
    )
    search_fields = ("linked_user__username",)
    readonly_fields = (
        "uuid",
        "created_at",
    )

    fieldsets = (
        (
            None,
            {"fields": ("uuid", "tracking_method", "linked_user")},
        ),
        (
            "Tracking",
            {"fields": ("first_ip_address", "first_user_agent", "merged_into")},
        ),
        ("Timestamps", {"fields": ("created_at", "last_visit_at")}),
    )

    inlines = [TouchpointInline, ConversionInline]
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(Touchpoint)
class TouchpointAdmin(admin.ModelAdmin):
    list_display = (
        "identity",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "created_at",
    )
    list_filter = ("utm_source", "utm_medium", "created_at")
    search_fields = ("url", "utm_source", "utm_campaign")
    readonly_fields = ("uuid", "created_at")

    fieldsets = (
        (None, {"fields": ("uuid", "identity", "created_at", "url", "referrer")}),
        (
            "UTM Parameters",
            {
                "fields": (
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                    "utm_term",
                    "utm_content",
                )
            },
        ),
    )

    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(Conversion)
class ConversionAdmin(admin.ModelAdmin):
    list_display = (
        "identity",
        "conversion_type",
        "conversion_value",
        "currency",
        "created_at",
    )
    list_filter = (
        "conversion_type",
        "currency",
        "created_at",
    )
    search_fields = (
        "conversion_type",
        "identity__uuid",
    )
    readonly_fields = (
        "uuid",
        "created_at",
    )

    fieldsets = (
        (None, {"fields": ("uuid", "identity", "conversion_type", "created_at")}),
        ("Value", {"fields": ("conversion_value", "currency")}),
        ("Source", {"fields": ("source_content_type", "source_object_id")}),
    )

    date_hierarchy = "created_at"
    ordering = ("-created_at",)
