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
        "event",
        "conversion_value",
        "currency",
    )
    ordering = ("-created_at",)


class IsCanonicalFilter(admin.SimpleListFilter):
    title = "canonical status"
    parameter_name = "is_canonical"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Canonical"),
            ("no", "Merged"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(merged_into__isnull=True)
        if self.value() == "no":
            return queryset.filter(merged_into__isnull=False)
        return queryset


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):
    list_display = (
        "linked_user",
        "created_at",
        "is_canonical",
    )
    list_filter = ("created_at", IsCanonicalFilter)
    search_fields = ("linked_user__username",)
    readonly_fields = (
        "uuid",
        "created_at",
    )

    fieldsets = (
        (
            None,
            {"fields": ("uuid", "linked_user", "first_visit_user_agent")},
        ),
        (
            "Tracking",
            {"fields": ("merged_into",)},
        ),
        ("Timestamps", {"fields": ("created_at",)}),
    )

    inlines = [TouchpointInline, ConversionInline]
    autocomplete_fields = ["linked_user"]
    date_hierarchy = "created_at"
    ordering = (
        "merged_into",
        "-created_at",
    )

    def is_canonical(self, obj: Identity) -> bool:
        return obj.is_canonical()

    is_canonical.boolean = True  # type: ignore


@admin.register(Touchpoint)
class TouchpointAdmin(admin.ModelAdmin):
    list_display = (
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "created_at",
    )
    list_filter = ("utm_source", "utm_medium", "created_at")
    search_fields = ("url", "utm_source", "utm_campaign")
    readonly_fields = ("uuid", "created_at")
    autocomplete_fields = ["identity"]

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
        (
            "Click Tracking Parameters",
            {
                "fields": (
                    "fbclid",
                    "gclid",
                    "msclkid",
                    "ttclid",
                    "li_fat_id",
                    "twclid",
                    "igshid",
                )
            },
        ),
    )

    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(Conversion)
class ConversionAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "conversion_value",
        "currency",
        "created_at",
        "is_confirmed",
    )
    list_filter = (
        "event",
        "currency",
        "created_at",
    )
    search_fields = (
        "event",
        "identity__uuid",
    )
    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ["identity"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "uuid",
                    "identity",
                    "event",
                    "created_at",
                    "updated_at",
                    "is_confirmed",
                )
            },
        ),
        ("Value", {"fields": ("conversion_value", "currency")}),
        ("Source", {"fields": ("source_content_type", "source_object_id")}),
    )

    date_hierarchy = "created_at"
    ordering = ("-created_at",)
